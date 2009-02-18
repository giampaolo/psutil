#!/usr/bin/env python
# setup.py

import sys
from distutils.core import setup, Extension


# Windows
if sys.platform.lower().startswith("win"):
    extensions = Extension('_psutil_mswindows',
                           sources=['psutil/_psutil_mswindows.c', 'psutil/arch/mswindows/process_info.c', 'psutil/arch/mswindows/security.c'],
                           define_macros=[('_WIN32_WINNT', '0x0500')],
                           libraries=["psapi", "kernel32", "advapi32", "shell32"]
                           )
# OS X
elif sys.platform.lower().startswith("darwin"):
    extensions = Extension('_psutil_osx',
                           sources = ['psutil/_psutil_osx.c', 'psutil/arch/osx/process_info.c']
                           )
# Others
else:
    extensions = None


def main():
    setup_args = dict(
        name='psutil',
        version='0.1.0',
        description='A process utilities module for Python',
        long_description="""
psutil is a module providing convenience functions for managing processes in a
portable way by using Python.""",
        author='Giampaolo Rodola, Dave Daeschler, Jay Loden',
        author_email='psutil-dev@googlegroups.com',
        url='http://code.google.com/p/psutil/',
        platforms='Platform Independent',
        license='License :: OSI Approved :: BSD License',
        packages=['psutil'],
        classifiers=[
              'Development Status :: 2 - Pre-Alpha',
              'Environment :: Console',
              'Operating System :: MacOS',
              'Operating System :: Microsoft :: Windows',
              'Operating System :: POSIX :: Linux',
              'Operating System :: OS Independent',
              'Programming Language :: Python',
              'Topic :: System :: Monitoring',
              'Topic :: System :: Systems Administration',
              'Topic :: Utilities',
              'Topic :: Software Development :: Libraries :: Python Modules',
              'Intended Audience :: Developers',
              'Intended Audience :: System Administrators',
              'License :: OSI Approved :: MIT License',
              ],
        )
    if extensions is not None:
        setup_args["ext_modules"] = [extensions]
    setup(**setup_args)


if __name__ == '__main__':
    main()
