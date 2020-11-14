Linux, Windows, macOS (wheels)
==============================

psutil makes extensive use of C extension modules, meaning a C compiler is
required.
For these 3 platforms though, pre-compiled cPython wheels are provided on each
psutil release, so all you have to do is this::

    pip3 install psutil

If wheels are not available and you whish to install from sources, keep reading.

Linux (install from sources)
============================

Ubuntu / Debian::

    sudo apt-get install gcc python3-dev
    pip3 install --user psutil --no-binary :all:

RedHat / CentOS::

    sudo yum install gcc python3-devel
    pip3 install --user psutil --no-binary :all:

Windows (install from sources)
==============================

In order to compile psutil on Windows you'll need **Visual Studio**.
Here's a couple of guides describing how to do it: `1 <https://blog.ionelmc.ro/2014/12/21/compiling-python-extensions-on-windows/>`__
and `2 <https://cpython-core-tutorial.readthedocs.io/en/latest/build_cpython_windows.html>`__. And then::

    pip3 install --user psutil --no-binary :all:

Note that MinGW compiler is not supported.

FreeBSD
=======

::

    pkg install python3 gcc
    python3 -m pip3 install psutil

OpenBSD
=======

::

    export PKG_PATH=http://ftp.eu.openbsd.org/pub/OpenBSD/`uname -r`/packages/`uname -m`/
    pkg_add -v python gcc
    python3 -m pip install psutil

NetBSD
======

::

    export PKG_PATH="ftp.netbsd.org/pub/pkgsrc/packages/NetBSD/`uname -m`/`uname -r`/All"
    pkg_add -v pkgin
    pkgin install python3 gcc
    python3 -m pip install psutil

Solaris
=======

If ``cc`` compiler is not installed create a symlink to ``gcc``::

    sudo ln -s /usr/bin/gcc /usr/local/bin/cc

Install::

    pkg install gcc
    python3 -m pip install psutil

Testing installation
====================

::

    python3 -m psutil.tests

Dev Guide
=========

`Link <https://github.com/giampaolo/psutil/blob/master/docs/DEVGUIDE.rst>`__.

Install pip
===========

Pip is shipped by default with Python 2.7.9+ and 3.4+.
If you don't have it you can install with wget::

    wget https://bootstrap.pypa.io/get-pip.py -O - | python3

...ow with curl::

    python3 < <(curl -s https://bootstrap.pypa.io/get-pip.py)

On Windows, `download pip <https://pip.pypa.io/en/latest/installing/>`__, open
cmd.exe and install it::

    C:\Python27\python.exe get-pip.py

Permission issues (UNIX)
========================

If you bump into permission errors you have two options.
Install psutil for your user only::

    pip3 install --user psutil

...or prepend ``sudo`` and install it at system level::

    sudo pip3 install psutil
