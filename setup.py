#!/usr/bin/env python

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""psutil is a cross-platform library for retrieving information on
running processes and system utilization (CPU, memory, disks, network)
in Python.
"""

import atexit
import contextlib
import io
import os
import sys
import tempfile
import platform
try:
    from setuptools import setup, Extension
except ImportError:
    from distutils.core import setup, Extension


HERE = os.path.abspath(os.path.dirname(__file__))


def get_version():
    INIT = os.path.join(HERE, 'psutil/__init__.py')
    with open(INIT, 'r') as f:
        for line in f:
            if line.startswith('__version__'):
                ret = eval(line.strip().split(' = ')[1])
                assert ret.count('.') == 2, ret
                for num in ret.split('.'):
                    assert num.isdigit(), ret
                return ret
        else:
            raise ValueError("couldn't find version string")


def get_description():
    README = os.path.join(HERE, 'README.rst')
    with open(README, 'r') as f:
        return f.read()


@contextlib.contextmanager
def silenced_output(stream_name):
    class DummyFile(io.BytesIO):
        # see: https://github.com/giampaolo/psutil/issues/678
        errors = "ignore"

        def write(self, s):
            pass

    orig = getattr(sys, stream_name)
    try:
        setattr(sys, stream_name, DummyFile())
        yield
    finally:
        setattr(sys, stream_name, orig)


VERSION = get_version()
VERSION_MACRO = ('PSUTIL_VERSION', int(VERSION.replace('.', '')))


# POSIX
if os.name == 'posix':
    posix_extension = Extension(
        'psutil._psutil_posix',
        sources=['psutil/_psutil_posix.c'])
    if sys.platform.startswith("sunos"):
        posix_extension.libraries.append('socket')
        if platform.release() == '5.10':
            posix_extension.sources.append('psutil/arch/solaris/v10/ifaddrs.c')
            posix_extension.define_macros.append(('PSUTIL_SUNOS10', 1))

# Windows
if sys.platform.startswith("win32"):

    def get_winver():
        maj, min = sys.getwindowsversion()[0:2]
        return '0x0%s' % ((maj * 100) + min)

    ext = Extension(
        'psutil._psutil_windows',
        sources=[
            'psutil/_psutil_windows.c',
            'psutil/_psutil_common.c',
            'psutil/arch/windows/process_info.c',
            'psutil/arch/windows/process_handles.c',
            'psutil/arch/windows/security.c',
            'psutil/arch/windows/inet_ntop.c',
        ],
        define_macros=[
            VERSION_MACRO,
            # be nice to mingw, see:
            # http://www.mingw.org/wiki/Use_more_recent_defined_functions
            ('_WIN32_WINNT', get_winver()),
            ('_AVAIL_WINVER_', get_winver()),
            ('_CRT_SECURE_NO_WARNINGS', None),
            # see: https://github.com/giampaolo/psutil/issues/348
            ('PSAPI_VERSION', 1),
        ],
        libraries=[
            "psapi", "kernel32", "advapi32", "shell32", "netapi32",
            "iphlpapi", "wtsapi32", "ws2_32",
        ],
        # extra_compile_args=["/Z7"],
        # extra_link_args=["/DEBUG"]
    )
    extensions = [ext]
# OS X
elif sys.platform.startswith("darwin"):
    ext = Extension(
        'psutil._psutil_osx',
        sources=[
            'psutil/_psutil_osx.c',
            'psutil/_psutil_common.c',
            'psutil/arch/osx/process_info.c'
        ],
        define_macros=[VERSION_MACRO],
        extra_link_args=[
            '-framework', 'CoreFoundation', '-framework', 'IOKit'
        ])
    extensions = [ext, posix_extension]
# FreeBSD
elif sys.platform.startswith("freebsd"):
    ext = Extension(
        'psutil._psutil_bsd',
        sources=[
            'psutil/_psutil_bsd.c',
            'psutil/_psutil_common.c',
            'psutil/arch/bsd/process_info.c'],
        define_macros=[VERSION_MACRO],
        libraries=["devstat"])
    extensions = [ext, posix_extension]
# Linux
elif sys.platform.startswith("linux"):
    def get_ethtool_macro():
        # see: https://github.com/giampaolo/psutil/issues/659
        from distutils.unixccompiler import UnixCCompiler
        from distutils.errors import CompileError

        with tempfile.NamedTemporaryFile(
                suffix='.c', delete=False, mode="wt") as f:
            f.write("#include <linux/ethtool.h>")

        @atexit.register
        def on_exit():
            try:
                os.remove(f.name)
            except OSError:
                pass

        compiler = UnixCCompiler()
        try:
            with silenced_output('stderr'):
                with silenced_output('stdout'):
                    compiler.compile([f.name])
        except CompileError:
            return ("PSUTIL_ETHTOOL_MISSING_TYPES", 1)
        else:
            return None

    ETHTOOL_MACRO = get_ethtool_macro()
    macros = [VERSION_MACRO]
    if ETHTOOL_MACRO is not None:
        macros.append(ETHTOOL_MACRO)
    ext = Extension(
        'psutil._psutil_linux',
        sources=['psutil/_psutil_linux.c'],
        define_macros=macros)
    extensions = [ext, posix_extension]
# Solaris
elif sys.platform.lower().startswith('sunos'):
    ext = Extension(
        'psutil._psutil_sunos',
        sources=['psutil/_psutil_sunos.c'],
        define_macros=[VERSION_MACRO],
        libraries=['kstat', 'nsl', 'socket'])
    extensions = [ext, posix_extension]
else:
    sys.exit('platform %s is not supported' % sys.platform)


def main():
    setup_args = dict(
        name='psutil',
        version=VERSION,
        description=__doc__.replace('\n', '').strip(),
        long_description=get_description(),
        keywords=[
            'ps', 'top', 'kill', 'free', 'lsof', 'netstat', 'nice', 'tty',
            'ionice', 'uptime', 'taskmgr', 'process', 'df', 'iotop', 'iostat',
            'ifconfig', 'taskset', 'who', 'pidof', 'pmap', 'smem', 'pstree',
            'monitoring', 'ulimit', 'prlimit',
        ],
        author='Giampaolo Rodola',
        author_email='g.rodola <at> gmail <dot> com',
        url='https://github.com/giampaolo/psutil',
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
