============================
Installing using pip on UNIX
============================

The easiest way to install psutil on UNIX is by using pip (but first you might
need to install python header files; see later).
First install pip::

    $ wget https://bootstrap.pypa.io/get-pip.py
    $ python get-pip.py

...then run::

    $ pip install psutil

You may need to install gcc and python header files first (see later).


=====================
Installing on Windows
=====================

Just get the right installer for your Python version and architecture from:
https://pypi.python.org/pypi/psutil/#downloads
Since wheels installers are also available you may also use pip.


========================================
Compiling on Windows using Visual Studio
========================================

In order to compile psutil on Windows you'll need **Visual Studio** (**Mingw32
is no longer supported**). Depending on the Python version you'll also need a
specific VS version.
The links reported down here used to work at the time this was written
(Sep 2015):

* Python 2.6:  VS 2008 (download it from `here <http://www.microsoft.com/en-us/download/details.aspx?id=44266>`__).
* Python 2.7:  VS 2008 (download it from `here <http://www.microsoft.com/en-us/download/details.aspx?id=44266>`__).
* Python 3.3: VS 2010 (download it from `here <http://www.visualstudio.com/downloads/download-visual-studio-vs#d-2010-express>`__).
* Python 3.4: VS 2010 (download it from `here <http://www.visualstudio.com/downloads/download-visual-studio-vs#d-2010-express>`__).
* Python 3.5+: VS 2015 (download it from `here <http://www.visualstudio.com/en-au/news/vs2015-preview-vs>`__).

To build:

    setup.py build

To install:

    setup.py install

Compiling 64 bit versions of Python 2.6 and 2.7 with VS 2008 requires
Windows SDK and .NET Framework 3.5 SP1 to be installed first.
Once you have those run vcvars64.bat, then compile (see
`here <http://stackoverflow.com/questions/11072521/>`__).

===================
Installing on Linux
===================

gcc is required and so the python headers. They can easily be installed by
using the distro package manager. For example, on Debian and Ubuntu::

    $ sudo apt-get install gcc python-dev

...on Redhat and CentOS::

    $ sudo yum install gcc python-devel

Once done, you can build/install psutil with::

    $ python setup.py install


=================
Installing on OSX
=================

OSX installation from source will require gcc which you can obtain as part of
the `XcodeTools <https://developer.apple.com/downloads/?name=Xcode>`__
installer from Apple.
Once you have installed XCode you can run the standard distutils commands.
To build only::

    $ python setup.py build

To install and build::

    $ python setup.py install


=====================
Installing on FreeBSD
=====================

The same compiler used to install Python must be present on the system in order
to build modules using distutils. Assuming it is installed, you can build using
the standard distutils commands.

Build only::

    $ python setup.py build

Install and build::

    $ python setup.py install


========
Makefile
========

A makefile is available for both UNIX and Windows (make.bat).  It provides
some automations for the tasks described above and might be preferred over
using setup.py. Some useful commands:

    $ make install       # just install (in --user mode)
    $ make uninstall     # uninstall (needs pip)
    $ make setup-dev-env # install all dev deps for running tests, building doc, etc
    $ make test          # run tests
    $ make clean         # remove installation files
