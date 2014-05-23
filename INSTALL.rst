============================
Installing using pip on UNIX
============================

The easiest way to install psutil on UNIX is by using pip (but first you might
need to install python header files; see later).
First install pip:

    $ wget https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py
    python ez_setup.py

...then run:

    $ pip install psutil

You may need to install gcc and python header files first (see later).


=====================
Installing on Windows
=====================

Just get the right installer for your Python version and architecture from:
https://pypi.python.org/pypi/psutil/#downloads


==================================
Compiling on Windows using mingw32
==================================

First install mingw (http://www.mingw.org/) then add mingw "bin" folder to
environment PATH (NOTE: this assumes MinGW is installed in C:\MinGW):

    SET PATH=C:\MinGW\bin;%PATH%

You can then compile psutil by running:

    setup.py build -c mingw32

To compile and install:

    setup.py build -c mingw32 install

You can also use make.bat which automatically sets the env variable for you:

    make.bat build

FWIW I managed to compile psutil against all 32-bit Python versions but not
64 bit.


========================================
Compiling on Windows using Visual Studio
========================================

To use Visual Studio to compile psutil you must have the same version of
Visual Studio used to compile your installation of Python which is::

    Python 2.4:  VS 2003
    Python 2.5:  VS 2003
    Python 2.6:  VS 2008
    Python 2.7:  VS 2008
    Python 3.3+: VS 2010

...then run:

    setup.py build

...or:

    make.bat build

Compiling 64 bit versions of Python 2.6 and 2.7 with VS 2008 requires
Windows SDK and .NET Framework 3.5 SP1 to be installed first.
Once you have those run vcvars64.bat, then compile:
http://stackoverflow.com/questions/11072521/

If you do not have the right version of Visual Studio available then try using
MinGW instead.


===================
Installing on Linux
===================

gcc is required and so the python headers. They can easily be installed by
using the distro package manager. For example, on Debian amd Ubuntu:

    $ sudo apt-get install gcc python-dev

...on Redhat and CentOS:

    $ sudo yum install gcc python-devel

Once done, you can build/install psutil with:

    $ python setup.py install


==================
Installing on OS X
==================

OS X installation from source will require gcc which you can obtain as part of
the 'XcodeTools' installer from Apple. Then you can run the standard distutils
commands.
To build only:

    $ python setup.py build

To install and build:

    $ python setup.py install


=====================
Installing on FreeBSD
=====================

The same compiler used to install Python must be present on the system in order
to build modules using distutils. Assuming it is installed, you can build using
the standard distutils commands.

Build only:

    $ python setup.py build

Install and build:

    $ python setup.py install


========
Makefile
========

A makefile is available for both UNIX and Windows (make.bat).  It provides
some automations for the tasks described above and might be preferred over
using setup.py. With it you can::

    $ make install    # just install
    $ make uninstall  # uninstall (needs pip)
    $ make test       # run tests
    $ make clean      # remove installation files
