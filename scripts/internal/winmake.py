#!/usr/bin/env python

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Shortcuts for various tasks, emulating UNIX "make" on Windows.
This is supposed to be invoked by "make.bat" and not used directly.
This was originally written as a bat file but they suck so much
that they should be deemed illegal!
"""

import errno
import fnmatch
import functools
import os
import shutil
import ssl
import subprocess
import sys
import tempfile


PYTHON = sys.executable
TSCRIPT = os.environ['TSCRIPT']
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
PY3 = sys.version_info[0] == 3
DEPS = [
    "coverage",
    "flake8",
    "ipaddress",
    "mock",
    "nose",
    "pdbpp",
    "perf",
    "pip",
    "pypiwin32",
    "setuptools",
    "unittest2",
    "wheel",
    "wmi",
]
_cmds = {}


# ===================================================================
# utils
# ===================================================================


def sh(cmd):
    print("cmd: " + cmd)
    code = os.system(cmd)
    if code:
        raise SystemExit


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
            print("rm %s" % path)

    def safe_rmtree(path):
        def onerror(fun, path, excinfo):
            exc = excinfo[1]
            if exc.errno != errno.ENOENT:
                raise

        existed = os.path.isdir(path)
        shutil.rmtree(path, onerror=onerror)
        if existed:
            print("rmdir -f %s" % path)

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
                print("rmdir -f %s" % path)
                safe_rmtree(path)
            else:
                print("rm %s" % path)
                safe_remove(path)


def safe_remove(path):
    try:
        os.remove(path)
    except OSError as err:
        if err.errno != errno.ENOENT:
            raise
    else:
        print("rm %s" % path)


def safe_rmtree(path):
    def onerror(fun, path, excinfo):
        exc = excinfo[1]
        if exc.errno != errno.ENOENT:
            raise

    existed = os.path.isdir(path)
    shutil.rmtree(path, onerror=onerror)
    if existed:
        print("rmdir -f %s" % path)


def recursive_rm(*patterns):
    """Recursively remove a file or matching a list of patterns."""
    for root, subdirs, subfiles in os.walk('.'):
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


# ===================================================================
# commands
# ===================================================================


@cmd
def help():
    """Print this help"""
    print('Run "make <target>" where <target> is one of:')
    for name in sorted(_cmds):
        print("    %-20s %s" % (name.replace('_', '-'), _cmds[name] or ''))


@cmd
def build():
    """Build / compile"""
    sh("%s setup.py build" % PYTHON)
    # copies compiled *.pyd files in ./psutil directory in order to
    # allow "import psutil" when using the interactive interpreter
    # from within this directory.
    sh("%s setup.py build_ext -i" % PYTHON)


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
        print("downloading %s" % GET_PIP_URL)
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
    clean()
    try:
        import psutil
    except ImportError:
        return
    install_pip()
    sh("%s -m pip uninstall -y psutil" % PYTHON)

    # Uninstalling psutil on Windows seems to be tricky as we may have
    # different versions os psutil installed. Also we don't want to be
    # in the main psutil source dir as "import psutil" will always
    # succeed so this really removes files from site-packages dir.
    here = os.getcwd()
    try:
        os.chdir('C:\\')
        while True:
            try:
                import psutil  # NOQA
            except ImportError:
                return
            sh("%s -m pip uninstall -y psutil" % PYTHON)
    finally:
        os.chdir(here)


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
    sh("%s -m flake8 %s" % (PYTHON, py_files))


@cmd
def test():
    """Run tests"""
    install()
    sh("%s %s" % (PYTHON, TSCRIPT))


@cmd
def coverage():
    """Run coverage tests."""
    # Note: coverage options are controlled by .coveragerc file
    install()
    sh("%s -m coverage run %s" % (PYTHON, TSCRIPT))
    sh("%s -m coverage report" % PYTHON)
    sh("%s -m coverage html" % PYTHON)
    sh("%s -m webbrowser -t htmlcov/index.html" % PYTHON)


@cmd
def test_process():
    """Run process tests"""
    install()
    sh("%s -m unittest -v psutil.tests.test_process" % PYTHON)


@cmd
def test_system():
    """Run system tests"""
    install()
    sh("%s -m unittest -v psutil.tests.test_system" % PYTHON)


@cmd
def test_platform():
    """Run windows only tests"""
    install()
    sh("%s -m unittest -v psutil.tests.test_windows" % PYTHON)


@cmd
def test_misc():
    """Run misc tests"""
    install()
    sh("%s -m unittest -v psutil.tests.test_misc" % PYTHON)


@cmd
def test_by_name():
    """Run test by name"""
    try:
        print(sys.argv)
        name = sys.argv[2]
    except IndexError:
        sys.exit('second arg missing')
    install()
    sh("%s -m unittest -v %s" % (PYTHON, name))


@cmd
def test_memleaks():
    """Run memory leaks tests"""
    install()
    sh("%s psutil\\tests\\test_memory_leaks.py" % PYTHON)


@cmd
def install_git_hooks():
    if os.path.isdir('.git'):
        shutil.copy(".git-pre-commit", ".git\\hooks\\pre-commit")


@cmd
def bench_oneshot():
    install()
    sh("%s scripts\\internal\\bench_oneshot.py" % PYTHON)


@cmd
def bench_oneshot_2():
    install()
    sh("%s scripts\\internal\\bench_oneshot_2.py" % PYTHON)


def main():
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
