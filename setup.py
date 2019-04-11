#!/usr/bin/env python

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Cross-platform lib for process and system monitoring in Python."""

import contextlib
import io
import os
import platform
import sys
import tempfile
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    try:
        import setuptools
        from setuptools import setup, Extension
    except ImportError:
        setuptools = None
        from distutils.core import setup, Extension

HERE = os.path.abspath(os.path.dirname(__file__))

# ...so we can import _common.py
sys.path.insert(0, os.path.join(HERE, "psutil"))

from _common import AIX  # NOQA
from _common import BSD  # NOQA
from _common import FREEBSD  # NOQA
from _common import LINUX  # NOQA
from _common import MACOS  # NOQA
from _common import NETBSD  # NOQA
from _common import OPENBSD  # NOQA
from _common import POSIX  # NOQA
from _common import SUNOS  # NOQA
from _common import WINDOWS  # NOQA


macros = []
if POSIX:
    macros.append(("PSUTIL_POSIX", 1))
if BSD:
    macros.append(("PSUTIL_BSD", 1))

sources = ['psutil/_psutil_common.c']
if POSIX:
    sources.append('psutil/_psutil_posix.c')

tests_require = []
if sys.version_info[:2] <= (2, 6):
    tests_require.append('unittest2')
if sys.version_info[:2] <= (2, 7):
    tests_require.append('mock')
if sys.version_info[:2] <= (3, 2):
    tests_require.append('ipaddress')

extras_require = {}
if sys.version_info[:2] <= (3, 3):
    extras_require.update(dict(enum='enum34'))


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
        raise ValueError("couldn't find version string")


VERSION = get_version()
macros.append(('PSUTIL_VERSION', int(VERSION.replace('.', ''))))


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


if WINDOWS:
    def get_winver():
        maj, min = sys.getwindowsversion()[0:2]
        return '0x0%s' % ((maj * 100) + min)

    if sys.getwindowsversion()[0] < 6:
        msg = "this Windows version is too old (< Windows Vista); "
        msg += "psutil 3.4.2 is the latest version which supports Windows "
        msg += "2000, XP and 2003 server"
        raise RuntimeError(msg)

    macros.append(("PSUTIL_WINDOWS", 1))
    macros.extend([
        # be nice to mingw, see:
        # http://www.mingw.org/wiki/Use_more_recent_defined_functions
        ('_WIN32_WINNT', get_winver()),
        ('_AVAIL_WINVER_', get_winver()),
        ('_CRT_SECURE_NO_WARNINGS', None),
        # see: https://github.com/giampaolo/psutil/issues/348
        ('PSAPI_VERSION', 1),
    ])

    ext = Extension(
        'psutil._psutil_windows',
        sources=sources + [
            'psutil/_psutil_windows.c',
            'psutil/arch/windows/process_info.c',
            'psutil/arch/windows/process_handles.c',
            'psutil/arch/windows/security.c',
            'psutil/arch/windows/inet_ntop.c',
            'psutil/arch/windows/services.c',
            'psutil/arch/windows/global.c',
            'psutil/arch/windows/wmi.c',
        ],
        define_macros=macros,
        libraries=[
            "psapi", "kernel32", "advapi32", "shell32", "netapi32",
            "wtsapi32", "ws2_32", "PowrProf", "pdh",
        ],
        # extra_compile_args=["/Z7"],
        # extra_link_args=["/DEBUG"]
    )

elif MACOS:
    macros.append(("PSUTIL_OSX", 1))
    ext = Extension(
        'psutil._psutil_osx',
        sources=sources + [
            'psutil/_psutil_osx.c',
            'psutil/arch/osx/process_info.c',
        ],
        define_macros=macros,
        extra_link_args=[
            '-framework', 'CoreFoundation', '-framework', 'IOKit'
        ])

elif FREEBSD:
    macros.append(("PSUTIL_FREEBSD", 1))
    ext = Extension(
        'psutil._psutil_bsd',
        sources=sources + [
            'psutil/_psutil_bsd.c',
            'psutil/arch/freebsd/specific.c',
            'psutil/arch/freebsd/sys_socks.c',
            'psutil/arch/freebsd/proc_socks.c',
        ],
        define_macros=macros,
        libraries=["devstat"])

elif OPENBSD:
    macros.append(("PSUTIL_OPENBSD", 1))
    ext = Extension(
        'psutil._psutil_bsd',
        sources=sources + [
            'psutil/_psutil_bsd.c',
            'psutil/arch/openbsd/specific.c',
        ],
        define_macros=macros,
        libraries=["kvm"])

elif NETBSD:
    macros.append(("PSUTIL_NETBSD", 1))
    ext = Extension(
        'psutil._psutil_bsd',
        sources=sources + [
            'psutil/_psutil_bsd.c',
            'psutil/arch/netbsd/specific.c',
            'psutil/arch/netbsd/socks.c',
        ],
        define_macros=macros,
        libraries=["kvm"])

elif LINUX:
    def get_ethtool_macro():
        # see: https://github.com/giampaolo/psutil/issues/659
        from distutils.unixccompiler import UnixCCompiler
        from distutils.errors import CompileError

        with tempfile.NamedTemporaryFile(
                suffix='.c', delete=False, mode="wt") as f:
            f.write("#include <linux/ethtool.h>")

        try:
            compiler = UnixCCompiler()
            with silenced_output('stderr'):
                with silenced_output('stdout'):
                    compiler.compile([f.name])
        except CompileError:
            return ("PSUTIL_ETHTOOL_MISSING_TYPES", 1)
        else:
            return None
        finally:
            try:
                os.remove(f.name)
            except OSError:
                pass

    macros.append(("PSUTIL_LINUX", 1))
    ETHTOOL_MACRO = get_ethtool_macro()
    if ETHTOOL_MACRO is not None:
        macros.append(ETHTOOL_MACRO)
    ext = Extension(
        'psutil._psutil_linux',
        sources=sources + ['psutil/_psutil_linux.c'],
        define_macros=macros)

elif SUNOS:
    macros.append(("PSUTIL_SUNOS", 1))
    ext = Extension(
        'psutil._psutil_sunos',
        sources=sources + [
            'psutil/_psutil_sunos.c',
            'psutil/arch/solaris/v10/ifaddrs.c',
            'psutil/arch/solaris/environ.c'
        ],
        define_macros=macros,
        libraries=['kstat', 'nsl', 'socket'])
# AIX
elif AIX:
    macros.append(("PSUTIL_AIX", 1))
    ext = Extension(
        'psutil._psutil_aix',
        sources=sources + [
            'psutil/_psutil_aix.c',
            'psutil/arch/aix/net_connections.c',
            'psutil/arch/aix/common.c',
            'psutil/arch/aix/ifaddrs.c'],
        libraries=['perfstat'],
        define_macros=macros)

else:
    sys.exit('platform %s is not supported' % sys.platform)


if POSIX:
    posix_extension = Extension(
        'psutil._psutil_posix',
        define_macros=macros,
        sources=sources)
    if SUNOS:
        posix_extension.libraries.append('socket')
        if platform.release() == '5.10':
            posix_extension.sources.append('psutil/arch/solaris/v10/ifaddrs.c')
            posix_extension.define_macros.append(('PSUTIL_SUNOS10', 1))
    elif AIX:
        posix_extension.sources.append('psutil/arch/aix/ifaddrs.c')

    extensions = [ext, posix_extension]
else:
    extensions = [ext]


def main():
    kwargs = dict(
        name='psutil',
        version=VERSION,
        description=__doc__ .replace('\n', ' ').strip() if __doc__ else '',
        long_description=get_description(),
        keywords=[
            'ps', 'top', 'kill', 'free', 'lsof', 'netstat', 'nice', 'tty',
            'ionice', 'uptime', 'taskmgr', 'process', 'df', 'iotop', 'iostat',
            'ifconfig', 'taskset', 'who', 'pidof', 'pmap', 'smem', 'pstree',
            'monitoring', 'ulimit', 'prlimit', 'smem', 'performance',
            'metrics', 'agent', 'observability',
        ],
        author='Giampaolo Rodola',
        author_email='g.rodola@gmail.com',
        url='https://github.com/giampaolo/psutil',
        platforms='Platform Independent',
        license='BSD',
        packages=['psutil', 'psutil.tests'],
        ext_modules=extensions,
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
            'Operating System :: POSIX :: BSD :: NetBSD',
            'Operating System :: POSIX :: BSD :: OpenBSD',
            'Operating System :: POSIX :: BSD',
            'Operating System :: POSIX :: Linux',
            'Operating System :: POSIX :: SunOS/Solaris',
            'Operating System :: POSIX',
            'Programming Language :: C',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 2.6',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
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
            'Topic :: System :: Operating System',
            'Topic :: System :: Systems Administration',
            'Topic :: Utilities',
        ],
    )
    if setuptools is not None:
        kwargs.update(
            python_requires=">=2.6, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*",
            test_suite="psutil.tests.get_suite",
            tests_require=tests_require,
            extras_require=extras_require,
            zip_safe=False,
        )
    setup(**kwargs)


if __name__ == '__main__':
    main()
