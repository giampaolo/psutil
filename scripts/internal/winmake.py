#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Shortcuts for various tasks, emulating UNIX "make" on Windows.
This is supposed to be invoked by "make.bat" and not used directly.
This was originally written as a bat file but they suck so much
that they should be deemed illegal!
"""

from __future__ import print_function

import argparse
import atexit
import ctypes
import errno
import fnmatch
import os
import shutil
import site
import ssl
import subprocess
import sys
import tempfile


APPVEYOR = bool(os.environ.get('APPVEYOR'))
PYTHON = sys.executable if APPVEYOR else os.getenv('PYTHON', sys.executable)
PY3 = sys.version_info[0] >= 3
PYTEST_ARGS = "-v -s --tb=short"
if PY3:
    PYTEST_ARGS += "-o "
HERE = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.realpath(os.path.join(HERE, "..", ".."))
PYPY = '__pypy__' in sys.builtin_module_names
if PY3:
    GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
else:
    GET_PIP_URL = "https://bootstrap.pypa.io/pip/2.7/get-pip.py"


# mandatory deps
if PY3:
    DEPS = [
        "setuptools",
        "pytest",
        "pytest-xdist",
        "wheel",
    ]
else:
    DEPS = [
        "enum34",
        "futures",
        "ipaddress",
        "mock==1.0.1",
        "pytest-xdist",
        "pytest==4.6.11",
        "setuptools",
        "wheel",
    ]

# deps for local development
if not APPVEYOR:
    DEPS += [
        "coverage",
        "pdbpp",
        "pyperf",
        "pyreadline",
        "requests",
        "wheel",
    ]

if not PYPY:
    DEPS.append("pywin32")
    DEPS.append("wmi")

_cmds = {}
if PY3:
    basestring = str

GREEN = 2
LIGHTBLUE = 3
YELLOW = 6
RED = 4
DEFAULT_COLOR = 7


# ===================================================================
# utils
# ===================================================================


def safe_print(text, file=sys.stdout):
    """Prints a (unicode) string to the console, encoded depending on
    the stdout/file encoding (eg. cp437 on Windows). This is to avoid
    encoding errors in case of funky path names.
    Works with Python 2 and 3.
    """
    if not isinstance(text, basestring):
        return print(text, file=file)
    try:
        file.write(text)
    except UnicodeEncodeError:
        bytes_string = text.encode(file.encoding, 'backslashreplace')
        if hasattr(file, 'buffer'):
            file.buffer.write(bytes_string)
        else:
            text = bytes_string.decode(file.encoding, 'strict')
            file.write(text)
    file.write("\n")


def stderr_handle():
    GetStdHandle = ctypes.windll.Kernel32.GetStdHandle
    STD_ERROR_HANDLE_ID = ctypes.c_ulong(0xFFFFFFF4)
    GetStdHandle.restype = ctypes.c_ulong
    handle = GetStdHandle(STD_ERROR_HANDLE_ID)
    atexit.register(ctypes.windll.Kernel32.CloseHandle, handle)
    return handle


def win_colorprint(s, color=LIGHTBLUE):
    color += 8  # bold
    handle = stderr_handle()
    SetConsoleTextAttribute = ctypes.windll.Kernel32.SetConsoleTextAttribute
    SetConsoleTextAttribute(handle, color)
    try:
        print(s)
    finally:
        SetConsoleTextAttribute(handle, DEFAULT_COLOR)


def sh(cmd, nolog=False):
    if not nolog:
        safe_print("cmd: " + cmd)
    p = subprocess.Popen(  # noqa S602
        cmd, shell=True, env=os.environ, cwd=os.getcwd()
    )
    p.communicate()
    if p.returncode != 0:
        sys.exit(p.returncode)


def rm(pattern, directory=False):
    """Recursively remove a file or dir by pattern."""

    def safe_remove(path):
        try:
            os.remove(path)
        except OSError as err:
            if err.errno != errno.ENOENT:
                raise
        else:
            safe_print("rm %s" % path)

    def safe_rmtree(path):
        def onerror(fun, path, excinfo):
            exc = excinfo[1]
            if exc.errno != errno.ENOENT:
                raise  # noqa: PLE0704

        existed = os.path.isdir(path)
        shutil.rmtree(path, onerror=onerror)
        if existed:
            safe_print("rmdir -f %s" % path)

    if "*" not in pattern:
        if directory:
            safe_rmtree(pattern)
        else:
            safe_remove(pattern)
        return

    for root, dirs, files in os.walk('.'):
        root = os.path.normpath(root)
        if root.startswith('.git/'):
            continue
        found = fnmatch.filter(dirs if directory else files, pattern)
        for name in found:
            path = os.path.join(root, name)
            if directory:
                safe_print("rmdir -f %s" % path)
                safe_rmtree(path)
            else:
                safe_print("rm %s" % path)
                safe_remove(path)


def safe_remove(path):
    try:
        os.remove(path)
    except OSError as err:
        if err.errno != errno.ENOENT:
            raise
    else:
        safe_print("rm %s" % path)


def safe_rmtree(path):
    def onerror(fun, path, excinfo):
        exc = excinfo[1]
        if exc.errno != errno.ENOENT:
            raise  # noqa: PLE0704

    existed = os.path.isdir(path)
    shutil.rmtree(path, onerror=onerror)
    if existed:
        safe_print("rmdir -f %s" % path)


def recursive_rm(*patterns):
    """Recursively remove a file or matching a list of patterns."""
    for root, dirs, files in os.walk('.'):
        root = os.path.normpath(root)
        if root.startswith('.git/'):
            continue
        for file in files:
            for pattern in patterns:
                if fnmatch.fnmatch(file, pattern):
                    safe_remove(os.path.join(root, file))
        for dir in dirs:
            for pattern in patterns:
                if fnmatch.fnmatch(dir, pattern):
                    safe_rmtree(os.path.join(root, dir))


# ===================================================================
# commands
# ===================================================================


def build():
    """Build / compile."""
    # Make sure setuptools is installed (needed for 'develop' /
    # edit mode).
    sh('%s -c "import setuptools"' % PYTHON)

    # "build_ext -i" copies compiled *.pyd files in ./psutil directory in
    # order to allow "import psutil" when using the interactive interpreter
    # from within psutil root directory.
    cmd = [PYTHON, "setup.py", "build_ext", "-i"]
    if sys.version_info[:2] >= (3, 6) and (os.cpu_count() or 1) > 1:
        cmd += ['--parallel', str(os.cpu_count())]
    # Print coloured warnings in real time.
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        for line in iter(p.stdout.readline, b''):
            if PY3:
                line = line.decode()
            line = line.strip()
            if 'warning' in line:
                win_colorprint(line, YELLOW)
            elif 'error' in line:
                win_colorprint(line, RED)
            else:
                print(line)
        # retcode = p.poll()
        p.communicate()
        if p.returncode:
            win_colorprint("failure", RED)
            sys.exit(p.returncode)
    finally:
        p.terminate()
        p.wait()

    # Make sure it actually worked.
    sh('%s -c "import psutil"' % PYTHON)
    win_colorprint("build + import successful", GREEN)


def wheel():
    """Create wheel file."""
    build()
    sh("%s setup.py bdist_wheel" % PYTHON)


def upload_wheels():
    """Upload wheel files on PyPI."""
    build()
    sh("%s -m twine upload dist/*.whl" % PYTHON)


def install_pip():
    """Install pip."""
    try:
        sh('%s -c "import pip"' % PYTHON)
    except SystemExit:
        if PY3:
            from urllib.request import urlopen
        else:
            from urllib2 import urlopen

        if hasattr(ssl, '_create_unverified_context'):
            ctx = ssl._create_unverified_context()
        else:
            ctx = None
        kw = dict(context=ctx) if ctx else {}
        safe_print("downloading %s" % GET_PIP_URL)
        req = urlopen(GET_PIP_URL, **kw)
        data = req.read()

        tfile = os.path.join(tempfile.gettempdir(), 'get-pip.py')
        with open(tfile, 'wb') as f:
            f.write(data)

        try:
            sh('%s %s --user' % (PYTHON, tfile))
        finally:
            os.remove(tfile)


def install():
    """Install in develop / edit mode."""
    build()
    sh("%s setup.py develop" % PYTHON)


def uninstall():
    """Uninstall psutil."""
    # Uninstalling psutil on Windows seems to be tricky.
    # On "import psutil" tests may import a psutil version living in
    # C:\PythonXY\Lib\site-packages which is not what we want, so
    # we try both "pip uninstall psutil" and manually remove stuff
    # from site-packages.
    clean()
    install_pip()
    here = os.getcwd()
    try:
        os.chdir('C:\\')
        while True:
            try:
                import psutil  # NOQA
            except ImportError:
                break
            else:
                sh("%s -m pip uninstall -y psutil" % PYTHON)
    finally:
        os.chdir(here)

    for dir in site.getsitepackages():
        for name in os.listdir(dir):
            if name.startswith('psutil'):
                rm(os.path.join(dir, name))
            elif name == 'easy-install.pth':
                # easy_install can add a line (installation path) into
                # easy-install.pth; that line alters sys.path.
                path = os.path.join(dir, name)
                with open(path) as f:
                    lines = f.readlines()
                    hasit = False
                    for line in lines:
                        if 'psutil' in line:
                            hasit = True
                            break
                if hasit:
                    with open(path, "w") as f:
                        for line in lines:
                            if 'psutil' not in line:
                                f.write(line)
                            else:
                                print("removed line %r from %r" % (line, path))


def clean():
    """Deletes dev files."""
    recursive_rm(
        "$testfn*",
        "*.bak",
        "*.core",
        "*.egg-info",
        "*.orig",
        "*.pyc",
        "*.pyd",
        "*.pyo",
        "*.rej",
        "*.so",
        "*.~",
        "*__pycache__",
        ".coverage",
        ".failed-tests.txt",
    )
    safe_rmtree("build")
    safe_rmtree(".coverage")
    safe_rmtree("dist")
    safe_rmtree("docs/_build")
    safe_rmtree("htmlcov")
    safe_rmtree("tmp")


def setup_dev_env():
    """Install useful deps."""
    install_pip()
    install_git_hooks()
    sh("%s -m pip install -U %s" % (PYTHON, " ".join(DEPS)))


def test(args=""):
    """Run tests."""
    build()
    sh("%s -m pytest %s %s" % (PYTHON, PYTEST_ARGS, args))


def coverage():
    """Run coverage tests."""
    # Note: coverage options are controlled by .coveragerc file
    build()
    sh("%s -m coverage run -m pytest %s" % (PYTHON, PYTEST_ARGS))
    sh("%s -m coverage report" % PYTHON)
    sh("%s -m coverage html" % PYTHON)
    sh("%s -m webbrowser -t htmlcov/index.html" % PYTHON)


def test_process():
    """Run process tests."""
    build()
    sh("%s psutil\\tests\\test_process.py" % PYTHON)


def test_process_all():
    """Run process all tests."""
    build()
    sh("%s psutil\\tests\\test_process_all.py" % PYTHON)


def test_system():
    """Run system tests."""
    build()
    sh("%s psutil\\tests\\test_system.py" % PYTHON)


def test_platform():
    """Run windows only tests."""
    build()
    sh("%s psutil\\tests\\test_windows.py" % PYTHON)


def test_misc():
    """Run misc tests."""
    build()
    sh("%s psutil\\tests\\test_misc.py" % PYTHON)


def test_unicode():
    """Run unicode tests."""
    build()
    sh("%s psutil\\tests\\test_unicode.py" % PYTHON)


def test_connections():
    """Run connections tests."""
    build()
    sh("%s psutil\\tests\\test_connections.py" % PYTHON)


def test_contracts():
    """Run contracts tests."""
    build()
    sh("%s psutil\\tests\\test_contracts.py" % PYTHON)


def test_testutils():
    """Run test utilities tests."""
    build()
    sh("%s psutil\\tests\\test_testutils.py" % PYTHON)


def test_by_name(name):
    """Run test by name."""
    build()
    test(name)


def test_last_failed():
    """Re-run tests which failed on last run."""
    build()
    test("--last-failed")


def test_memleaks():
    """Run memory leaks tests."""
    build()
    sh("%s psutil\\tests\\test_memleaks.py" % PYTHON)


def install_git_hooks():
    """Install GIT pre-commit hook."""
    if os.path.isdir('.git'):
        src = os.path.join(
            ROOT_DIR, "scripts", "internal", "git_pre_commit.py"
        )
        dst = os.path.realpath(
            os.path.join(ROOT_DIR, ".git", "hooks", "pre-commit")
        )
        with open(src) as s:
            with open(dst, "w") as d:
                d.write(s.read())


def bench_oneshot():
    """Benchmarks for oneshot() ctx manager (see #799)."""
    sh("%s -Wa scripts\\internal\\bench_oneshot.py" % PYTHON)


def bench_oneshot_2():
    """Same as above but using perf module (supposed to be more precise)."""
    sh("%s -Wa scripts\\internal\\bench_oneshot_2.py" % PYTHON)


def print_access_denied():
    """Print AD exceptions raised by all Process methods."""
    build()
    sh("%s -Wa scripts\\internal\\print_access_denied.py" % PYTHON)


def print_api_speed():
    """Benchmark all API calls."""
    build()
    sh("%s -Wa scripts\\internal\\print_api_speed.py" % PYTHON)


def print_sysinfo():
    """Print system info."""
    build()
    from psutil.tests import print_sysinfo

    print_sysinfo()


def download_appveyor_wheels():
    """Download appveyor wheels."""
    sh(
        "%s -Wa scripts\\internal\\download_wheels_appveyor.py "
        "--user giampaolo --project psutil" % PYTHON
    )


def generate_manifest():
    """Generate MANIFEST.in file."""
    script = "scripts\\internal\\generate_manifest.py"
    out = subprocess.check_output([PYTHON, script], text=True)
    with open("MANIFEST.in", "w", newline="\n") as f:
        f.write(out)


def get_python(path):
    if not path:
        return sys.executable
    if os.path.isabs(path):
        return path
    # try to look for a python installation given a shortcut name
    path = path.replace('.', '')
    vers = (
        '27',
        '27-32',
        '27-64',
        '310-32',
        '310-64',
        '311-32',
        '311-64',
        '312-32',
        '312-64',
    )
    for v in vers:
        pypath = r'C:\\python%s\python.exe' % v
        if path in pypath and os.path.isfile(pypath):
            return pypath


def parse_args():
    parser = argparse.ArgumentParser()
    # option shared by all commands
    parser.add_argument('-p', '--python', help="use python executable path")
    sp = parser.add_subparsers(dest='command', title='targets')
    sp.add_parser('bench-oneshot', help="benchmarks for oneshot()")
    sp.add_parser('bench-oneshot_2', help="benchmarks for oneshot() (perf)")
    sp.add_parser('build', help="build")
    sp.add_parser('clean', help="deletes dev files")
    sp.add_parser('coverage', help="run coverage tests.")
    sp.add_parser('download-appveyor-wheels', help="download wheels.")
    sp.add_parser('generate-manifest', help="generate MANIFEST.in file")
    sp.add_parser('help', help="print this help")
    sp.add_parser('install', help="build + install in develop/edit mode")
    sp.add_parser('install-git-hooks', help="install GIT pre-commit hook")
    sp.add_parser('install-pip', help="install pip")
    sp.add_parser('print-access-denied', help="print AD exceptions")
    sp.add_parser('print-api-speed', help="benchmark all API calls")
    sp.add_parser('print-sysinfo', help="print system info")
    sp.add_parser('setup-dev-env', help="install deps")
    test = sp.add_parser('test', help="[ARG] run tests")
    test_by_name = sp.add_parser('test-by-name', help="<ARG> run test by name")
    sp.add_parser('test-connections', help="run connections tests")
    sp.add_parser('test-contracts', help="run contracts tests")
    sp.add_parser(
        'test-last-failed', help="re-run tests which failed on last run"
    )
    sp.add_parser('test-memleaks', help="run memory leaks tests")
    sp.add_parser('test-misc', help="run misc tests")
    sp.add_parser('test-platform', help="run windows only tests")
    sp.add_parser('test-process', help="run process tests")
    sp.add_parser('test-process-all', help="run process all tests")
    sp.add_parser('test-system', help="run system tests")
    sp.add_parser('test-unicode', help="run unicode tests")
    sp.add_parser('test-testutils', help="run test utils tests")
    sp.add_parser('uninstall', help="uninstall psutil")
    sp.add_parser('upload-wheels', help="upload wheel files on PyPI")
    sp.add_parser('wheel', help="create wheel file")

    for p in (test, test_by_name):
        p.add_argument('arg', type=str, nargs='?', default="", help="arg")

    args = parser.parse_args()

    if not args.command or args.command == 'help':
        parser.print_help(sys.stderr)
        sys.exit(1)

    return args


def main():
    global PYTHON
    args = parse_args()
    # set python exe
    PYTHON = get_python(args.python)
    if not PYTHON:
        return sys.exit(
            "can't find any python installation matching %r" % args.python
        )
    os.putenv('PYTHON', PYTHON)
    win_colorprint("using " + PYTHON)

    fname = args.command.replace('-', '_')
    fun = getattr(sys.modules[__name__], fname)  # err if fun not defined
    funargs = []
    # mandatory args
    if args.command in ('test-by-name', 'test-script'):
        if not args.arg:
            sys.exit('command needs an argument')
        funargs = [args.arg]
    # optional args
    if args.command == 'test' and args.arg:
        funargs = [args.arg]
    fun(*funargs)


if __name__ == '__main__':
    main()
