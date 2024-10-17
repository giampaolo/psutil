Install psutil
==============

Linux, Windows, macOS (wheels)
------------------------------

Pre-compiled wheels are distributed for these platforms, so you won't have to
install a C compiler. All you have to do is::

    pip install psutil

If wheels are not available for your platform or architecture, or you wish to
build & install psutil from sources, keep reading.

Compile psutil from sources
===========================

UNIX
----

On all UNIX systems you can use the `install-sysdeps.sh
<https://github.com/giampaolo/psutil/blob/master/scripts/internal/install-sysdeps.sh>`__
script. This will install the system dependencies necessary to compile psutil
from sources. You can invoke this script from the Makefile as::

    make install-sysdeps

After system deps are installed, you can compile & install psutil with::

    make build
    make install

...or this, which will fetch the latest source distribution from `PyPI <https://pypi.org/project/psutil/>`__::

    pip install --no-binary :all: psutil

Linux
-----

Debian / Ubuntu::

    sudo apt-get install gcc python3-dev
    pip install --no-binary :all: psutil

RedHat / CentOS::

    sudo yum install gcc python3-devel
    pip install --no-binary :all: psutil

Alpine::

    sudo apk add gcc python3-dev musl-dev linux-headers
    pip install --no-binary :all: psutil

Windows
-------

In order to build / install psutil from sources on Windows you need to install
`Visua Studio 2017 <https://visualstudio.microsoft.com/vs/older-downloads/>`__
or later (see cPython `devguide <https://devguide.python.org/getting-started/setup-building/#windows>`__'s instructions).
MinGW is not supported. Once Visual Studio is installed do::

    pip install --no-binary :all: psutil

macOS (build)
-------------

Install `Xcode <https://developer.apple.com/downloads/?name=Xcode>`__ then run::

    pip install --no-binary :all: psutil

FreeBSD
-------

::

    pkg install python3 gcc
    python3 -m pip install psutil

OpenBSD
-------

::

    export PKG_PATH=https://cdn.openbsd.org/pub/OpenBSD/`uname -r`/packages/`uname -m`/
    pkg_add -v python3 gcc
    pip install psutil

NetBSD
------

Assuming Python 3.11 (the most recent at the time of writing):

::

    export PKG_PATH="https://ftp.netbsd.org/pub/pkgsrc/packages/NetBSD/`uname -m`/`uname -r`/All"
    pkg_add -v pkgin
    pkgin install python311-* gcc12-* py311-setuptools-* py311-pip-*
    python3.11 -m pip install psutil

Sun Solaris
-----------

If ``cc`` compiler is not installed create a symbolic link to ``gcc``::

    sudo ln -s /usr/bin/gcc /usr/local/bin/cc

Install::

    pkg install gcc
    pip install psutil

Troubleshooting
===============

Install pip
-----------

Pip is shipped by default with Python 2.7.9+ and 3.4+.
If you don't have pip you can install it with wget::

    wget https://bootstrap.pypa.io/get-pip.py -O - | python3

...or with curl::

    python3 < <(curl -s https://bootstrap.pypa.io/get-pip.py)

On Windows, `download pip <https://pip.pypa.io/en/latest/installing/>`__, open
cmd.exe and install it with::

    py get-pip.py

"pip not found"
---------------

Sometimes pip is installed but it's not available in your ``PATH``
("pip command not found" or similar). Try this::

    python3 -m pip install psutil

Permission errors (UNIX)
------------------------

If you want to install psutil system-wide and you bump into permission errors
either run as root user or prepend ``sudo``::

    sudo pip install psutil
