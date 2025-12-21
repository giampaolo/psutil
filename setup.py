#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Cross-platform lib for process and system monitoring in Python.

NOTE: the syntax of this script MUST be kept compatible with Python 2.7.
"""

from __future__ import print_function

import ast
import contextlib
import glob
import io
import os
import shutil
import struct
import subprocess
import sys
import sysconfig
import tempfile
import textwrap
import warnings

if sys.version_info[0] == 2:
    sys.exit(textwrap.dedent("""\
        As of version 7.0.0 psutil no longer supports Python 2.7, see:
        https://github.com/giampaolo/psutil/issues/2480
        Latest version supporting Python 2.7 is psutil 6.1.X.
        Install it with:

            python2 -m pip install psutil==6.1.*\
        """))


with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    try:
        import setuptools
        from setuptools import Extension
        from setuptools import setup
    except ImportError:
        if "CIBUILDWHEEL" in os.environ:
            raise
        setuptools = None
        from distutils.core import Extension
        from distutils.core import setup


HERE = os.path.abspath(os.path.dirname(__file__))

# ...so we can import _common.py
sys.path.insert(0, os.path.join(HERE, "psutil"))

from _common import AIX  # noqa: E402
from _common import BSD  # noqa: E402
from _common import FREEBSD  # noqa: E402
from _common import LINUX  # noqa: E402
from _common import MACOS  # noqa: E402
from _common import NETBSD  # noqa: E402
from _common import OPENBSD  # noqa: E402
from _common import POSIX  # noqa: E402
from _common import SUNOS  # noqa: E402
from _common import WINDOWS  # noqa: E402
from _common import hilite  # noqa: E402

PYPY = '__pypy__' in sys.builtin_module_names
PY36_PLUS = sys.version_info[:2] >= (3, 6)
PY37_PLUS = sys.version_info[:2] >= (3, 7)
CP36_PLUS = PY36_PLUS and sys.implementation.name == "cpython"
CP37_PLUS = PY37_PLUS and sys.implementation.name == "cpython"
Py_GIL_DISABLED = sysconfig.get_config_var("Py_GIL_DISABLED")

# Test deps, installable via `pip install .[test]` or
# `make install-pydeps-test`.
TEST_DEPS = [
    "psleak",
    "pytest",
    "pytest-instafail",
    "pytest-xdist",
    "setuptools",
]
if WINDOWS and not hasattr(sys, "pypy_version_info"):
    TEST_DEPS.extend([
        "pywin32",
        "wheel",
        "wmi",
    ])

# Development deps, installable via `pip install .[dev]` or
# `make install-pydeps-dev`.
DEV_DEPS = TEST_DEPS + [
    "abi3audit",
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
    "validate-pyproject[all]",
    "virtualenv",
    "vulture",
    "wheel",
]

if WINDOWS:
    DEV_DEPS.extend([
        "colorama",
        "pyreadline3",
    ])

# The pre-processor macros that are passed to the C compiler when
# building the extension.
macros = []

if POSIX:
    macros.append(("PSUTIL_POSIX", 1))
if BSD:
    macros.append(("PSUTIL_BSD", 1))

# Needed to determine _Py_PARSE_PID in case it's missing (PyPy).
# Taken from Lib/test/test_fcntl.py.
# XXX: not bullet proof as the (long long) case is missing.
if struct.calcsize('l') <= 8:
    macros.append(('PSUTIL_SIZEOF_PID_T', '4'))  # int
else:
    macros.append(('PSUTIL_SIZEOF_PID_T', '8'))  # long


sources = glob.glob("psutil/arch/all/*.c")
if POSIX:
    sources.extend(glob.glob("psutil/arch/posix/*.c"))


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
if setuptools and CP36_PLUS and (MACOS or LINUX) and not Py_GIL_DISABLED:
    py_limited_api = {"py_limited_api": True}
    options = {"bdist_wheel": {"py_limited_api": "cp36"}}
    macros.append(('Py_LIMITED_API', '0x03060000'))
elif setuptools and CP37_PLUS and WINDOWS and not Py_GIL_DISABLED:
    # PyErr_SetFromWindowsErr / PyErr_SetFromWindowsErrWithFilename are
    # part of the stable API/ABI starting with CPython 3.7
    py_limited_api = {"py_limited_api": True}
    options = {"bdist_wheel": {"py_limited_api": "cp37"}}
    macros.append(('Py_LIMITED_API', '0x03070000'))
else:
    py_limited_api = {}
    options = {}


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
def silenced_output():
    with contextlib.redirect_stdout(io.StringIO()):
        with contextlib.redirect_stderr(io.StringIO()):
            yield


def has_python_h():
    include_dir = sysconfig.get_path("include")
    return os.path.exists(os.path.join(include_dir, "Python.h"))


def get_sysdeps():
    if LINUX:
        pyimpl = "pypy" if PYPY else "python"
        if shutil.which("dpkg"):
            return "sudo apt-get install gcc {}3-dev".format(pyimpl)
        elif shutil.which("rpm"):
            return "sudo yum install gcc {}3-devel".format(pyimpl)
        elif shutil.which("pacman"):
            return "sudo pacman -S gcc python"
        elif shutil.which("apk"):
            return "sudo apk add gcc {}3-dev musl-dev linux-headers".format(
                pyimpl
            )
    elif MACOS:
        return "xcode-select --install"
    elif FREEBSD:
        if shutil.which("pkg"):
            return "pkg install gcc python3"
        elif shutil.which("mport"):  # MidnightBSD
            return "mport install gcc python3"
    elif OPENBSD:
        return "pkg_add -v gcc python3"
    elif NETBSD:
        return "pkgin install gcc python3"
    elif SUNOS:
        return "pkg install gcc"


def print_install_instructions():
    reasons = []
    if not shutil.which("gcc"):
        reasons.append("gcc is not installed.")
    if not has_python_h():
        reasons.append("Python header files are not installed.")
    if reasons:
        sysdeps = get_sysdeps()
        if sysdeps:
            s = "psutil could not be compiled from sources. "
            s += " ".join(reasons)
            s += " Try running:\n"
            s += "  {}".format(sysdeps)
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
        with silenced_output():
            compiler.compile([f.name], output_dir=tempdir)
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
        return "0x0{}".format((maj * 100) + min)

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
            "advapi32",
            "kernel32",
            "netapi32",
            "pdh",
            "PowrProf",
            "psapi",
            "shell32",
            "ws2_32",
        ],
        # extra_compile_args=["/W 4"],
        # extra_link_args=["/DEBUG"],
        # fmt: off
        # python 2.7 compatibility requires no comma
        **py_limited_api
        # fmt: on
    )

elif MACOS:
    macros.extend([("PSUTIL_OSX", 1), ("PSUTIL_MACOS", 1)])
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
        libraries=["kvm", "jemalloc"],
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
        sources=(
            sources
            + ["psutil/_psutil_sunos.c"]
            + glob.glob("psutil/arch/sunos/*.c")
        ),
        define_macros=macros,
        libraries=["kstat", "nsl", "socket"],
        # fmt: off
        # python 2.7 compatibility requires no comma
        **py_limited_api
        # fmt: on
    )

elif AIX:
    macros.append(("PSUTIL_AIX", 1))

    ext = Extension(
        'psutil._psutil_aix',
        sources=(
            sources
            + ["psutil/_psutil_aix.c"]
            + glob.glob("psutil/arch/aix/*.c")
        ),
        libraries=["perfstat"],
        define_macros=macros,
        # fmt: off
        # python 2.7 compatibility requires no comma
        **py_limited_api
        # fmt: on
    )

else:
    sys.exit("platform {} is not supported".format(sys.platform))


def main():
    kwargs = dict(
        name='psutil',
        version=VERSION,
        description="Cross-platform lib for process and system monitoring.",
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
        packages=['psutil'],
        ext_modules=[ext],
        options=options,
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Environment :: Console',
            'Intended Audience :: Developers',
            'Intended Audience :: Information Technology',
            'Intended Audience :: System Administrators',
            'Operating System :: MacOS :: MacOS X',
            'Operating System :: Microsoft :: Windows :: Windows 10',
            'Operating System :: Microsoft :: Windows :: Windows 11',
            'Operating System :: Microsoft :: Windows :: Windows 7',
            'Operating System :: Microsoft :: Windows :: Windows 8',
            'Operating System :: Microsoft :: Windows :: Windows 8.1',
            'Operating System :: Microsoft :: Windows :: Windows Server 2003',
            'Operating System :: Microsoft :: Windows :: Windows Server 2008',
            'Operating System :: Microsoft :: Windows :: Windows Vista',
            'Operating System :: Microsoft :: Windows',
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
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: Implementation :: CPython',
            'Programming Language :: Python :: Implementation :: PyPy',
            'Programming Language :: Python',
            'Topic :: Software Development :: Libraries :: Python Modules',
            'Topic :: Software Development :: Libraries',
            'Topic :: System :: Benchmark',
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
            python_requires=">=3.6",
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
            print_install_instructions()


if __name__ == '__main__':
    main()
