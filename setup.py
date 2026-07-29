#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Cross-platform lib for process and system monitoring in Python."""

import concurrent.futures
import glob
import os
import pathlib
import shlex
import struct
import subprocess
import sys
import sysconfig
import tempfile

from setuptools import Extension
from setuptools import setup
from setuptools.command.build_ext import build_ext

ROOT_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from _bootstrap import get_version  # noqa: E402
from _bootstrap import load_module  # noqa: E402

_common = load_module(ROOT_DIR / "psutil" / "_common.py")

AIX = _common.AIX
BSD = _common.BSD
FREEBSD = _common.FREEBSD
LINUX = _common.LINUX
MACOS = _common.MACOS
NETBSD = _common.NETBSD
OPENBSD = _common.OPENBSD
POSIX = _common.POSIX
SUNOS = _common.SUNOS
WINDOWS = _common.WINDOWS

hilite = _common.hilite

PYPY = '__pypy__' in sys.builtin_module_names
CPYTHON = sys.implementation.name == "cpython"
Py_GIL_DISABLED = sysconfig.get_config_var("Py_GIL_DISABLED")
NUM_CPUS = os.cpu_count() or 1


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


VERSION = get_version()
macros.append(('PSUTIL_VERSION', int(VERSION.replace('.', ''))))

# The oldest interpreter we support, and the one the wheel claims to
# run on. Py_LIMITED_API lets us create a single wheel which works with
# multiple python versions, including unreleased ones.
MIN_PY_VERSION = (3, 8)

abi3_platform = MACOS or LINUX or WINDOWS  # the ones we ship wheels for
if CPYTHON and abi3_platform and not Py_GIL_DISABLED:
    _abi3_tag = "cp{}{}".format(*MIN_PY_VERSION)
    _hexversion = "0x{:02x}{:02x}0000".format(*MIN_PY_VERSION)
    py_limited_api = {"py_limited_api": True}
    options = {"bdist_wheel": {"py_limited_api": _abi3_tag}}
    macros.append(('Py_LIMITED_API', _hexversion))
else:
    py_limited_api = {}
    options = {}


def get_long_description():
    script = ROOT_DIR / "scripts" / "internal" / "convert_readme.py"
    readme = ROOT_DIR / 'README.rst'
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


def has_python_h():
    """Whether a C file including Python.h really compiles."""
    paths = sysconfig.get_paths()
    incdirs = [paths["include"]]
    if paths.get("platinclude") and paths["platinclude"] not in incdirs:
        incdirs.append(paths["platinclude"])
    args = []
    for d in incdirs:
        args.extend(["-I", d])
    return unix_can_compile("#include <Python.h>", args)


def get_cc():
    """The compiler (plus flags) python uses to build C extensions."""
    cc = os.getenv('CC') or sysconfig.get_config_var("CC") or "cc"
    return shlex.split(cc)


def has_compiler():
    return unix_can_compile("int main(void) { return 0; }")


def unix_can_compile(c_code, extra_args=()):
    # https://github.com/giampaolo/psutil/pull/1568
    with tempfile.TemporaryDirectory() as tempdir:
        src = os.path.join(tempdir, "test.c")
        with open(src, "w") as f:
            f.write(c_code)
        cmd = (
            get_cc()
            + list(extra_args)
            + [
                "-c",
                src,
                "-o",
                os.path.join(tempdir, "test.o"),
            ]
        )
        try:
            ret = subprocess.call(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except OSError:
            return False  # compiler is not installed
        return ret == 0


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
        'psutil._psutil',
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
        **py_limited_api,
    )

elif MACOS:
    macros.extend([("PSUTIL_OSX", 1), ("PSUTIL_MACOS", 1)])
    ext = Extension(
        'psutil._psutil',
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
        **py_limited_api,
    )

elif FREEBSD:
    macros.append(("PSUTIL_FREEBSD", 1))

    ext = Extension(
        'psutil._psutil',
        sources=(
            sources
            + ["psutil/_psutil_bsd.c"]
            + glob.glob("psutil/arch/bsd/*.c")
            + glob.glob("psutil/arch/freebsd/*.c")
        ),
        define_macros=macros,
        libraries=["devstat"],
        **py_limited_api,
    )

elif OPENBSD:
    macros.append(("PSUTIL_OPENBSD", 1))

    ext = Extension(
        'psutil._psutil',
        sources=(
            sources
            + ["psutil/_psutil_bsd.c"]
            + glob.glob("psutil/arch/bsd/*.c")
            + glob.glob("psutil/arch/openbsd/*.c")
        ),
        define_macros=macros,
        libraries=["kvm"],
        **py_limited_api,
    )

elif NETBSD:
    macros.append(("PSUTIL_NETBSD", 1))

    ext = Extension(
        'psutil._psutil',
        sources=(
            sources
            + ["psutil/_psutil_bsd.c"]
            + glob.glob("psutil/arch/bsd/*.c")
            + glob.glob("psutil/arch/netbsd/*.c")
        ),
        define_macros=macros,
        libraries=["kvm", "jemalloc"],
        **py_limited_api,
    )

elif LINUX:
    # see: https://github.com/giampaolo/psutil/issues/659
    if not unix_can_compile("#include <linux/ethtool.h>"):
        macros.append(("PSUTIL_ETHTOOL_MISSING_TYPES", 1))

    macros.append(("PSUTIL_LINUX", 1))
    ext = Extension(
        'psutil._psutil',
        sources=(
            sources
            + ["psutil/_psutil_linux.c"]
            + glob.glob("psutil/arch/linux/*.c")
        ),
        define_macros=macros,
        **py_limited_api,
    )

elif SUNOS:
    macros.append(("PSUTIL_SUNOS", 1))

    ext = Extension(
        'psutil._psutil',
        sources=(
            sources
            + ["psutil/_psutil_sunos.c"]
            + glob.glob("psutil/arch/sunos/*.c")
        ),
        define_macros=macros,
        libraries=["kstat", "nsl", "socket"],
        **py_limited_api,
    )

elif AIX:
    macros.append(("PSUTIL_AIX", 1))

    ext = Extension(
        'psutil._psutil',
        sources=(
            sources
            + ["psutil/_psutil_aix.c"]
            + glob.glob("psutil/arch/aix/*.c")
        ),
        libraries=["perfstat"],
        define_macros=macros,
        **py_limited_api,
    )

else:
    sys.exit("platform {} is not supported".format(sys.platform))


class BuildExt(build_ext):
    """Compile the C sources in parallel."""

    def build_extensions(self):  # override
        compiler = self.compiler
        real_spawn = compiler.spawn
        real_compile = compiler.compile

        def parallel_compile(*args, **kwargs):
            # Run compile() as usual, but have every compiler
            # invocation return right away, then wait for all of them.
            # Hooking spawn() instead of the private per-file methods
            # is what makes this work on Windows as well.
            futures = []
            with concurrent.futures.ThreadPoolExecutor(NUM_CPUS) as pool:
                compiler.spawn = lambda cmd, **kw: futures.append(
                    pool.submit(real_spawn, cmd, **kw)
                )
                try:
                    objects = real_compile(*args, **kwargs)
                finally:
                    compiler.spawn = real_spawn
                for fut in concurrent.futures.as_completed(futures):
                    fut.result()  # let compiler errors surface
            return objects

        compiler.compile = parallel_compile
        super().build_extensions()


def print_install_instructions():
    if WINDOWS:
        return
    suggest = ""
    if not has_compiler():
        suggest = "A C compiler is not installed."
    elif not has_python_h():
        suggest = "Python header files are not installed."
    if suggest:
        if MACOS:
            cmd = "xcode-select --install"
        else:
            script = "https://raw.githubusercontent.com/giampaolo/psutil/master/scripts/internal/install-sysdeps.sh"
            cmd = f"curl -fsSL {script} | sh"
        suggest += f" Try running:\n{cmd}"
        print(hilite(suggest, color="red", bold=True), file=sys.stderr)


def main():
    kwargs = dict(
        name='psutil',
        version=VERSION,
        description="Cross-platform lib for process and system monitoring.",
        long_description=get_long_description(),
        long_description_content_type='text/x-rst',
        # fmt: off
        keywords=[
            'ps', 'top', 'kill', 'free', 'lsof', 'netstat', 'df', 'uptime',
            'taskmgr', 'process', 'monitoring', 'performance', 'metrics',
            'observability',
        ],
        # fmt: on
        author='Giampaolo Rodola',
        author_email='g.rodola@gmail.com',
        url='https://github.com/giampaolo/psutil',
        platforms='Platform Independent',
        license='BSD-3-Clause',
        packages=['psutil'],
        ext_modules=[ext],
        cmdclass={'build_ext': BuildExt if NUM_CPUS > 1 else build_ext},
        options=options,
        python_requires=">={}.{}".format(*MIN_PY_VERSION),
        # https://docs.pypi.org/project_metadata/
        project_urls={
            'Homepage': 'https://github.com/giampaolo/psutil',
            'Source': 'https://github.com/giampaolo/psutil',
            'Issues': 'https://github.com/giampaolo/psutil/issues',
            'Documentation': 'https://psutil.io/',
            'Changelog': 'https://psutil.io/changelog/',
            'Funding': 'https://github.com/sponsors/giampaolo',
        },
        # https://pypi.org/classifiers/
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Environment :: Console',
            'Intended Audience :: Developers',
            'Intended Audience :: Information Technology',
            'Intended Audience :: System Administrators',
            'License :: OSI Approved :: BSD License',
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
            'Programming Language :: Python :: 3 :: Only',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: Implementation :: CPython',
            'Programming Language :: Python :: Implementation :: PyPy',
            'Programming Language :: Python',
            'Programming Language :: Python :: Free Threading',
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
    success = False
    try:
        setup(**kwargs)
        success = True
    finally:
        cmd = sys.argv[1] if len(sys.argv) >= 2 else ''
        if (
            not success
            and POSIX
            and cmd.startswith(("build", "install", "bdist", "develop"))
        ):
            print_install_instructions()


if __name__ == '__main__':
    main()
