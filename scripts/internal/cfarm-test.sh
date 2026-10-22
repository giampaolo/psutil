#!/bin/sh

# Sync this checkout to a remote host (e.g. one of the GCC compile farm
# machines), build it in a venv there and run the test suite. Output is
# streamed as it happens and also kept on the remote, so whatever was
# produced before a dropped connection isn't lost. The run itself does
# not survive the disconnect.

set -e

HOST=
LOCAL_DIR=
PYTHON=python3
REMOTE_DIR=psutil
CMD="make test-parallel"
REMOTE_LOG=.cfarm-test.log
REMOTE_RC=.cfarm-test.rc
REMOTE_SH=.cfarm-test.sh

files=
stage=
tmp=

# --- utils

usage() {
    cat << EOF
usage: $(basename "$0") [options] HOST

Sync this checkout to HOST, build it in a venv and run the test suite.

  --python=PATH     interpreter used to create the venv, if there isn't
                    one already (default: python3)
  --remote-dir=DIR  remote path, relative to the home dir (default: psutil)
  --cmd=CMD         command to run remotely (default: "make test-parallel")
  -h, --help        show this help

Known hosts:
EOF
    if [ -r "$HOME/.ssh/config" ]; then
        awk '/^Host / {
            for (i = 2; i <= NF; i++)
                if ($i !~ /[*?]/)
                    print "  " $i
        }' "$HOME/.ssh/config"
    fi
}

log() {
    printf '\n\033[1;36m=== %s\033[0m\n' "$1"
}

shquote() {
    # Escape a value for embedding in a single-quoted remote string.
    printf "%s" "$1" | sed "s/'/'\\\\''/g"
}

parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            -h | --help)
                usage
                exit 0
                ;;
            --python=*)
                PYTHON=${1#*=}
                ;;
            --remote-dir=*)
                REMOTE_DIR=${1#*=}
                ;;
            --cmd=*)
                CMD=${1#*=}
                ;;
            -*)
                echo "error: unknown option $1" >&2
                exit 2
                ;;
            *)
                if [ -n "$HOST" ]; then
                    echo "error: too many arguments" >&2
                    exit 2
                fi
                HOST=$1
                ;;
        esac
        shift
    done
    if [ -z "$HOST" ]; then
        echo "error: no host given" >&2
        usage >&2
        exit 2
    fi
    LOCAL_DIR=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
}

# --- sync

sync_repo() {
    log "syncing $LOCAL_DIR -> $HOST:$REMOTE_DIR"
    # Stage the tracked files first, then mirror that directory. rsync
    # then gets a real, complete source tree, so --delete means what it
    # looks like, and the excludes double as protect rules keeping the
    # remote venv, build dir and log alive.
    files=$(mktemp)
    stage=$(mktemp -d)
    git -C "$LOCAL_DIR" ls-files -z > "$files"
    if [ ! -s "$files" ]; then
        echo "error: no tracked files to sync" >&2
        return 1
    fi
    # git lists tracked files deleted from the working tree but not
    # committed yet; skip them here so the mirror drops them too.
    rsync \
        --archive \
        --ignore-missing-args \
        --from0 \
        --files-from="$files" \
        "$LOCAL_DIR/" "$stage/"
    # SC2016: $PATH is meant for the remote shell, not this one.
    # shellcheck disable=SC2016
    rsync \
        --archive \
        --compress \
        --delete \
        --exclude=/.venv \
        --exclude=/build \
        --exclude='/.cfarm-test.*' \
        --partial \
        --rsync-path='PATH=$PATH:/opt/freeware/bin rsync' \
        "$stage/" "$HOST:$REMOTE_DIR"
}

# --- remote

remote_script() {
    cat << 'EOF'
set -e

if [ ! -d .venv ]; then
    echo ">>> creating .venv with $PYTHON"
    # Debian ships ensurepip in a separate python3-venv package which
    # the farm machines don't always have. install-pydeps.sh bootstraps
    # pip over the network anyway, so a venv without it will do.
    "$PYTHON" -m venv .venv || {
        rm -rf .venv
        "$PYTHON" -m venv --without-pip .venv
    }
fi

. .venv/bin/activate

uname -srm
python -VV
python -c 'import os, platform, struct, sys; print("libc=%s%s | %s-endian | %d bit | page=%dK" % (platform.libc_ver()[0] or "?", platform.libc_ver()[1], sys.byteorder, struct.calcsize("P") * 8, os.sysconf("SC_PAGE_SIZE") // 1024))'

echo ">>> make install-pydeps-test"
make install-pydeps-test

echo ">>> make build"
make build

echo ">>> $CMD"
eval "$CMD"
EOF
}

upload_script() {
    tmp=$(mktemp)
    remote_script > "$tmp"
    scp -q "$tmp" "$HOST:$REMOTE_DIR/$REMOTE_SH"
}

remote_command() {
    # The exit status goes through a file because the remote shell is
    # sh, which has neither PIPESTATUS nor pipefail. tee also means
    # pytest's stdout is a pipe rather than the pty, hence PY_COLORS.
    cat << EOF
cd '$(shquote "$REMOTE_DIR")' || exit 1
export CMD='$(shquote "$CMD")' PYTHON='$(shquote "$PYTHON")'
export PY_COLORS=1
{ sh '$REMOTE_SH' 2>&1; echo \$? > '$REMOTE_RC'; } | tee '$REMOTE_LOG'
rc=\$(cat '$REMOTE_RC')
rm -f '$REMOTE_SH' '$REMOTE_RC'
exit \$rc
EOF
}

run_remote() {
    log "building and testing on $HOST"
    # The variables in remote_command expand here, not on the remote.
    # shellcheck disable=SC2029
    if [ -t 0 ]; then
        # A pty lets ctrl-c reach the remote make and pytest. ssh can
        # only allocate one if we have one ourselves.
        ssh -t "$HOST" "$(remote_command)"
    else
        ssh "$HOST" "$(remote_command)"
    fi
}

main() {
    trap 'rm -rf "$files" "$stage" "$tmp"' EXIT
    parse_args "$@"
    sync_repo
    upload_script
    rc=0
    run_remote || rc=$?
    if [ "$rc" -eq 255 ]; then
        log "connection lost; the log is still on $HOST:$REMOTE_DIR/$REMOTE_LOG"
    else
        log "done (exit $rc), remote log: $HOST:$REMOTE_DIR/$REMOTE_LOG"
    fi
    exit "$rc"
}

main "$@"
