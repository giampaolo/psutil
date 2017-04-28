#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Notes about unicode handling in psutil
======================================

In psutil these are the APIs returning or dealing with a string:

- Process.cmdline()
- Process.connections('unix')  (not tested)
- Process.cwd()
- Process.environ()
- Process.exe()
- Process.memory_maps()        (not tested)
- Process.name()
- Process.open_files()
- Process.username()           (not tested)

- disk_io_counters()           (not tested)
- disk_partitions()            (not tested)
- disk_usage(str)
- net_if_addrs()               (not tested)
- net_if_stats()               (not tested)
- net_io_counters()            (not tested)
- sensors_fans()
- sensors_temperatures()
- users()                      (not tested)
- WindowsService               (not tested)

In here we create a unicode path with a funky non-ASCII name and (where
possible) make psutil return it back (e.g. on name(), exe(),
open_files(), etc.) and make sure psutil never crashes with
UnicodeDecodeError.

On Python 3 the returned path is supposed to match 100% (and this
is tested).
Not on Python 2 though, where we assume correct unicode path handling
is broken. In fact it is broken for most os.* functions, see:
http://bugs.python.org/issue18695
There really is no way for psutil to handle unicode correctly on
Python 2 unless we make such APIs return a unicode type in certain
circumstances.
I'd rather have unicode support broken on Python 2 than having APIs
returning variable str/unicode types, see:
https://github.com/giampaolo/psutil/issues/655#issuecomment-136131180
"""

import os

from psutil import BSD
from psutil import WINDOWS
from psutil._compat import PY3
from psutil.tests import ASCII_FS
from psutil.tests import chdir
from psutil.tests import create_exe
from psutil.tests import get_test_subprocess
from psutil.tests import reap_children
from psutil.tests import run_test_module_by_name
from psutil.tests import safe_mkdir
from psutil.tests import safe_rmpath
from psutil.tests import TESTFN
from psutil.tests import TESTFN_UNICODE
from psutil.tests import unittest
import psutil
import psutil.tests


# ===================================================================
# FS APIs
# ===================================================================


class _BaseFSAPIsTests(object):

    funky_name = None

    @classmethod
    def setUpClass(cls):
        cls.funky_dirname = cls.funky_name + '2'
        safe_rmpath(cls.funky_name)
        safe_mkdir(cls.funky_dirname)
        create_exe(cls.funky_name)

    @classmethod
    def tearDownClass(cls):
        safe_rmpath(cls.funky_name)
        safe_rmpath(cls.funky_dirname)

    def tearDown(self):
        reap_children()

    @classmethod
    def expect_exact_path_match(cls):
        # Do not expect psutil to correctly handle unicode paths on
        # Python 2 if os.listdir() is not able either.
        return PY3 or cls.funky_name in os.listdir('.')

    def test_proc_exe(self):
        subp = get_test_subprocess(cmd=[self.funky_name])
        p = psutil.Process(subp.pid)
        exe = p.exe()
        self.assertIsInstance(exe, str)
        if self.expect_exact_path_match():
            self.assertEqual(exe, self.funky_name)

    def test_proc_name(self):
        subp = get_test_subprocess(cmd=[self.funky_name])
        if WINDOWS:
            # On Windows name() is determined from exe() first, because
            # it's faster; we want to overcome the internal optimization
            # and test name() instead of exe().
            from psutil._pswindows import py2_strencode
            name = py2_strencode(psutil._psplatform.cext.proc_name(subp.pid))
        else:
            name = psutil.Process(subp.pid).name()
        self.assertIsInstance(name, str)
        if self.expect_exact_path_match():
            self.assertEqual(name, os.path.basename(self.funky_name))

    def test_proc_cmdline(self):
        subp = get_test_subprocess(cmd=[self.funky_name])
        p = psutil.Process(subp.pid)
        cmdline = p.cmdline()
        if self.expect_exact_path_match():
            self.assertEqual(cmdline, [self.funky_name])

    def test_proc_cwd(self):
        with chdir(self.funky_dirname):
            p = psutil.Process()
            cwd = p.cwd()
        self.assertIsInstance(p.cwd(), str)
        if self.expect_exact_path_match():
            self.assertEqual(cwd, self.funky_dirname)

    # @unittest.skipIf(APPVEYOR, "unreliable on APPVEYOR")
    def test_proc_open_files(self):
        p = psutil.Process()
        start = set(p.open_files())
        with open(self.funky_name, 'wb'):
            new = set(p.open_files())
        path = (new - start).pop().path
        if BSD and not path:
            # XXX
            # see https://github.com/giampaolo/psutil/issues/595
            return self.skipTest("open_files on BSD is broken")
        self.assertIsInstance(path, str)
        if self.expect_exact_path_match():
            self.assertEqual(os.path.normcase(path),
                             os.path.normcase(self.funky_name))

    def test_disk_usage(self):
        psutil.disk_usage(self.funky_dirname)


@unittest.skipIf(ASCII_FS, "ASCII fs")
class TestFSAPIs(_BaseFSAPIsTests, unittest.TestCase):
    """Test FS APIs with a funky, valid, UTF8 path name."""
    funky_name = TESTFN_UNICODE


class TestFSAPIsWithInvalidPath(_BaseFSAPIsTests, unittest.TestCase):
    """Test FS APIs with a funky, invalid path name."""
    if PY3:
        funky_name = (TESTFN.encode('utf8') + b"f\xc0\x80").decode(
            'utf8', 'surrogateescape')
    else:
        funky_name = TESTFN + "f\xc0\x80"


# ===================================================================
# FS APIs
# ===================================================================


class TestOtherAPIS(unittest.TestCase):
    """Unicode tests for non fs-related APIs."""

    @unittest.skipUnless(hasattr(psutil.Process, "environ"),
                         "platform not supported")
    def test_proc_environ(self):
        # Note: differently from others, this test does not deal
        # with fs paths. On Python 2 subprocess module is broken as
        # it's not able to handle with non-ASCII env vars, so
        # we use "è", which is part of the extended ASCII table
        # (unicode point <= 255).
        env = os.environ.copy()
        funny_str = TESTFN_UNICODE if PY3 else 'è'
        env['FUNNY_ARG'] = funny_str
        sproc = get_test_subprocess(env=env)
        p = psutil.Process(sproc.pid)
        env = p.environ()
        self.assertEqual(env['FUNNY_ARG'], funny_str)


if __name__ == '__main__':
    run_test_module_by_name(__file__)
