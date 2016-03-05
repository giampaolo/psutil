.. note::
    pip is the easiest way to install psutil.
    It is shipped by default with Python 2.7.9+ and 3.4+. If you're using
    an older Python version
    `install pip <https://pip.pypa.io/en/latest/installing/>`__ first.

=====
Linux
=====

Ubuntu::

    sudo apt-get install gcc python-dev
    pip install psutil

RedHat::

    sudo yum install gcc python-devel
    pip install psutil

OSX
===

Install `XcodeTools <https://developer.apple.com/downloads/?name=Xcode>`__
first, then:

::

    pip install psutil

Windows
=======

The easiest way to install psutil on Windows is to just use the pre-compiled
exe/wheel installers on
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

XXX

OpenBSD
=======

Note - tested on OpenBSD 5.8::

    PKG_PATH=http://mirrors.nycbug.org/pub/OpenBSD/5.8/packages/i386/
    export PKG_PATH
    pkg_add -v python
    python -m pip install psutil

NetBSD
======

Note - tested on NetBSD 7.0::

    PKG_PATH="http://ftp.netbsd.org/pub/pkgsrc/packages/NetBSD/i386/7.0/All"
    export PKG_PATH
    pkg_add -v pkgin
    pkgin install python
    python -m pip install psutil

Solaris
=======

XXX

========
Makefile
========

A makefile is available for both UNIX and Windows (make.bat).  It provides
some automations for the tasks described above and might be preferred over
using setup.py. It is useful only if you want to develop for psutil.
Some useful commands::

    $ make install       # just install (in --user mode)
    $ make uninstall     # uninstall (needs pip)
    $ make setup-dev-env # install all dev deps for running tests, building doc, etc
    $ make test          # run tests
    $ make clean         # remove installation files
