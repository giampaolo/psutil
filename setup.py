#!/usr/bin/env python

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""psutil is a cross-platform library for retrieving information on
running processes and system utilization (CPU, memory, disks, network)
in Python.
"""

import os
import sys
try:
    from setuptools import setup, Extension
except ImportError:
    from distutils.core import setup, Extension


HERE = os.path.abspath(os.path.dirname(__file__))


def get_version():
    INIT = os.path.join(HERE, 'psutil/__init__.py')
    f = open(INIT, 'r')
    try:
        for line in f:
            if line.startswith('__version__'):
                ret = eval(line.strip().split(' = ')[1])
                assert ret.count('.') == 2, ret
                for num in ret.split('.'):
                    assert num.isdigit(), ret
                return ret
        else:
            raise ValueError("couldn't find version string")
    finally:
        f.close()


def get_description():
    README = os.path.join(HERE, 'README')
    f = open(README, 'r')
    try:
        return f.read()
    finally:
        f.close()


# POSIX
if os.name == 'posix':
    posix_extension = Extension(
        '_psutil_posix',
        sources=['psutil/_psutil_posix.c'],
    )
# Windows
if sys.platform.startswith("win32"):

    def get_winver():
        maj, min = sys.getwindowsversion()[0:2]
        return '0x0%s' % ((maj * 100) + min)

    extensions = [Extension(
        '_psutil_windows',
        sources=[
            'psutil/_psutil_windows.c',
            'psutil/_psutil_common.c',
            'psutil/arch/windows/process_info.c',
            'psutil/arch/windows/process_handles.c',
            'psutil/arch/windows/security.c',
        ],
        define_macros=[
            # be nice to mingw, see:
            # http://www.mingw.org/wiki/Use_more_recent_defined_functions
            ('_WIN32_WINNT', get_winver()),
            ('_AVAIL_WINVER_', get_winver()),
            # see: https://code.google.com/p/psutil/issues/detail?id=348
            ('PSAPI_VERSION', 1),
        ],
        libraries=[
            "psapi", "kernel32", "advapi32", "shell32", "netapi32", "iphlpapi",
            "wtsapi32",
        ],
        # extra_compile_args=["/Z7"],
        # extra_link_args=["/DEBUG"]
    )]
# OS X
elif sys.platform.startswith("darwin"):
    extensions = [Extension(
        '_psutil_osx',
        sources=[
            'psutil/_psutil_osx.c',
            'psutil/_psutil_common.c',
            'psutil/arch/osx/process_info.c'
        ],
        extra_link_args=[
            '-framework', 'CoreFoundation', '-framework', 'IOKit'
        ],
    ),
        posix_extension,
    ]
# FreeBSD
elif sys.platform.startswith("freebsd"):
    extensions = [Extension(
        '_psutil_bsd',
        sources=[
            'psutil/_psutil_bsd.c',
            'psutil/_psutil_common.c',
            'psutil/arch/bsd/process_info.c'
        ],
        libraries=["devstat"]),
        posix_extension,
    ]
# Linux
elif sys.platform.startswith("linux"):
    extensions = [Extension(
        '_psutil_linux',
        sources=['psutil/_psutil_linux.c']),
        posix_extension,
    ]
# Solaris
elif sys.platform.lower().startswith('sunos'):
    extensions = [Extension(
        '_psutil_sunos',
        sources=['psutil/_psutil_sunos.c'],
        libraries=['kstat', 'nsl'],),
        posix_extension,
    ]
else:
    sys.exit('platform %s is not supported' % sys.platform)


def main():
    setup_args = dict(
        name='psutil',
        version=get_version(),
        description=__doc__,
        long_description=get_description(),
        keywords=[
            'ps', 'top', 'kill', 'free', 'lsof', 'netstat', 'nice',
            'tty', 'ionice', 'uptime', 'taskmgr', 'process', 'df',
            'iotop', 'iostat', 'ifconfig', 'taskset', 'who', 'pidof',
            'pmap', 'smem', 'monitoring', 'ulimit', 'prlimit',
        ],
        author='Giampaolo Rodola',
        author_email='g.rodola <at> gmail <dot> com',
        url='http://code.google.com/p/psutil/',
        platforms='Platform Independent',
        license='BSD',
        packages=['psutil'],
        # see: python setup.py register --list-classifiers
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Environment :: Console',
            'Environment :: Win32 (MS Windows)',
            'Intended Audience :: Developers',
            'Intended Audience :: Information Technology',
            'Intended Audience :: System Administrators',
            'License :: OSI Approved :: BSD License',
            'Operating System :: MacOS :: MacOS X',
            'Operating System :: Microsoft :: Windows :: Windows NT/2000',
            'Operating System :: Microsoft',
            'Operating System :: OS Independent',
            'Operating System :: POSIX :: BSD :: FreeBSD',
            'Operating System :: POSIX :: Linux',
            'Operating System :: POSIX :: SunOS/Solaris',
            'Operating System :: POSIX',
            'Programming Language :: C',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 2.4',
            'Programming Language :: Python :: 2.5',
            'Programming Language :: Python :: 2.6',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.0',
            'Programming Language :: Python :: 3.1',
            'Programming Language :: Python :: 3.2',
            'Programming Language :: Python :: 3.3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: Implementation :: CPython',
            'Programming Language :: Python :: Implementation :: PyPy',
            'Programming Language :: Python',
            'Topic :: Software Development :: Libraries :: Python Modules',
            'Topic :: Software Development :: Libraries',
            'Topic :: System :: Benchmark',
            'Topic :: System :: Hardware',
            'Topic :: System :: Monitoring',
            'Topic :: System :: Networking :: Monitoring',
            'Topic :: System :: Networking',
            'Topic :: System :: Systems Administration',
            'Topic :: Utilities',
        ],
    )
    if extensions is not None:
        setup_args["ext_modules"] = extensions
    setup(**setup_args)

if __name__ == '__main__':
    main()
