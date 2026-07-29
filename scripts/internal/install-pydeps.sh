#!/bin/sh

# Install python deps with uv if available, else pip (BSD, AIX, SunOS).
# NOTE: this script MUST be kept compatible with the `sh` shell.

set -e

if [ -z "$PYTHON" ]; then
    PYTHON=python3
fi

pip_install() {
    "$PYTHON" "$(dirname "$0")/install_pip.py"
    PIP_BREAK_SYSTEM_PACKAGES=1 "$PYTHON" -m pip install \
        --trusted-host files.pythonhosted.org \
        --trusted-host pypi.org \
        --upgrade \
        --upgrade-strategy eager \
        "$@"
}

uv_install() {
    user_base=$("$PYTHON" -c \
        'import sys, site; print("" if sys.prefix != sys.base_prefix else site.getuserbase())')
    if [ -n "$user_base" ]; then
        set -- --prefix "$user_base" "$@"
    fi
    uv pip install \
        --python "$(command -v "$PYTHON")" \
        --upgrade \
        "$@"
}

if [ $# -eq 0 ]; then
    echo "usage: $0 <pkg>" >&2
    exit 1
elif command -v uv > /dev/null 2>&1; then
    uv_install "$@"
else
    pip_install "$@"
fi
