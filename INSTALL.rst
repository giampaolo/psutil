*Note: pip is the easiest way to install psutil.
It is shipped by default with Python 2.7.9+ and 3.4+. If you're using an
older Python version* `install pip <https://pip.pypa.io/en/latest/installing/>`__
*first.*

Linux
=====

Ubuntu / Debian (use `python3-dev` for python 3)::

    $ sudo apt-get install gcc python-dev
    $ pip install psutil

RedHat (use `python3-devel` for python 3)::

    $ sudo yum install gcc python-devel
    $ pip install psutil

OSX
===

Install `XcodeTools <https://developer.apple.com/downloads/?name=Xcode>`__
first, then:

::

    $ pip install psutil

Windows
=======

The easiest way to install psutil on Windows is to just use the pre-compiled
exe/wheel installers on
`PYPI <https://pypi.python.org/pypi/psutil/#downloads>`__ via pip::

    $ C:\Python27\python.exe -m pip install psutil

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

    $ make.bat build
    $ make.bat install

FreeBSD
=======

::

    $ pkg install python gcc
    $ python -m pip install psutil

OpenBSD
=======

::

    $ export PKG_PATH=http://ftp.usa.openbsd.org/pub/OpenBSD/`uname -r`/packages/`arch -s`
    $ pkg_add -v python gcc
    $ python -m pip install psutil

NetBSD
======

::

    $ export PKG_PATH="ftp.netbsd.org/pub/pkgsrc/packages/NetBSD/`uname -m`/`uname -r`/All"
    $ pkg_add -v pkgin
    $ pkgin install python gcc
    $ python -m pip install psutil

Solaris
=======

XXX

Dev Guide
=========

If you plan on hacking on psutil you may want to take a look at the
`dev guide <https://github.com/giampaolo/psutil/blob/master/DEVGUIDE.rst>`__.
