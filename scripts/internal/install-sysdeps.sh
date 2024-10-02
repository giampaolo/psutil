#!/bin/sh

set -e

UNAME_S=$(uname -s)

case "$UNAME_S" in
    Linux)
        LINUX=true
        if command -v apt > /dev/null 2>&1; then
            HAS_APT=true
        elif command -v yum > /dev/null 2>&1; then
            HAS_YUM=true
        elif command -v apk > /dev/null 2>&1; then
            HAS_APK=true  # musl linux
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
esac

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    SUDO=sudo
fi

# Function to install system dependencies
main() {
    if [ "$HAS_APT" = true ]; then
        $SUDO apt-get install -y python3-dev gcc
        $SUDO apt-get install -y net-tools coreutils util-linux  # for tests
    elif [ "$HAS_YUM" = true ]; then
        $SUDO yum install -y python3-devel gcc
        $SUDO yum install -y net-tools coreutils util-linux  # for tests
    elif [ "$HAS_APK" = true ]; then
        $SUDO apk add python3-dev gcc musl-dev linux-headers coreutils procps
    elif [ "$FREEBSD" = true ]; then
        $SUDO pkg install -y gmake python3 gcc
    elif [ "$NETBSD" = true ]; then
        $SUDO /usr/sbin/pkg_add -v pkgin
        $SUDO pkgin update
        $SUDO pkgin -y install gmake python311-* gcc12-*
    elif [ "$OPENBSD" = true ]; then
        $SUDO pkg_add gmake gcc python3
    else
        echo "Unsupported platform: $UNAME_S"
    fi
}

main
