#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Cross-platform lib for process and system monitoring in Python."""

from __future__ import print_function
import contextlib
import io
import os
import platform
import re
import shutil
import struct
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

# ...so we can import _common.py and _compat.py
sys.path.insert(0, os.path.join(HERE, "psutil"))

from _common import AIX  # NOQA
from _common import BSD  # NOQA
from _common import FREEBSD  # NOQA
from _common import hilite  # NOQA
from _common import LINUX  # NOQA
from _common import MACOS  # NOQA
from _common import NETBSD  # NOQA
from _common import OPENBSD  # NOQA
from _common import POSIX  # NOQA
from _common import SUNOS  # NOQA
from _common import WINDOWS  # NOQA
from _compat import PY3  # NOQA
from _compat import which  # NOQA


macros = []
if POSIX:
    macros.append(("PSUTIL_POSIX", 1))
if BSD:
    macros.append(("PSUTIL_BSD", 1))

# Needed to determine _Py_PARSE_PID in case it's missing (Python 2, PyPy).
# Taken from Lib/test/test_fcntl.py.
# XXX: not bullet proof as the (long long) case is missing.
if struct.calcsize('l') <= 8:
    macros.append(('PSUTIL_SIZEOF_PID_T', '4'))  # int
else:
    macros.append(('PSUTIL_SIZEOF_PID_T', '8'))  # long


sources = ['psutil/_psutil_common.c']
if POSIX:
    sources.append('psutil/_psutil_posix.c')


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


def missdeps(msg):
    s = hilite("C compiler or Python headers are not installed ", ok=False)
    s += hilite("on this system. Try to run:\n", ok=False)
    s += hilite(msg, ok=False, bold=True)
    print(s, file=sys.stderr)


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
            'psutil/arch/windows/process_utils.c',
            'psutil/arch/windows/process_info.c',
            'psutil/arch/windows/process_handles.c',
            'psutil/arch/windows/disk.c',
            'psutil/arch/windows/net.c',
            'psutil/arch/windows/cpu.c',
            'psutil/arch/windows/security.c',
            'psutil/arch/windows/services.c',
            'psutil/arch/windows/socks.c',
            'psutil/arch/windows/wmi.c',
        ],
        define_macros=macros,
        libraries=[
            "psapi", "kernel32", "advapi32", "shell32", "netapi32",
            "wtsapi32", "ws2_32", "PowrProf", "pdh",
        ],
        # extra_compile_args=["/W 4"],
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

        output_dir = tempfile.mkdtemp()
        try:
            compiler = UnixCCompiler()
            # https://github.com/giampaolo/psutil/pull/1568
            if os.getenv('CC'):
                compiler.set_executable('compiler_so', os.getenv('CC'))
            with silenced_output('stderr'):
                with silenced_output('stdout'):
                    compiler.compile([f.name], output_dir=output_dir)
        except CompileError:
            return ("PSUTIL_ETHTOOL_MISSING_TYPES", 1)
        else:
            return None
        finally:
            os.remove(f.name)
            shutil.rmtree(output_dir)

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
        def get_sunos_update():
            # See https://serverfault.com/q/524883
            # for an explanation of Solaris /etc/release
            with open('/etc/release') as f:
                update = re.search(r'(?<=s10s_u)[0-9]{1,2}', f.readline())
                if update is None:
                    return 0
                else:
                    return int(update.group(0))

        posix_extension.libraries.append('socket')
        if platform.release() == '5.10':
            # Detect Solaris 5.10, update >= 4, see:
            # https://github.com/giampaolo/psutil/pull/1638
            if get_sunos_update() >= 4:
                # MIB compliancy starts with SunOS 5.10 Update 4:
                posix_extension.define_macros.append(('NEW_MIB_COMPLIANT', 1))
            posix_extension.sources.append('psutil/arch/solaris/v10/ifaddrs.c')
            posix_extension.define_macros.append(('PSUTIL_SUNOS10', 1))
        else:
            # Other releases are by default considered to be new mib compliant.
            posix_extension.define_macros.append(('NEW_MIB_COMPLIANT', 1))
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
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Environment :: Console',
            'Environment :: Win32 (MS Windows)',
            'Intended Audience :: Developers',
            'Intended Audience :: Information Technology',
            'Intended Audience :: System Administrators',
            'License :: OSI Approved :: BSD License',
            'Operating System :: MacOS :: MacOS X',
            'Operating System :: Microsoft :: Windows :: Windows 10',
            'Operating System :: Microsoft :: Windows :: Windows 7',
            'Operating System :: Microsoft :: Windows :: Windows 8',
            'Operating System :: Microsoft :: Windows :: Windows 8.1',
            'Operating System :: Microsoft :: Windows :: Windows Server 2003',
            'Operating System :: Microsoft :: Windows :: Windows Server 2008',
            'Operating System :: Microsoft :: Windows :: Windows Vista',
            'Operating System :: Microsoft',
            'Operating System :: OS Independent',
            'Operating System :: POSIX :: AIX',
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
            'Programming Language :: Python :: Implementation :: CPython',
            'Programming Language :: Python :: Implementation :: PyPy',
            'Programming Language :: Python',
            'Topic :: Software Development :: Libraries :: Python Modules',
            'Topic :: Software Development :: Libraries',
            'Topic :: System :: Benchmark',
            'Topic :: System :: Hardware :: Hardware Drivers',
            'Topic :: System :: Hardware',
            'Topic :: System :: Monitoring',
            'Topic :: System :: Networking :: Monitoring :: Hardware Watchdog',
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
            extras_require=extras_require,
            zip_safe=False,
        )
    success = False
    try:
        setup(**kwargs)
        success = True
    finally:
        if not success and POSIX and not which('gcc'):
            py3 = "3" if PY3 else ""
            if LINUX:
                if which('dpkg'):
                    missdeps("sudo apt-get install gcc python%s-dev" % py3)
                elif which('rpm'):
                    missdeps("sudo yum install gcc python%s-devel" % py3)
            elif MACOS:
                print(hilite("XCode (https://developer.apple.com/xcode/) "
                             "is not installed"), ok=False, file=sys.stderr)
            elif FREEBSD:
                missdeps("pkg install gcc python%s" % py3)
            elif OPENBSD:
                missdeps("pkg_add -v gcc python%s" % py3)
            elif NETBSD:
                missdeps("pkgin install gcc python%s" % py3)
            elif SUNOS:
                missdeps("sudo ln -s /usr/bin/gcc /usr/local/bin/cc && "
                         "pkg install gcc")
        elif not success and WINDOWS:
            if PY3:
                ur = "http://www.visualstudio.com/en-au/news/vs2015-preview-vs"
            else:
                ur = "http://www.microsoft.com/en-us/download/"
                ur += "details.aspx?id=44266"
            s = "VisualStudio is not installed; get it from %s" % ur
            print(hilite(s, ok=False), file=sys.stderr)


if __name__ == '__main__':
    main()
