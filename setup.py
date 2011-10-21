#!/usr/bin/env python
#
# $Id$
#
# Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import sys
import os
try:
    from setuptools import setup, Extension
except ImportError:
    from distutils.core import setup, Extension

__ver__ = "0.3.1"

# Hack for Python 3 to tell distutils to run 2to3 against the files
# copied in the build directory before installing.
# Reference: http://docs.python.org/dev/howto/pyporting.html#during-installation
try:
    from distutils.command.build_py import build_py_2to3 as build_py
except ImportError:
    from distutils.command.build_py import build_py


if os.name == 'posix':
    posix_extension = Extension('_psutil_posix',
                                sources = ['psutil/_psutil_posix.c'])


# Windows
if sys.platform.lower().startswith("win"):

    def get_winver():
        maj,min = sys.getwindowsversion()[0:2]
        return '0x0%s' % ((maj * 100) + min)

    extensions = [Extension('_psutil_mswindows',
                            sources=['psutil/_psutil_mswindows.c',
                                     'psutil/_psutil_common.c',
                                     'psutil/arch/mswindows/process_info.c',
                                     'psutil/arch/mswindows/process_handles.c',
                                     'psutil/arch/mswindows/security.c'],
                            define_macros=[('_WIN32_WINNT', get_winver()),
                                           ('_AVAIL_WINVER_', get_winver())],
                            libraries=["psapi", "kernel32", "advapi32",
                                       "shell32", "netapi32"]
                            )]
# OS X
elif sys.platform.lower().startswith("darwin"):
    extensions = [Extension('_psutil_osx',
                            sources = ['psutil/_psutil_osx.c',
                                       'psutil/_psutil_common.c',
                                       'psutil/arch/osx/process_info.c'],
                            extra_link_args=['-framework', 'CoreFoundation',
                                             '-framework', 'IOKit']
                            ),
                  posix_extension]
# FreeBSD
elif sys.platform.lower().startswith("freebsd"):
    extensions = [Extension('_psutil_bsd',
                            sources = ['psutil/_psutil_bsd.c',
                                       'psutil/_psutil_common.c',
                                       'psutil/arch/bsd/process_info.c'],
                            libraries=["devstat"],
                            ),
                  posix_extension]
# Linux
elif sys.platform.lower().startswith("linux"):
    extensions = [Extension('_psutil_linux',
                            sources=['psutil/_psutil_linux.c'],
                            ),
                  posix_extension]

else:
    raise NotImplementedError('platform %s is not supported' % sys.platform)


def main():
    setup_args = dict(
        name='psutil',
        version=__ver__,
        download_url="http://psutil.googlecode.com/files/psutil-%s.tar.gz" % __ver__,
        description='A process utilities module for Python',
        long_description="""\
psutil is a module providing convenience functions for monitoring
system and processes in a portable way by using Python.""",
        keywords=['ps', 'top', 'kill', 'free', 'lsof', 'netstat', 'nice',
                  'tty', 'ionice', 'uptime', 'taskmgr', 'process', 'df',
                  'monitoring'],
        author='Giampaolo Rodola, Jay Loden',
        author_email='psutil@googlegroups.com',
        url='http://code.google.com/p/psutil/',
        platforms='Platform Independent',
        license='License :: OSI Approved :: BSD License',
        packages=['psutil'],
        cmdclass={'build_py':build_py},  # Python 3.X
        classifiers=[
              'Development Status :: 5 - Production/Stable',
              'Environment :: Console',
              'Operating System :: MacOS :: MacOS X',
              'Operating System :: Microsoft :: Windows :: Windows NT/2000',
              'Operating System :: POSIX :: Linux',
              'Operating System :: POSIX :: BSD :: FreeBSD',
              'Operating System :: OS Independent',
              'Programming Language :: C',
              'Programming Language :: Python',
              'Programming Language :: Python :: 2',
              'Programming Language :: Python :: 2.4',
              'Programming Language :: Python :: 2.5',
              'Programming Language :: Python :: 2.6',
              'Programming Language :: Python :: 2.7',
              'Programming Language :: Python :: 3',
              'Programming Language :: Python :: 3.0',
              'Programming Language :: Python :: 3.1',
              'Programming Language :: Python :: 3.2',
              'Topic :: System :: Monitoring',
              'Topic :: System :: Networking',
              'Topic :: System :: Benchmark',
              'Topic :: System :: Systems Administration',
              'Topic :: Utilities',
              'Topic :: Software Development :: Libraries :: Python Modules',
              'Intended Audience :: Developers',
              'Intended Audience :: System Administrators',
              'License :: OSI Approved :: MIT License',
              ],
        )
    if extensions is not None:
        setup_args["ext_modules"] = extensions

    setup(**setup_args)


if __name__ == '__main__':
    main()

