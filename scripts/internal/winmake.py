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
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
PY3 = sys.version_info[0] == 3
DEPS = [
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


def sh(cmd, decode=False):
    print("cmd: " + cmd)
    try:
        out = subprocess.check_output(cmd, shell=True)
    except subprocess.CalledProcessError as err:
        sys.exit(err)
    else:
        if decode and PY3:
            out = out.decode()
        return out


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
    py_files = sh("git ls-files", decode=True)
    py_files = [x for x in py_files.split() if x.endswith('.py')]
    py_files = ' '.join(py_files)
    sh("%s -m flake8 %s" % (PYTHON, py_files))


@cmd
def test():
    """Run tests"""
    TSCRIPT = os.environ['TSCRIPT']
    install()
    sh("%s %s" % (PYTHON, TSCRIPT))


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
