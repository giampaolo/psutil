#!/bin/sh

# Install Python deps with uv, installing uv itself if missing. Falls back
# on pip where uv ships no binary for the platform (BSD, AIX, SunOS).
# NOTE: this script MUST be kept compatible with the `sh` shell.

set -e

if [ -z "$PYTHON" ]; then
    PYTHON=python3
fi

UV=

# --- pip

install_pip() {
    echo "installing pip"
    "$PYTHON" "$(dirname "$0")/install_pip.py"
}

pip_install() {
    install_pip
    echo "installing $* via pip"
    PIP_BREAK_SYSTEM_PACKAGES=1 "$PYTHON" -m pip install \
        --upgrade \
        --upgrade-strategy eager \
        "$@"
}

# --- uv

find_uv() {
    if command -v uv > /dev/null 2>&1; then
        UV=$(command -v uv)
    else
        UV=$("$PYTHON" -c \
            'from uv import find_uv_bin; print(find_uv_bin())' 2>/dev/null) || UV=
    fi
}

install_uv() {
    install_pip || return
    echo "installing uv"
    # --only-binary: pick up the .whl, else fail
    PIP_BREAK_SYSTEM_PACKAGES=1 "$PYTHON" -m pip install \
        --only-binary=:all: \
        --upgrade \
        'uv>=0.8.8'
}

uv_install() {
    echo "installing $* via uv"
    # Outside a venv, use the user base. pip automatically falls back there
    # when the system Python is not writable; uv does not. --prefix is not
    # exactly pip --user, but avoids requiring a venv or root.
    user_base=$("$PYTHON" -c \
        'import sys, site; print("" if sys.prefix != sys.base_prefix else site.getuserbase())')
    if [ -n "$user_base" ]; then
        set -- --prefix "$user_base" "$@"
    fi
    "$UV" pip install \
        --python "$("$PYTHON" -c 'import sys; print(sys.executable)')" \
        --upgrade \
        "$@"
}

main() {
    if [ $# -eq 0 ]; then
        echo "usage: $0 <pkg>" >&2
        exit 1
    fi

    find_uv

    if [ -z "$UV" ]; then
        install_uv || echo "$0: uv unavailable on this platform, using pip" >&2
        find_uv
    fi

    if [ -n "$UV" ]; then
        uv_install "$@"
    else
        pip_install "$@"
    fi
}

main "$@"
