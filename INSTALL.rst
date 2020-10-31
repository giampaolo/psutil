Linux, Windows, macOS
=====================

Wheel binaries are provided for these platforms, so all you have to do is this::

    python3 -m pip install psutil

If you whish to install from sources instead, take a look at the
`dev guide <https://github.com/giampaolo/psutil/blob/master/docs/DEVGUIDE.rst>`__.

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


Install from sources
====================

::

    git clone https://github.com/giampaolo/psutil.git
    cd psutil
    python3 setup.py install

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
For other Python versions you can install it manually.
On Linux or via wget::

    wget https://bootstrap.pypa.io/get-pip.py -O - | python

On macOS or via curl::

    python < <(curl -s https://bootstrap.pypa.io/get-pip.py)

On Windows, `download pip <https://pip.pypa.io/en/latest/installing/>`__, open
cmd.exe and install it::

    C:\Python27\python.exe get-pip.py

Permission issues (UNIX)
========================

The commands below assume you're running as root.
If you aren't or you bump into permission errors you can either install psutil
for your user only::

    pip3 install --user psutil

...or prepend ``sudo`` and install it globally, e.g.::

    sudo pip3 install psutil
