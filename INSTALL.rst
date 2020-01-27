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
If you aren't or you bump into permission errors you can either install psutil
for your user only::

    pip3 install --user psutil

...or prepend ``sudo`` and install it globally, e.g.::

    sudo pip3 install psutil

Linux
=====

Ubuntu / Debian::

    sudo apt-get install gcc python3-dev
    pip3 install psutil

RedHat / CentOS::

    sudo yum install gcc python3-devel
    pip3 install psutil

If you're on Python 2 use ``python-dev`` instead.

macOS
=====

Install `Xcode <https://developer.apple.com/downloads/?name=Xcode>`__ then run::

    pip3 install psutil

Windows
=======

Open a cmd.exe shell and run::

    python3 -m pip install psutil

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

    python3 setup.py build
    python3 setup.py install

FreeBSD
=======

::

    pkg install python3 gcc
    python -m pip3 install psutil

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

See: `dev guide <https://github.com/giampaolo/psutil/blob/master/docs/DEVGUIDE.rst>`__.
