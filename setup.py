#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Cross-platform lib for process and system monitoring in Python."""

from __future__ import print_function

import ast
import contextlib
import glob
import io
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import sysconfig
import tempfile
import warnings


with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    try:
        import setuptools
        from setuptools import Extension
        from setuptools import setup
    except ImportError:
        setuptools = None
        from distutils.core import Extension
        from distutils.core import setup
    try:
        from wheel.bdist_wheel import bdist_wheel
    except ImportError:
        if "CIBUILDWHEEL" in os.environ:
            raise
        bdist_wheel = None

HERE = os.path.abspath(os.path.dirname(__file__))

# ...so we can import _common.py and _compat.py
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
from _common import hilite  # NOQA
from _compat import PY3  # NOQA
from _compat import which  # NOQA


PYPY = '__pypy__' in sys.builtin_module_names
PY36_PLUS = sys.version_info[:2] >= (3, 6)
PY37_PLUS = sys.version_info[:2] >= (3, 7)
CP36_PLUS = PY36_PLUS and sys.implementation.name == "cpython"
CP37_PLUS = PY37_PLUS and sys.implementation.name == "cpython"
Py_GIL_DISABLED = sysconfig.get_config_var("Py_GIL_DISABLED")

# Test deps, installable via `pip install .[test]`.
if PY3:
    TEST_DEPS = [
        "pytest",
        "pytest-xdist",
        "setuptools",
    ]
else:
    TEST_DEPS = [
        "futures",
        "ipaddress",
        "enum34",
        "mock==1.0.1",
        "pytest-xdist",
        "pytest==4.6.11",
        "setuptools",
    ]
if WINDOWS and not PYPY:
    TEST_DEPS.append("pywin32")
    TEST_DEPS.append("wheel")
    TEST_DEPS.append("wmi")

# Development deps, installable via `pip install .[dev]`.
DEV_DEPS = [
    "black",
    "check-manifest",
    "coverage",
    "packaging",
    "pylint",
    "pyperf",
    "pypinfo",
    "pytest-cov",
    "requests",
    "rstcheck",
    "ruff",
    "sphinx",
    "sphinx_rtd_theme",
    "toml-sort",
    "twine",
    "virtualenv",
    "wheel",
]
if WINDOWS:
    DEV_DEPS.append("pyreadline")
    DEV_DEPS.append("pdbpp")

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


def get_version():
    INIT = os.path.join(HERE, 'psutil/__init__.py')
    with open(INIT) as f:
        for line in f:
            if line.startswith('__version__'):
                ret = ast.literal_eval(line.strip().split(' = ')[1])
                assert ret.count('.') == 2, ret
                for num in ret.split('.'):
                    assert num.isdigit(), ret
                return ret
        msg = "couldn't find version string"
        raise ValueError(msg)


VERSION = get_version()
macros.append(('PSUTIL_VERSION', int(VERSION.replace('.', ''))))

# Py_LIMITED_API lets us create a single wheel which works with multiple
# python versions, including unreleased ones.
if bdist_wheel and CP36_PLUS and (MACOS or LINUX) and not Py_GIL_DISABLED:
    py_limited_api = {"py_limited_api": True}
    macros.append(('Py_LIMITED_API', '0x03060000'))
elif bdist_wheel and CP37_PLUS and WINDOWS and not Py_GIL_DISABLED:
    # PyErr_SetFromWindowsErr / PyErr_SetFromWindowsErrWithFilename are
    # part of the stable API/ABI starting with CPython 3.7
    py_limited_api = {"py_limited_api": True}
    macros.append(('Py_LIMITED_API', '0x03070000'))
else:
    py_limited_api = {}


def get_long_description():
    script = os.path.join(HERE, "scripts", "internal", "convert_readme.py")
    readme = os.path.join(HERE, 'README.rst')
    p = subprocess.Popen(
        [sys.executable, script, readme],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        raise RuntimeError(stderr)
    return stdout


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


def missdeps(cmdline):
    s = "psutil could not be installed from sources"
    if not SUNOS and not which("gcc"):
        s += " because gcc is not installed. "
    else:
        s += ". Perhaps Python header files are not installed. "
    s += "Try running:\n"
    s += "  %s" % cmdline
    print(hilite(s, color="red", bold=True), file=sys.stderr)


def unix_can_compile(c_code):
    from distutils.errors import CompileError
    from distutils.unixccompiler import UnixCCompiler

    with tempfile.NamedTemporaryFile(
        suffix='.c', delete=False, mode="wt"
    ) as f:
        f.write(c_code)

    tempdir = tempfile.mkdtemp()
    try:
        compiler = UnixCCompiler()
        # https://github.com/giampaolo/psutil/pull/1568
        if os.getenv('CC'):
            compiler.set_executable('compiler_so', os.getenv('CC'))
        with silenced_output('stderr'):
            with silenced_output('stdout'):
                compiler.compile([f.name], output_dir=tempdir)
    except CompileError:
        return False
    else:
        return True
    finally:
        os.remove(f.name)
        shutil.rmtree(tempdir)


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

    if Py_GIL_DISABLED:
        macros.append(('Py_GIL_DISABLED', 1))

    ext = Extension(
        'psutil._psutil_windows',
        sources=(
            sources
            + ["psutil/_psutil_windows.c"]
            + glob.glob("psutil/arch/windows/*.c")
        ),
        define_macros=macros,
        libraries=[
            "psapi",
            "kernel32",
            "advapi32",
            "shell32",
            "netapi32",
            "ws2_32",
            "PowrProf",
            "pdh",
        ],
        # extra_compile_args=["/W 4"],
        # extra_link_args=["/DEBUG"],
        # fmt: off
        # python 2.7 compatibility requires no comma
        **py_limited_api
        # fmt: on
    )

elif MACOS:
    macros.append(("PSUTIL_OSX", 1))
    ext = Extension(
        'psutil._psutil_osx',
        sources=(
            sources
            + ["psutil/_psutil_osx.c"]
            + glob.glob("psutil/arch/osx/*.c")
        ),
        define_macros=macros,
        extra_link_args=[
            '-framework',
            'CoreFoundation',
            '-framework',
            'IOKit',
        ],
        # fmt: off
        # python 2.7 compatibility requires no comma
        **py_limited_api
        # fmt: on
    )

elif FREEBSD:
    macros.append(("PSUTIL_FREEBSD", 1))
    ext = Extension(
        'psutil._psutil_bsd',
        sources=(
            sources
            + ["psutil/_psutil_bsd.c"]
            + glob.glob("psutil/arch/bsd/*.c")
            + glob.glob("psutil/arch/freebsd/*.c")
        ),
        define_macros=macros,
        libraries=["devstat"],
        # fmt: off
        # python 2.7 compatibility requires no comma
        **py_limited_api
        # fmt: on
    )

elif OPENBSD:
    macros.append(("PSUTIL_OPENBSD", 1))
    ext = Extension(
        'psutil._psutil_bsd',
        sources=(
            sources
            + ["psutil/_psutil_bsd.c"]
            + glob.glob("psutil/arch/bsd/*.c")
            + glob.glob("psutil/arch/openbsd/*.c")
        ),
        define_macros=macros,
        libraries=["kvm"],
        # fmt: off
        # python 2.7 compatibility requires no comma
        **py_limited_api
        # fmt: on
    )

elif NETBSD:
    macros.append(("PSUTIL_NETBSD", 1))
    ext = Extension(
        'psutil._psutil_bsd',
        sources=(
            sources
            + ["psutil/_psutil_bsd.c"]
            + glob.glob("psutil/arch/bsd/*.c")
            + glob.glob("psutil/arch/netbsd/*.c")
        ),
        define_macros=macros,
        libraries=["kvm"],
        # fmt: off
        # python 2.7 compatibility requires no comma
        **py_limited_api
        # fmt: on
    )

elif LINUX:
    # see: https://github.com/giampaolo/psutil/issues/659
    if not unix_can_compile("#include <linux/ethtool.h>"):
        macros.append(("PSUTIL_ETHTOOL_MISSING_TYPES", 1))

    macros.append(("PSUTIL_LINUX", 1))
    ext = Extension(
        'psutil._psutil_linux',
        sources=(
            sources
            + ["psutil/_psutil_linux.c"]
            + glob.glob("psutil/arch/linux/*.c")
        ),
        define_macros=macros,
        # fmt: off
        # python 2.7 compatibility requires no comma
        **py_limited_api
        # fmt: on
    )

elif SUNOS:
    macros.append(("PSUTIL_SUNOS", 1))
    ext = Extension(
        'psutil._psutil_sunos',
        sources=sources
        + [
            'psutil/_psutil_sunos.c',
            'psutil/arch/solaris/v10/ifaddrs.c',
            'psutil/arch/solaris/environ.c',
        ],
        define_macros=macros,
        libraries=['kstat', 'nsl', 'socket'],
        # fmt: off
        # python 2.7 compatibility requires no comma
        **py_limited_api
        # fmt: on
    )

elif AIX:
    macros.append(("PSUTIL_AIX", 1))
    ext = Extension(
        'psutil._psutil_aix',
        sources=sources
        + [
            'psutil/_psutil_aix.c',
            'psutil/arch/aix/net_connections.c',
            'psutil/arch/aix/common.c',
            'psutil/arch/aix/ifaddrs.c',
        ],
        libraries=['perfstat'],
        define_macros=macros,
        # fmt: off
        # python 2.7 compatibility requires no comma
        **py_limited_api
        # fmt: on
    )

else:
    sys.exit('platform %s is not supported' % sys.platform)


if POSIX:
    posix_extension = Extension(
        'psutil._psutil_posix',
        define_macros=macros,
        sources=sources,
        # fmt: off
        # python 2.7 compatibility requires no comma
        **py_limited_api
        # fmt: on
    )
    if SUNOS:

        def get_sunos_update():
            # See https://serverfault.com/q/524883
            # for an explanation of Solaris /etc/release
            with open('/etc/release') as f:
                update = re.search(r'(?<=s10s_u)[0-9]{1,2}', f.readline())
                return int(update.group(0)) if update else 0

        posix_extension.libraries.append('socket')
        if platform.release() == '5.10':
            # Detect Solaris 5.10, update >= 4, see:
            # https://github.com/giampaolo/psutil/pull/1638
            if get_sunos_update() >= 4:
                # MIB compliance starts with SunOS 5.10 Update 4:
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

cmdclass = {}
if py_limited_api:

    class bdist_wheel_abi3(bdist_wheel):
        def get_tag(self):
            python, _abi, plat = bdist_wheel.get_tag(self)
            return python, "abi3", plat

    cmdclass["bdist_wheel"] = bdist_wheel_abi3


def main():
    kwargs = dict(
        name='psutil',
        version=VERSION,
        cmdclass=cmdclass,
        description=__doc__.replace('\n', ' ').strip() if __doc__ else '',
        long_description=get_long_description(),
        long_description_content_type='text/x-rst',
        # fmt: off
        keywords=[
            'ps', 'top', 'kill', 'free', 'lsof', 'netstat', 'nice', 'tty',
            'ionice', 'uptime', 'taskmgr', 'process', 'df', 'iotop', 'iostat',
            'ifconfig', 'taskset', 'who', 'pidof', 'pmap', 'smem', 'pstree',
            'monitoring', 'ulimit', 'prlimit', 'smem', 'performance',
            'metrics', 'agent', 'observability',
        ],
        # fmt: on
        author='Giampaolo Rodola',
        author_email='g.rodola@gmail.com',
        url='https://github.com/giampaolo/psutil',
        platforms='Platform Independent',
        license='BSD-3-Clause',
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
        extras_require = {
            "dev": DEV_DEPS,
            "test": TEST_DEPS,
        }
        kwargs.update(
            python_requires=(
                ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, !=3.5.*"
            ),
            extras_require=extras_require,
            zip_safe=False,
        )
    success = False
    try:
        setup(**kwargs)
        success = True
    finally:
        cmd = sys.argv[1] if len(sys.argv) >= 2 else ''
        if (
            not success
            and POSIX
            and cmd.startswith(
                ("build", "install", "sdist", "bdist", "develop")
            )
        ):
            py3 = "3" if PY3 else ""
            if LINUX:
                pyimpl = "pypy" if PYPY else "python"
                if which('dpkg'):
                    missdeps(
                        "sudo apt-get install gcc %s%s-dev" % (pyimpl, py3)
                    )
                elif which('rpm'):
                    missdeps("sudo yum install gcc %s%s-devel" % (pyimpl, py3))
                elif which('apk'):
                    missdeps(
                        "sudo apk add gcc %s%s-dev musl-dev linux-headers"
                        % (pyimpl, py3)
                    )
            elif MACOS:
                msg = (
                    "XCode (https://developer.apple.com/xcode/)"
                    " is not installed"
                )
                print(hilite(msg, color="red"), file=sys.stderr)
            elif FREEBSD:
                if which('pkg'):
                    missdeps("pkg install gcc python%s" % py3)
                elif which('mport'):  # MidnightBSD
                    missdeps("mport install gcc python%s" % py3)
            elif OPENBSD:
                missdeps("pkg_add -v gcc python%s" % py3)
            elif NETBSD:
                missdeps("pkgin install gcc python%s" % py3)
            elif SUNOS:
                missdeps(
                    "sudo ln -s /usr/bin/gcc /usr/local/bin/cc && "
                    "pkg install gcc"
                )


if __name__ == '__main__':
    main()
