#!/bin/sh

# Depending on the UNIX platform, install the necessary system dependencies to:
# * compile psutil
# * run those unit tests that rely on CLI tools (netstat, ps, etc.)
# NOTE: this script MUST be kept compatible with the `sh` shell.

set -e

UNAME_S=$(uname -s)

case "$UNAME_S" in
    Linux)
        if command -v apt > /dev/null 2>&1; then
            HAS_APT=true  # debian / ubuntu
        elif command -v yum > /dev/null 2>&1; then
            HAS_YUM=true  # redhat / centos
        elif command -v pacman > /dev/null 2>&1; then
            HAS_PACMAN=true  # arch
        elif command -v apk > /dev/null 2>&1; then
            HAS_APK=true  # musl
        fi
        ;;
    FreeBSD)
        FREEBSD=true
        ;;
    NetBSD)
        NETBSD=true
        ;;
    OpenBSD)
        OPENBSD=true
        ;;
    SunOS)
        SUNOS=true
        ;;
esac

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    SUDO=sudo
fi

# Function to install system dependencies
main() {
    if [ $HAS_APT ]; then
        $SUDO apt-get install -y python3-dev gcc
        $SUDO apt-get install -y net-tools coreutils util-linux sudo  # for tests
    elif [ $HAS_YUM ]; then
        $SUDO yum install -y python3-devel gcc
        $SUDO yum install -y net-tools coreutils-single util-linux sudo  # for tests
    elif [ $HAS_PACMAN ]; then
        $SUDO pacman -S --noconfirm python gcc
        $SUDO pacman -S --noconfirm net-tools coreutils util-linux sudo  # for tests
    elif [ $HAS_APK ]; then
        $SUDO apk add --no-interactive python3-dev gcc musl-dev linux-headers
        $SUDO apk add --no-interactive coreutils util-linux procps  # for tests
    elif [ $FREEBSD ]; then
        $SUDO pkg install -y python3 gcc
    elif [ $NETBSD ]; then
        $SUDO /usr/sbin/pkg_add -v pkgin
        $SUDO pkgin update
        $SUDO pkgin -y install python311-* gcc12-*
    elif [ $OPENBSD ]; then
        $SUDO pkg_add gcc python3
    elif [ $SUNOS ]; then
        $SUDO pkg install developer/gcc
    else
        echo "Unsupported platform '$UNAME_S'. Ignoring."
    fi
}

main
