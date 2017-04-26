Install pip
===========

pip is the easiest way to install psutil.
It is shipped by default with Python 2.7.9+ and 3.4+. For other Python versions
you can install it manually.
On Linux or via wget::

    wget https://bootstrap.pypa.io/get-pip.py -O - | python

On OSX or via curl::

    python < <(curl -s https://bootstrap.pypa.io/get-pip.py)

On Windows, `download pip <https://pip.pypa.io/en/latest/installing/>`__, open
cmd.exe and install it::

    C:\Python27\python.exe get-pip.py

Permission issues (UNIX)
========================

The commands below assume you're running as root.
If you're not or you bump into permission errors you can either:

* prepend ``sudo``, e.g.:

::

    sudo pip install psutil

* install psutil for your user only (not at system level):

::

    pip install --user psutil

Linux
=====

Ubuntu / Debian::

    sudo apt-get install gcc python-dev python-pip
    pip install psutil

RedHat / CentOS::

    sudo yum install gcc python-devel python-pip
    pip install psutil

If you're on Python 3 use ``python3-dev`` and ``python3-pip`` instead.

Major Linux distros also provide binary distributions of psutil so, for
instance, on Ubuntu and Debian you can also do::

    sudo apt-get install python-psutil

On RedHat and CentOS::

    sudo yum install python-psutil

This is not recommended though as Linux distros usually ship older psutil
versions.

OSX
===

Install `Xcode <https://developer.apple.com/downloads/?name=Xcode>`__
first, then:

::

    pip install psutil

Windows
=======

The easiest way to install psutil on Windows is to just use the pre-compiled
exe/wheel installers hosted on
`PYPI <https://pypi.python.org/pypi/psutil/#downloads>`__ via pip::

    C:\Python27\python.exe -m pip install psutil

If you want to compile psutil from sources you'll need **Visual Studio**
(Mingw32 is no longer supported):

* Python 2.6, 2.7: `VS-2008 <http://www.microsoft.com/en-us/download/details.aspx?id=44266>`__
* Python 3.3, 3.4: `VS-2010 <http://www.visualstudio.com/downloads/download-visual-studio-vs#d-2010-express>`__
* Python 3.5+: `VS-2015 <http://www.visualstudio.com/en-au/news/vs2015-preview-vs>`__

Compiling 64 bit versions of Python 2.6 and 2.7 with VS 2008 requires
`Windows SDK and .NET Framework 3.5 SP1 <https://www.microsoft.com/en-us/download/details.aspx?id=3138>`__.
Once installed run vcvars64.bat, then you can finally compile (see
`here <http://stackoverflow.com/questions/11072521/>`__).
To compile / install psutil from sources on Windows run::

    make.bat build
    make.bat install

FreeBSD
=======

::

    pkg install python gcc
    python -m pip install psutil

OpenBSD
=======

::

    export PKG_PATH="http://ftp.openbsd.org/pub/OpenBSD/`uname -r`/packages/`arch -s`/"
    pkg_add -v python gcc
    python -m pip install psutil

NetBSD
======

::

    export PKG_PATH="ftp.netbsd.org/pub/pkgsrc/packages/NetBSD/`uname -m`/`uname -r`/All"
    pkg_add -v pkgin
    pkgin install python gcc
    python -m pip install psutil

Solaris
=======

If ``cc`` compiler is not installed create a symlink to ``gcc``:

::

    sudo ln -s /usr/bin/gcc /usr/local/bin/cc

Install:

::

    pkg install gcc
    python -m pip install psutil

Install from sources
====================

::

    git clone https://github.com/giampaolo/psutil.git
    cd psutil
    python setup.py install


Dev Guide
=========

If you plan on hacking on psutil you may want to take a look at the
`dev guide <https://github.com/giampaolo/psutil/blob/master/DEVGUIDE.rst>`__.
