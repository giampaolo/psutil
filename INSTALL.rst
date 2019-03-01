Install pip
===========

pip is the easiest way to install psutil. It is shipped by default with Python
2.7.9+ and 3.4+. For other Python versions you can install it manually.
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
If you're not or you bump into permission errors you can either install psutil
for your user only::

    pip install --user psutil

...or prepend ``sudo``, e.g.::

    sudo pip install psutil

Linux
=====

Ubuntu / Debian::

    sudo apt-get install gcc python-dev python-pip
    pip install psutil

RedHat / CentOS::

    sudo yum install gcc python-devel python-pip
    pip install psutil

If you're on Python 3 use ``python3-dev`` and ``python3-pip`` instead.

macOS
=====

Install `Xcode <https://developer.apple.com/downloads/?name=Xcode>`__ then run::

    pip install psutil

Windows
=======

Open a cmd.exe shell and run::

    python -m pip install psutil

This assumes "python" is in your PATH. If not, specify the full python.exe
path.

In order to compile psutil from sources you'll need **Visual Studio** (Mingw32
is not supported).
This  `blog post <https://blog.ionelmc.ro/2014/12/21/compiling-python-extensions-on-windows/>`__
provides numerous info on how to properly set up VS. The needed VS versions are:

* Python 2.6, 2.7: `VS-2008 <http://www.microsoft.com/en-us/download/details.aspx?id=44266>`__
* Python 3.4: `VS-2010 <http://www.visualstudio.com/downloads/download-visual-studio-vs#d-2010-express>`__
* Python 3.5+: `VS-2015 <http://www.visualstudio.com/en-au/news/vs2015-preview-vs>`__

Compiling 64 bit versions of Python 2.6 and 2.7 with VS 2008 requires
`Windows SDK and .NET Framework 3.5 SP1 <https://www.microsoft.com/en-us/download/details.aspx?id=3138>`__.
Once installed run `vcvars64.bat`
(see `here <http://stackoverflow.com/questions/11072521/>`__).
Once VS is setup open a cmd.exe shell, cd into psutil directory and run::

    python setup.py build
    python setup.py install

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

If you wan to hacking or contribute on psutil continue reading the
`dev guide <https://github.com/giampaolo/psutil/blob/master/docs/DEVGUIDE.rst>`__
