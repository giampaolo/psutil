Install psutil
==============

Linux, Windows, macOS (wheels)
------------------------------

Pre-compiled wheels are distributed for these platforms, so you won't have to
install a C compiler. All you have to do is::

    pip install psutil

If wheels are not available for your platform or architecture, or you whish to
build & install psutil from sources, keep reading.

Linux (build)
-------------

Ubuntu / Debian::

    sudo apt-get install gcc python3-dev
    pip install --no-binary :all: psutil

RedHat / CentOS::

    sudo yum install gcc python3-devel
    pip install --no-binary :all: psutil

Windows (build)
---------------

In order to install psutil from sources on Windows you need Visual Studio
(MinGW is not supported).
Here's a couple of guides describing how to do it: `link <https://blog.ionelmc.ro/2014/12/21/compiling-python-extensions-on-windows/>`__
and `link <https://cpython-core-tutorial.readthedocs.io/en/latest/build_cpython_windows.html>`__.
Once VS is installed do::

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

    export PKG_PATH=http://ftp.eu.openbsd.org/pub/OpenBSD/`uname -r`/packages/`uname -m`/
    pkg_add -v python gcc
    pip install psutil

NetBSD
------

::

    export PKG_PATH="ftp.netbsd.org/pub/pkgsrc/packages/NetBSD/`uname -m`/`uname -r`/All"
    pkg_add -v pkgin
    pkgin install python3 gcc
    pip install psutil

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
If you don't have pip you can install with wget::

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
