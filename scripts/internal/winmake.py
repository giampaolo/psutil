#!/usr/bin/env python

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Shortcuts for various tasks, emulating UNIX "make" on Windows.
This is supposed to be invoked by "make.bat" and not used directly.
This was originally written as a bat file but they suck so much
that they should be deemed illegal!
"""

import functools
import os
import ssl
import subprocess
import sys
import textwrap


HERE = os.path.abspath(os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '../..'))
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
    "pip",
    "pypiwin32",
    "setuptools",
    "unittest2",
    "wheel",
    "wmi",
]


# ===================================================================
# utils
# ===================================================================


def sh(cmd):
    print("cmd: " + cmd)
    code = os.system(cmd)
    if code:
        sys.exit(code)


_cmds = {}

def cmd(fun):
    @functools.wraps(fun)
    def wrapper(*args, **kwds):
        return fun(*args, **kwds)

    _cmds[fun.__name__] = fun.__doc__
    return wrapper


def install_pip():
    try:
        import pip  # NOQA
        return
    except ImportError:
        pass

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

    with open('get-pip.py', 'wb') as f:
        f.write(data)

    try:
        sh('%s %s --user' % (PYTHON, f.name))
    finally:
        os.remove(f.name)


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
    sh("%s setup.py build_ext -i" % PYTHON)


@cmd
def install():
    """Install in develop / edit mode"""
    build()
    sh("%s setup.py develop" % PYTHON)


@cmd
def uninstall():
    """Uninstall psutil"""
    install_pip()
    sh("%s -m pip uninstall -y psutil" % PYTHON)


@cmd
def clean():
    """Deletes dev files"""
    sh("for /r %%R in (__pycache__) do if exist %%R (rmdir /S /Q %%R)")
    sh("for /r %%R in (*.pyc) do if exist %%R (del /s %%R)")
    sh("for /r %%R in (*.pyd) do if exist %%R (del /s %%R)")
    sh("for /r %%R in (*.orig) do if exist %%R (del /s %%R)")
    sh("for /r %%R in (*.bak) do if exist %%R (del /s %%R)")
    sh("for /r %%R in (*.rej) do if exist %%R (del /s %%R)")
    sh("if exist psutil.egg-info (rmdir /S /Q psutil.egg-info)")
    sh("if exist build (rmdir /S /Q build)")
    sh("if exist dist (rmdir /S /Q dist)")


@cmd
def setup_dev_env():
    """Install useful deps"""
    install_pip()
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
def test_by_name():
    """Run test by name"""
    try:
        print(sys.argv)
        name = sys.argv[2]
    except IndexError:
        sys.exit('second arg missing')
    install()
    sh(textwrap.dedent("""\
        %s -m nose \
        psutil\\tests\\test_process.py \
        psutil\\tests\\test_system.py \
        psutil\\tests\\test_windows.py \
        psutil\\tests\\test_misc.py --nocapture -v -m %s""" % (PYTHON, name)))


@cmd
def test_memleaks():
    """Run memory leaks tests"""
    install()
    sh("%s test\test_memory_leaks.py" % PYTHON)


def main():
    os.chdir(ROOT)
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
