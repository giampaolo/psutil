#!/bin/sh

# Install the system dependencies needed to compile psutil. With --test-only
# install CLI tools needed by unit tests.
# NOTE: this script MUST be kept compatible with the `sh` shell.

set -e

if [ "$1" = "--test-only" ]; then
    TEST_ONLY=true
fi

UNAME_S=$(uname -s)

case "$UNAME_S" in
    Linux)
        if command -v apt-get > /dev/null 2>&1; then
            HAS_APT=true  # debian / ubuntu
        elif command -v yum > /dev/null 2>&1; then
            HAS_YUM=true  # redhat / centos
        elif command -v dnf > /dev/null 2>&1; then
            HAS_DNF=true  # fedora
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

# Deps needed to compile psutil.
install_build_deps() {
    # Debian / Ubuntu
    if [ $HAS_APT ]; then
        $SUDO apt-get install -y python3-dev gcc
    # Redhat
    elif [ $HAS_YUM ]; then
        $SUDO yum install -y python3-devel gcc
    # Fedora
    elif [ $HAS_DNF ]; then
        $SUDO dnf install -y python3-devel gcc
    # Arch
    elif [ $HAS_PACMAN ]; then
        $SUDO pacman -S --noconfirm python gcc
    # Alpine
    elif [ $HAS_APK ]; then
        $SUDO apk add --no-interactive python3-dev gcc musl-dev linux-headers
    # FreeBSD
    elif [ $FREEBSD ]; then
        $SUDO pkg install -y python3  # no gcc: base cc is clang, and that's what python uses
    # NetBSD
    elif [ $NETBSD ]; then
        if ! command -v pkgin > /dev/null 2>&1; then
            : "${PKG_PATH:=https://cdn.netbsd.org/pub/pkgsrc/packages/NetBSD/$(uname -m)/$(uname -r)/All}"
            $SUDO env PKG_PATH="$PKG_PATH" /usr/sbin/pkg_add -v pkgin
        fi
        $SUDO pkgin update
        $SUDO pkgin -y install 'python311-*'  # no gcc12: base gcc compiles psutil just fine
        if [ ! -e /usr/pkg/bin/python3 ]; then
            $SUDO ln -s /usr/pkg/bin/python3.11 /usr/pkg/bin/python3
        fi
    # OpenBSD
    elif [ $OPENBSD ]; then
        $SUDO pkg_add python%3  # there's no "python3" package, and no gcc: base cc is clang
    # SunOS
    elif [ $SUNOS ]; then
        $SUDO pkg install developer/gcc
    else
        echo "Unsupported platform '$UNAME_S'. Ignoring."
    fi
}

# CLI tools needed by unit tests.
install_test_deps() {
    # Debian / Ubuntu
    if [ $HAS_APT ]; then
        $SUDO apt-get install -y net-tools coreutils util-linux sudo procps
    # Redhat
    elif [ $HAS_YUM ]; then
        $SUDO yum install -y net-tools coreutils-single util-linux sudo procps-ng
    # Fedora
    elif [ $HAS_DNF ]; then
        $SUDO dnf install -y net-tools coreutils util-linux sudo procps-ng
    # Arch
    elif [ $HAS_PACMAN ]; then
        $SUDO pacman -S --noconfirm net-tools coreutils util-linux sudo procps-ng
    # Alpine
    elif [ $HAS_APK ]; then
        $SUDO apk add --no-interactive coreutils util-linux procps
    else
        echo "No test deps to install on '$UNAME_S'. Ignoring."
    fi
}

main() {
    if [ $TEST_ONLY ]; then
        install_test_deps
    else
        install_build_deps
    fi
}

main
