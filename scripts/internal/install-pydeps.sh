#!/bin/sh

# Install python deps with uv, installing uv itself if missing. Falls back
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
        UV=uv
    elif "$PYTHON" -m uv --version > /dev/null 2>&1; then
        UV="$PYTHON -m uv"
    else
        UV=
    fi
}

install_uv() {
    install_pip
    echo "installing uv"
    # --only-binary: pickup the .whl, else fail
    PIP_BREAK_SYSTEM_PACKAGES=1 "$PYTHON" -m pip install \
        --only-binary=:all: \
        --upgrade \
        'uv>=0.5.8'
}

uv_install() {
    echo "installing $* via uv"
    user_base=$("$PYTHON" -c \
        'import sys, site; print("" if sys.prefix != sys.base_prefix else site.getuserbase())')
    if [ -n "$user_base" ]; then
        set -- --prefix "$user_base" "$@"
    fi
    $UV pip install \
        --python "$(command -v "$PYTHON")" \
        --upgrade \
        "$@"
}

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
