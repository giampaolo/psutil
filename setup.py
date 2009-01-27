#!/usr/bin/env python
# setup.py

import sys
from distutils.core import setup, Extension


# Windows
if sys.platform.lower().startswith("win"):
    extensions = Extension('_psutil_mswindows',
                           sources=['psutil/_psutil_mswindows.c'],
                           define_macros=[('_WIN32_WINNT', '0x0500')],
                           libraries=["psapi", "kernel32", "advapi32", "shell32"]
                           )
# OS X
elif sys.platform.lower().startswith("darwin"):
    extensions = Extension('_psutil_osx',
                           sources = ['psutil/_psutil_osx.c']
                           )
# Others
else:
    extensions = None


def main():
    setup_args = dict(
        name='psutil',
        version='0.1.0',
        description='Python Process Management Library',
        author='Giampaolo Rodola, Dave Daeschler, Jay Loden',
        author_email='psutil-dev@googlegroups.com',
        url='http://code.google.com/p/psutil/',
        license='License :: OSI Approved :: BSD License',
        packages=['psutil'],
        )
    if extensions is not None:
        setup_args["ext_modules"] = [extensions]
    setup(**setup_args)


if __name__ == '__main__':
    main()
