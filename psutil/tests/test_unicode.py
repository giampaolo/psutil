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

* Process.cmdline()
* Process.connections('unix')
* Process.cwd()
* Process.environ()
* Process.exe()
* Process.memory_maps()
* Process.name()
* Process.open_files()
* Process.username()             (not tested)

* disk_io_counters()             (not tested)
* disk_partitions()              (not tested)
* disk_usage(str)
* net_connections('unix')
* net_if_addrs()                 (not tested)
* net_if_stats()                 (not tested)
* net_io_counters()              (not tested)
* sensors_fans()                 (not tested)
* sensors_temperatures()         (not tested)
* users()                        (not tested)

* WindowsService.binpath()       (not tested)
* WindowsService.description()   (not tested)
* WindowsService.display_name()  (not tested)
* WindowsService.name()          (not tested)
* WindowsService.status()        (not tested)
* WindowsService.username()      (not tested)

In here we create a unicode path with a funky non-ASCII name and (where
possible) make psutil return it back (e.g. on name(), exe(), open_files(),
etc.) and make sure that:

* psutil never crashes with UnicodeDecodeError
* the returned path matches

For a detailed explanation of how psutil handles unicode see:
- https://github.com/giampaolo/psutil/issues/1040
- http://psutil.readthedocs.io/#unicode
"""

import os
import traceback
import warnings
from contextlib import closing

from psutil import BSD
from psutil import MACOS
from psutil import OPENBSD
from psutil import POSIX
from psutil import WINDOWS
from psutil._compat import PY3
from psutil._compat import u
from psutil.tests import APPVEYOR
from psutil.tests import ASCII_FS
from psutil.tests import bind_unix_socket
from psutil.tests import chdir
from psutil.tests import copyload_shared_lib
from psutil.tests import create_exe
from psutil.tests import get_test_subprocess
from psutil.tests import HAS_CONNECTIONS_UNIX
from psutil.tests import HAS_ENVIRON
from psutil.tests import HAS_MEMORY_MAPS
from psutil.tests import mock
from psutil.tests import PYPY
from psutil.tests import reap_children
from psutil.tests import run_test_module_by_name
from psutil.tests import safe_mkdir
from psutil.tests import safe_rmpath as _safe_rmpath
from psutil.tests import skip_on_access_denied
from psutil.tests import TESTFILE_PREFIX
from psutil.tests import TESTFN
from psutil.tests import TESTFN_UNICODE
from psutil.tests import TRAVIS
from psutil.tests import unittest
from psutil.tests import unix_socket_path
import psutil


def safe_rmpath(path):
    if APPVEYOR:
        # TODO - this is quite random and I'm not sure why it happens,
        # nor I can reproduce it locally:
        # https://ci.appveyor.com/project/giampaolo/psutil/build/job/
        #     jiq2cgd6stsbtn60
        # safe_rmpath() happens after reap_children() so this is weird
        # Perhaps wait_procs() on Windows is broken? Maybe because
        # of STILL_ACTIVE?
        # https://github.com/giampaolo/psutil/blob/
        #     68c7a70728a31d8b8b58f4be6c4c0baa2f449eda/psutil/arch/
        #     windows/process_info.c#L146
        try:
            return _safe_rmpath(path)
        except WindowsError:
            traceback.print_exc()
    else:
        return _safe_rmpath(path)


def subprocess_supports_unicode(name):
    """Return True if both the fs and the subprocess module can
    deal with a unicode file name.
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
        return True
    finally:
        reap_children()


# An invalid unicode string.
if PY3:
    INVALID_NAME = (TESTFN.encode('utf8') + b"f\xc0\x80").decode(
        'utf8', 'surrogateescape')
else:
    INVALID_NAME = TESTFN + "f\xc0\x80"


# ===================================================================
# FS APIs
# ===================================================================


class _BaseFSAPIsTests(object):
    funky_name = None

    @classmethod
    def setUpClass(cls):
        safe_rmpath(cls.funky_name)
        create_exe(cls.funky_name)

    @classmethod
    def tearDownClass(cls):
        reap_children()
        safe_rmpath(cls.funky_name)

    def tearDown(self):
        reap_children()

    def expect_exact_path_match(self):
        raise NotImplementedError("must be implemented in subclass")

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
            with mock.patch("psutil._psplatform.cext.proc_exe",
                            side_effect=psutil.AccessDenied(os.getpid())) as m:
                name = psutil.Process(subp.pid).name()
                assert m.called
        else:
            name = psutil.Process(subp.pid).name()
        self.assertIsInstance(name, str)
        if self.expect_exact_path_match():
            self.assertEqual(name, os.path.basename(self.funky_name))

    def test_proc_cmdline(self):
        subp = get_test_subprocess(cmd=[self.funky_name])
        p = psutil.Process(subp.pid)
        cmdline = p.cmdline()
        for part in cmdline:
            self.assertIsInstance(part, str)
        if self.expect_exact_path_match():
            self.assertEqual(cmdline, [self.funky_name])

    def test_proc_cwd(self):
        dname = self.funky_name + "2"
        self.addCleanup(safe_rmpath, dname)
        safe_mkdir(dname)
        with chdir(dname):
            p = psutil.Process()
            cwd = p.cwd()
        self.assertIsInstance(p.cwd(), str)
        if self.expect_exact_path_match():
            self.assertEqual(cwd, dname)

    def test_proc_open_files(self):
        p = psutil.Process()
        start = set(p.open_files())
        with open(self.funky_name, 'rb'):
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
                # AF_UNIX addr not set on OpenBSD
                if not OPENBSD:
                    self.assertEqual(conn.laddr, name)

    @unittest.skipIf(not POSIX, "POSIX only")
    @unittest.skipIf(not HAS_CONNECTIONS_UNIX, "can't list UNIX sockets")
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
                # AF_UNIX addr not set on OpenBSD
                if not OPENBSD:
                    conn = find_sock(cons)
                    self.assertIsInstance(conn.laddr, str)
                    self.assertEqual(conn.laddr, name)

    def test_disk_usage(self):
        dname = self.funky_name + "2"
        self.addCleanup(safe_rmpath, dname)
        safe_mkdir(dname)
        psutil.disk_usage(dname)

    @unittest.skipIf(not HAS_MEMORY_MAPS, "not supported")
    @unittest.skipIf(not PY3, "ctypes does not support unicode on PY2")
    def test_memory_maps(self):
        # XXX: on Python 2, using ctypes.CDLL with a unicode path
        # opens a message box which blocks the test run.
        with copyload_shared_lib(dst_prefix=self.funky_name) as funky_path:
            def normpath(p):
                return os.path.realpath(os.path.normcase(p))
            libpaths = [normpath(x.path)
                        for x in psutil.Process().memory_maps()]
            # ...just to have a clearer msg in case of failure
            libpaths = [x for x in libpaths if TESTFILE_PREFIX in x]
            self.assertIn(normpath(funky_path), libpaths)
            for path in libpaths:
                self.assertIsInstance(path, str)


# https://travis-ci.org/giampaolo/psutil/jobs/440073249
@unittest.skipIf(PYPY and TRAVIS, "unreliable on PYPY + TRAVIS")
@unittest.skipIf(MACOS and TRAVIS, "unreliable on TRAVIS")  # TODO
@unittest.skipIf(ASCII_FS, "ASCII fs")
@unittest.skipIf(not subprocess_supports_unicode(TESTFN_UNICODE),
                 "subprocess can't deal with unicode")
class TestFSAPIs(_BaseFSAPIsTests, unittest.TestCase):
    """Test FS APIs with a funky, valid, UTF8 path name."""
    funky_name = TESTFN_UNICODE

    @classmethod
    def expect_exact_path_match(cls):
        # Do not expect psutil to correctly handle unicode paths on
        # Python 2 if os.listdir() is not able either.
        if PY3:
            return True
        else:
            here = '.' if isinstance(cls.funky_name, str) else u('.')
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                return cls.funky_name in os.listdir(here)


@unittest.skipIf(PYPY and TRAVIS, "unreliable on PYPY + TRAVIS")
@unittest.skipIf(MACOS and TRAVIS, "unreliable on TRAVIS")  # TODO
@unittest.skipIf(not subprocess_supports_unicode(INVALID_NAME),
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
        with mock.patch("psutil._psplatform.cext.proc_exe",
                        side_effect=psutil.AccessDenied(os.getpid())) as m:
            self.assertIsInstance(psutil.Process().name(), str)
            assert m.called


# ===================================================================
# Non fs APIs
# ===================================================================


class TestNonFSAPIS(unittest.TestCase):
    """Unicode tests for non fs-related APIs."""

    def tearDown(self):
        reap_children()

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
