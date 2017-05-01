#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Notes about unicode handling in psutil
======================================

In psutil these are the APIs returning or dealing with a string
('not tested' means they are not tested to deal with non-ASCII strings):

- Process.cmdline()
- Process.connections('unix')
- Process.cwd()
- Process.environ()
- Process.exe()
- Process.memory_maps()
- Process.name()
- Process.open_files()
- Process.username()             (not tested)

- disk_io_counters()             (not tested)
- disk_partitions()              (not tested)
- disk_usage(str)
- net_connections('unix')
- net_if_addrs()                 (not tested)
- net_if_stats()                 (not tested)
- net_io_counters()              (not tested)
- sensors_fans()                 (not tested)
- sensors_temperatures()         (not tested)
- users()                        (not tested)

- WindowsService.binpath()       (not tested)
- WindowsService.description()   (not tested)
- WindowsService.display_name()  (not tested)
- WindowsService.name()          (not tested)
- WindowsService.status()        (not tested)
- WindowsService.username()      (not tested)

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

As such we also test that all APIs on Python 2 always return str and
never unicode (in test_contracts.py).
"""

import os
from contextlib import closing

from psutil import BSD
from psutil import OSX
from psutil import POSIX
from psutil import WINDOWS
from psutil._compat import PY3
from psutil.tests import ASCII_FS
from psutil.tests import bind_unix_socket
from psutil.tests import chdir
from psutil.tests import copyload_shared_lib
from psutil.tests import create_exe
from psutil.tests import get_test_subprocess
from psutil.tests import HAS_ENVIRON
from psutil.tests import HAS_MEMORY_MAPS
from psutil.tests import reap_children
from psutil.tests import run_test_module_by_name
from psutil.tests import safe_mkdir
from psutil.tests import safe_rmpath
from psutil.tests import skip_on_access_denied
from psutil.tests import TESTFILE_PREFIX
from psutil.tests import TESTFN
from psutil.tests import TESTFN_UNICODE
from psutil.tests import TRAVIS
from psutil.tests import unittest
from psutil.tests import unix_socket_path
import psutil
import psutil.tests


def can_deal_with_funky_name(name):
    """Return True if both the fs and the subprocess module can
    deal with a funky file name.
    """
    if PY3:
        return True
    try:
        safe_rmpath(name)
        create_exe(name)
        get_test_subprocess(cmd=[name])
    except UnicodeEncodeError:
        return False
    else:
        reap_children()
        return True


if PY3:
    INVALID_NAME = (TESTFN.encode('utf8') + b"f\xc0\x80").decode(
        'utf8', 'surrogateescape')
else:
    INVALID_NAME = TESTFN + "f\xc0\x80"
UNICODE_OK = can_deal_with_funky_name(TESTFN_UNICODE)
INVALID_UNICODE_OK = can_deal_with_funky_name(INVALID_NAME)


# ===================================================================
# FS APIs
# ===================================================================


class _BaseFSAPIsTests(object):
    funky_name = None

    def setUp(self):
        safe_rmpath(self.funky_name)

    def tearDown(self):
        reap_children()
        safe_rmpath(self.funky_name)

    def expect_exact_path_match(self):
        raise NotImplementedError("must be implemented in subclass")

    def test_proc_exe(self):
        create_exe(self.funky_name)
        subp = get_test_subprocess(cmd=[self.funky_name])
        p = psutil.Process(subp.pid)
        exe = p.exe()
        self.assertIsInstance(exe, str)
        if self.expect_exact_path_match():
            self.assertEqual(exe, self.funky_name)

    def test_proc_name(self):
        create_exe(self.funky_name)
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
        create_exe(self.funky_name)
        subp = get_test_subprocess(cmd=[self.funky_name])
        p = psutil.Process(subp.pid)
        cmdline = p.cmdline()
        for part in cmdline:
            self.assertIsInstance(part, str)
        if self.expect_exact_path_match():
            self.assertEqual(cmdline, [self.funky_name])

    def test_proc_cwd(self):
        safe_mkdir(self.funky_name)
        with chdir(self.funky_name):
            p = psutil.Process()
            cwd = p.cwd()
        self.assertIsInstance(p.cwd(), str)
        if self.expect_exact_path_match():
            self.assertEqual(cwd, self.funky_name)

    def test_proc_open_files(self):
        p = psutil.Process()
        start = set(p.open_files())
        with open(self.funky_name, 'wb'):
            new = set(p.open_files())
        path = (new - start).pop().path
        self.assertIsInstance(path, str)
        if BSD and not path:
            # XXX - see https://github.com/giampaolo/psutil/issues/595
            return self.skipTest("open_files on BSD is broken")
        if self.expect_exact_path_match():
            self.assertEqual(os.path.normcase(path),
                             os.path.normcase(self.funky_name))

    @unittest.skipIf(not POSIX, "POSIX only")
    def test_proc_connections(self):
        suffix = os.path.basename(self.funky_name)
        with unix_socket_path(suffix=suffix) as name:
            try:
                sock = bind_unix_socket(name)
            except UnicodeEncodeError:
                if PY3:
                    raise
                else:
                    raise unittest.SkipTest("not supported")
            with closing(sock):
                conn = psutil.Process().connections('unix')[0]
                self.assertIsInstance(conn.laddr, str)
                self.assertEqual(conn.laddr, name)

    @unittest.skipIf(not POSIX, "POSIX only")
    @skip_on_access_denied()
    def test_net_connections(self):
        def find_sock(cons):
            for conn in cons:
                if os.path.basename(conn.laddr).startswith(TESTFILE_PREFIX):
                    return conn
            raise ValueError("connection not found")

        suffix = os.path.basename(self.funky_name)
        with unix_socket_path(suffix=suffix) as name:
            try:
                sock = bind_unix_socket(name)
            except UnicodeEncodeError:
                if PY3:
                    raise
                else:
                    raise unittest.SkipTest("not supported")
            with closing(sock):
                cons = psutil.net_connections(kind='unix')
                conn = find_sock(cons)
                self.assertIsInstance(conn.laddr, str)
                self.assertEqual(conn.laddr, name)

    def test_disk_usage(self):
        safe_mkdir(self.funky_name)
        psutil.disk_usage(self.funky_name)

    @unittest.skipIf(not HAS_MEMORY_MAPS, "not supported")
    def test_memory_maps(self):
        p = psutil.Process()
        ext = ".so" if POSIX else ".dll"
        old = [x.path for x in p.memory_maps()
               if os.path.normcase(x.path).endswith(ext)][0]
        try:
            new = os.path.normcase(
                copyload_shared_lib(old, dst_prefix=self.funky_name))
        except UnicodeEncodeError:
            if PY3:
                raise
            else:
                raise unittest.SkipTest("ctypes can't handle unicode")
        newpaths = [os.path.normcase(x.path) for x in p.memory_maps()]
        self.assertIn(new, newpaths)


@unittest.skipIf(OSX and TRAVIS, "unreliable on TRAVIS")  # TODO
@unittest.skipIf(ASCII_FS, "ASCII fs")
@unittest.skipIf(not UNICODE_OK, "subprocess can't deal with unicode")
class TestFSAPIs(_BaseFSAPIsTests, unittest.TestCase):
    """Test FS APIs with a funky, valid, UTF8 path name."""
    funky_name = TESTFN_UNICODE

    @classmethod
    def expect_exact_path_match(cls):
        # Do not expect psutil to correctly handle unicode paths on
        # Python 2 if os.listdir() is not able either.
        return PY3 or cls.funky_name in os.listdir('.')


@unittest.skipIf(OSX and TRAVIS, "unreliable on TRAVIS")  # TODO
@unittest.skipIf(not INVALID_UNICODE_OK,
                 "subprocess can't deal with invalid unicode")
class TestFSAPIsWithInvalidPath(_BaseFSAPIsTests, unittest.TestCase):
    """Test FS APIs with a funky, invalid path name."""
    funky_name = INVALID_NAME

    @classmethod
    def expect_exact_path_match(cls):
        # Invalid unicode names are supposed to work on Python 2.
        return True


@unittest.skipIf(not WINDOWS, "WINDOWS only")
class TestWinProcessName(unittest.TestCase):

    def test_name_type(self):
        # On Windows name() is determined from exe() first, because
        # it's faster; we want to overcome the internal optimization
        # and test name() instead of exe().
        from psutil._pswindows import py2_strencode
        name = py2_strencode(psutil._psplatform.cext.proc_name(os.getpid()))
        self.assertIsInstance(name, str)


# ===================================================================
# Non fs APIs
# ===================================================================


class TestNonFSAPIS(unittest.TestCase):
    """Unicode tests for non fs-related APIs."""

    @unittest.skipIf(not HAS_ENVIRON, "not supported")
    def test_proc_environ(self):
        # Note: differently from others, this test does not deal
        # with fs paths. On Python 2 subprocess module is broken as
        # it's not able to handle with non-ASCII env vars, so
        # we use "è", which is part of the extended ASCII table
        # (unicode point <= 255).
        env = os.environ.copy()
        funky_str = TESTFN_UNICODE if PY3 else 'è'
        env['FUNNY_ARG'] = funky_str
        sproc = get_test_subprocess(env=env)
        p = psutil.Process(sproc.pid)
        env = p.environ()
        for k, v in env.items():
            self.assertIsInstance(k, str)
            self.assertIsInstance(v, str)
        self.assertEqual(env['FUNNY_ARG'], funky_str)


if __name__ == '__main__':
    run_test_module_by_name(__file__)
