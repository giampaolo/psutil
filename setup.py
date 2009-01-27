#!/usr/bin/env python
# setup.py

import sys
from distutils.core import setup, Extension


# Windows
if sys.platform.lower().startswith("win"):
    module = Extension('_psutil_mswindows',
                       sources=['psutil/_psutil_mswindows.c'],
                       define_macros=[('_WIN32_WINNT', '0x0500')],
                       libraries=["psapi", "kernel32", "advapi32", "shell32"])

    setup(name='PsutilMswindows',
         version='1.0',
         description='Windows implementation',
         ext_modules=[module]
         )


# OS X
if sys.platform.lower().startswith("darwin"):
    module = Extension('psutil/_psutil_osx',
                       sources = ['psutil/_psutil_osx.c'],)

    setup(name='PsutilOSX',
          version='1.0',
          description='OS X implementation',
          ext_modules=[module]
          )

if sys.platform.lower().startswith("linux"):
    # build Linux module, no compilation needed here
    setup(name='psutil',
          version='1.0',
          description='Linux implementation',
          packages=['psutil']
          )


setup(name='psutil',
      version='1.0',
      description='Python Process Management Library',
      author='Giampaolo Rodola, Dave Daeschler, Jay Loden',
      author_email='psutil-dev@googlegroups.com',
      url='http://code.google.com/p/psutil/',
      packages=['psutil'],
      )
