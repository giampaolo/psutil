#!/usr/bin/env python

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Shortcuts for various tasks, emulating UNIX "make" on Windows.
This is supposed to be invoked by "make.bat" and not used directly.
This was originally written as a bat file but they suck so much
that they should be deemed illegal!
"""

from __future__ import print_function
import errno
import fnmatch
import functools
import os
import shutil
import site
import ssl
import subprocess
import sys
import tempfile


APPVEYOR = bool(os.environ.get('APPVEYOR'))
if APPVEYOR:
    PYTHON = sys.executable
else:
    PYTHON = os.getenv('PYTHON', sys.executable)
TEST_SCRIPT = 'psutil\\tests\\__main__.py'
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
PY3 = sys.version_info[0] == 3
HERE = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.realpath(os.path.join(HERE, "..", ".."))
DEPS = [
    "coverage",
    "flake8",
    "nose",
    "pdbpp",
    "perf",
    "pip",
    "pypiwin32==219" if sys.version_info[:2] <= (3, 4) else "pypiwin32",
    "pyreadline",
    "setuptools",
    "wheel",
    "wmi",
    "requests"
]
if sys.version_info[:2] <= (2, 6):
    DEPS.append('unittest2')
if sys.version_info[:2] <= (2, 7):
    DEPS.append('mock')
if sys.version_info[:2] <= (3, 2):
    DEPS.append('ipaddress')

_cmds = {}
if PY3:
    basestring = str

# ===================================================================
# utils
# ===================================================================


def safe_print(text, file=sys.stdout, flush=False):
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


def sh(cmd, nolog=False):
    if not nolog:
        safe_print("cmd: " + cmd)
    p = subprocess.Popen(cmd, shell=True, env=os.environ, cwd=os.getcwd())
    p.communicate()
    if p.returncode != 0:
        sys.exit(p.returncode)


def cmd(fun):
    @functools.wraps(fun)
    def wrapper(*args, **kwds):
        return fun(*args, **kwds)

    _cmds[fun.__name__] = fun.__doc__
    return wrapper


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
                raise

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

    for root, subdirs, subfiles in os.walk('.'):
        root = os.path.normpath(root)
        if root.startswith('.git/'):
            continue
        found = fnmatch.filter(subdirs if directory else subfiles, pattern)
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
            raise

    existed = os.path.isdir(path)
    shutil.rmtree(path, onerror=onerror)
    if existed:
        safe_print("rmdir -f %s" % path)


def recursive_rm(*patterns):
    """Recursively remove a file or matching a list of patterns."""
    for root, subdirs, subfiles in os.walk(u'.'):
        root = os.path.normpath(root)
        if root.startswith('.git/'):
            continue
        for file in subfiles:
            for pattern in patterns:
                if fnmatch.fnmatch(file, pattern):
                    safe_remove(os.path.join(root, file))
        for dir in subdirs:
            for pattern in patterns:
                if fnmatch.fnmatch(dir, pattern):
                    safe_rmtree(os.path.join(root, dir))


def test_setup():
    os.environ['PYTHONWARNINGS'] = 'all'
    os.environ['PSUTIL_TESTING'] = '1'
    os.environ['PSUTIL_DEBUG'] = '1'


# ===================================================================
# commands
# ===================================================================


@cmd
def help():
    """Print this help"""
    safe_print('Run "make [-p <PYTHON>] <target>" where <target> is one of:')
    for name in sorted(_cmds):
        safe_print(
            "    %-20s %s" % (name.replace('_', '-'), _cmds[name] or ''))
    sys.exit(1)


@cmd
def build():
    """Build / compile"""
    # Make sure setuptools is installed (needed for 'develop' /
    # edit mode).
    sh('%s -c "import setuptools"' % PYTHON)
    sh("%s setup.py build" % PYTHON)
    # Copies compiled *.pyd files in ./psutil directory in order to
    # allow "import psutil" when using the interactive interpreter
    # from within this directory.
    sh("%s setup.py build_ext -i" % PYTHON)
    # Make sure it actually worked.
    sh('%s -c "import psutil"' % PYTHON)


@cmd
def wheel():
    """Create wheel file."""
    build()
    sh("%s setup.py bdist_wheel" % PYTHON)


@cmd
def upload_wheels():
    """Upload wheel files on PyPI."""
    build()
    sh("%s -m twine upload dist/*.whl" % PYTHON)


@cmd
def install_pip():
    """Install pip"""
    try:
        import pip  # NOQA
    except ImportError:
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


@cmd
def install():
    """Install in develop / edit mode"""
    install_git_hooks()
    build()
    sh("%s setup.py develop" % PYTHON)


@cmd
def uninstall():
    """Uninstall psutil"""
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


@cmd
def clean():
    """Deletes dev files"""
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
        ".tox",
    )
    safe_rmtree("build")
    safe_rmtree(".coverage")
    safe_rmtree("dist")
    safe_rmtree("docs/_build")
    safe_rmtree("htmlcov")
    safe_rmtree("tmp")


@cmd
def setup_dev_env():
    """Install useful deps"""
    install_pip()
    install_git_hooks()
    sh("%s -m pip install -U %s" % (PYTHON, " ".join(DEPS)))


@cmd
def flake8():
    """Run flake8 against all py files"""
    py_files = subprocess.check_output("git ls-files")
    if PY3:
        py_files = py_files.decode()
    py_files = [x for x in py_files.split() if x.endswith('.py')]
    py_files = ' '.join(py_files)
    sh("%s -m flake8 %s" % (PYTHON, py_files), nolog=True)


@cmd
def test():
    """Run tests"""
    try:
        arg = sys.argv[2]
    except IndexError:
        arg = TEST_SCRIPT

    install()
    test_setup()
    cmdline = "%s %s" % (PYTHON, arg)
    safe_print(cmdline)
    sh(cmdline)


@cmd
def coverage():
    """Run coverage tests."""
    # Note: coverage options are controlled by .coveragerc file
    install()
    test_setup()
    sh("%s -m coverage run %s" % (PYTHON, TEST_SCRIPT))
    sh("%s -m coverage report" % PYTHON)
    sh("%s -m coverage html" % PYTHON)
    sh("%s -m webbrowser -t htmlcov/index.html" % PYTHON)


@cmd
def test_process():
    """Run process tests"""
    install()
    test_setup()
    sh("%s psutil\\tests\\test_process.py" % PYTHON)


@cmd
def test_system():
    """Run system tests"""
    install()
    test_setup()
    sh("%s psutil\\tests\\test_system.py" % PYTHON)


@cmd
def test_platform():
    """Run windows only tests"""
    install()
    test_setup()
    sh("%s psutil\\tests\\test_windows.py" % PYTHON)


@cmd
def test_misc():
    """Run misc tests"""
    install()
    test_setup()
    sh("%s psutil\\tests\\test_misc.py" % PYTHON)


@cmd
def test_unicode():
    """Run unicode tests"""
    install()
    test_setup()
    sh("%s psutil\\tests\\test_unicode.py" % PYTHON)


@cmd
def test_connections():
    """Run connections tests"""
    install()
    test_setup()
    sh("%s psutil\\tests\\test_connections.py" % PYTHON)


@cmd
def test_contracts():
    """Run contracts tests"""
    install()
    test_setup()
    sh("%s psutil\\tests\\test_contracts.py" % PYTHON)


@cmd
def test_by_name():
    """Run test by name"""
    name = sys.argv[2]
    install()
    test_setup()
    sh("%s -m unittest -v %s" % (PYTHON, name))


@cmd
def test_failed():
    """Re-run tests which failed on last run."""
    install()
    test_setup()
    sh('%s -c "import psutil.tests.runner as r; r.run(last_failed=True)"' % (
        PYTHON))


@cmd
def test_script():
    """Quick way to test a script"""
    try:
        safe_print(sys.argv)
        name = sys.argv[2]
    except IndexError:
        sys.exit('second arg missing')
    install()
    test_setup()
    sh("%s %s" % (PYTHON, name))


@cmd
def test_memleaks():
    """Run memory leaks tests"""
    install()
    test_setup()
    sh("%s psutil\\tests\\test_memory_leaks.py" % PYTHON)


@cmd
def install_git_hooks():
    """Install GIT pre-commit hook."""
    if os.path.isdir('.git'):
        src = os.path.join(ROOT_DIR, "scripts", "internal", ".git-pre-commit")
        dst = os.path.realpath(
            os.path.join(ROOT_DIR, ".git", "hooks", "pre-commit"))
        with open(src, "rt") as s:
            with open(dst, "wt") as d:
                d.write(s.read())


@cmd
def bench_oneshot():
    """Benchmarks for oneshot() ctx manager (see #799)."""
    sh("%s -Wa scripts\\internal\\bench_oneshot.py" % PYTHON)


@cmd
def bench_oneshot_2():
    """Same as above but using perf module (supposed to be more precise)."""
    sh("%s -Wa scripts\\internal\\bench_oneshot_2.py" % PYTHON)


@cmd
def print_access_denied():
    """Print AD exceptions raised by all Process methods."""
    sh("%s -Wa scripts\\internal\\print_access_denied.py" % PYTHON)


@cmd
def print_api_speed():
    """Benchmark all API calls."""
    sh("%s -Wa scripts\\internal\\print_api_speed.py" % PYTHON)


def set_python(s):
    global PYTHON
    if os.path.isabs(s):
        PYTHON = s
    else:
        # try to look for a python installation
        orig = s
        s = s.replace('.', '')
        vers = ('26', '27', '34', '35', '36', '37',
                '26-64', '27-64', '34-64', '35-64', '36-64', '37-64')
        for v in vers:
            if s == v:
                path = r'C:\\python%s\python.exe' % s
                if os.path.isfile(path):
                    print(path)
                    PYTHON = path
                    os.putenv('PYTHON', path)
                    return
        return sys.exit(
            "can't find any python installation matching %r" % orig)


def parse_cmdline():
    if '-p' in sys.argv:
        try:
            pos = sys.argv.index('-p')
            sys.argv.pop(pos)
            py = sys.argv.pop(pos)
        except IndexError:
            return help()
        set_python(py)


def main():
    parse_cmdline()
    try:
        cmd = sys.argv[1].replace('-', '_')
    except IndexError:
        return help()
    if cmd in _cmds:
        fun = getattr(sys.modules[__name__], cmd)
        fun()
    else:
        help()


if __name__ == '__main__':
    main()
