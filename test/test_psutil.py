#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
psutil test suite. Run it with:
$ make test

If you're on Python < 2.7 unittest2 module must be installed first:
https://pypi.python.org/pypi/unittest2
"""

from __future__ import division

import ast
import atexit
import collections
import contextlib
import datetime
import errno
import functools
import imp
import json
import os
import pickle
import pprint
import re
import select
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import traceback
import types
import warnings
from socket import AF_INET, SOCK_STREAM, SOCK_DGRAM
try:
    import ipaddress  # python >= 3.3
except ImportError:
    ipaddress = None
try:
    from unittest import mock  # py3
except ImportError:
    import mock  # requires "pip install mock"

import psutil
from psutil._compat import PY3, callable, long, unicode

if sys.version_info < (2, 7):
    import unittest2 as unittest  # https://pypi.python.org/pypi/unittest2
else:
    import unittest
if sys.version_info >= (3, 4):
    import enum
else:
    enum = None


# ===================================================================
# --- Constants
# ===================================================================

# conf for retry_before_failing() decorator
NO_RETRIES = 10
# bytes tolerance for OS memory related tests
TOLERANCE = 500 * 1024  # 500KB
# the timeout used in functions which have to wait
GLOBAL_TIMEOUT = 3

AF_INET6 = getattr(socket, "AF_INET6")
AF_UNIX = getattr(socket, "AF_UNIX", None)
PYTHON = os.path.realpath(sys.executable)
DEVNULL = open(os.devnull, 'r+')
TESTFN = os.path.join(os.getcwd(), "$testfile")
TESTFN_UNICODE = TESTFN + "ƒőő"
TESTFILE_PREFIX = 'psutil-test-suite-'
if not PY3:
    try:
        TESTFN_UNICODE = unicode(TESTFN_UNICODE, sys.getfilesystemencoding())
    except UnicodeDecodeError:
        TESTFN_UNICODE = TESTFN + "???"

EXAMPLES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
                               '..', 'examples'))

POSIX = os.name == 'posix'
WINDOWS = os.name == 'nt'
if WINDOWS:
    WIN_VISTA = (6, 0, 0)
LINUX = sys.platform.startswith("linux")
OSX = sys.platform.startswith("darwin")
BSD = sys.platform.startswith("freebsd")
SUNOS = sys.platform.startswith("sunos")
VALID_PROC_STATUSES = [getattr(psutil, x) for x in dir(psutil)
                       if x.startswith('STATUS_')]
# whether we're running this test suite on Travis (https://travis-ci.org/)
TRAVIS = bool(os.environ.get('TRAVIS'))
# whether we're running this test suite on Appveyor for Windows
# (http://www.appveyor.com/)
APPVEYOR = bool(os.environ.get('APPVEYOR'))

if TRAVIS or 'tox' in sys.argv[0]:
    import ipaddress
if TRAVIS or APPVEYOR:
    GLOBAL_TIMEOUT = GLOBAL_TIMEOUT * 4


# ===================================================================
# --- Utility functions
# ===================================================================

def cleanup():
    reap_children(search_all=True)
    safe_remove(TESTFN)
    try:
        safe_rmdir(TESTFN_UNICODE)
    except UnicodeEncodeError:
        pass
    for path in _testfiles:
        safe_remove(path)

atexit.register(cleanup)
atexit.register(lambda: DEVNULL.close())


_subprocesses_started = set()


def get_test_subprocess(cmd=None, stdout=DEVNULL, stderr=DEVNULL,
                        stdin=DEVNULL, wait=False):
    """Return a subprocess.Popen object to use in tests.
    By default stdout and stderr are redirected to /dev/null and the
    python interpreter is used as test process.
    If 'wait' is True attemps to make sure the process is in a
    reasonably initialized state.
    """
    if cmd is None:
        pyline = ""
        if wait:
            pyline += "open(r'%s', 'w'); " % TESTFN
        pyline += "import time; time.sleep(60);"
        cmd_ = [PYTHON, "-c", pyline]
    else:
        cmd_ = cmd
    sproc = subprocess.Popen(cmd_, stdout=stdout, stderr=stderr, stdin=stdin)
    if wait:
        if cmd is None:
            stop_at = time.time() + 3
            while stop_at > time.time():
                if os.path.exists(TESTFN):
                    break
                time.sleep(0.001)
            else:
                warn("couldn't make sure test file was actually created")
        else:
            wait_for_pid(sproc.pid)
    _subprocesses_started.add(psutil.Process(sproc.pid))
    return sproc


_testfiles = []


def pyrun(src):
    """Run python code 'src' in a separate interpreter.
    Return interpreter subprocess.
    """
    if PY3:
        src = bytes(src, 'ascii')
    with tempfile.NamedTemporaryFile(
            prefix=TESTFILE_PREFIX, delete=False) as f:
        _testfiles.append(f.name)
        f.write(src)
        f.flush()
        subp = get_test_subprocess([PYTHON, f.name], stdout=None,
                                   stderr=None)
        wait_for_pid(subp.pid)
        return subp


def warn(msg):
    """Raise a warning msg."""
    warnings.warn(msg, UserWarning)


def sh(cmdline, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
    """run cmd in a subprocess and return its output.
    raises RuntimeError on error.
    """
    p = subprocess.Popen(cmdline, shell=True, stdout=stdout, stderr=stderr)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        raise RuntimeError(stderr)
    if stderr:
        warn(stderr)
    if PY3:
        stdout = str(stdout, sys.stdout.encoding)
    return stdout.strip()


def which(program):
    """Same as UNIX which command. Return None on command not found."""
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None


if POSIX:
    def get_kernel_version():
        """Return a tuple such as (2, 6, 36)."""
        s = ""
        uname = os.uname()[2]
        for c in uname:
            if c.isdigit() or c == '.':
                s += c
            else:
                break
        if not s:
            raise ValueError("can't parse %r" % uname)
        minor = 0
        micro = 0
        nums = s.split('.')
        major = int(nums[0])
        if len(nums) >= 2:
            minor = int(nums[1])
        if len(nums) >= 3:
            micro = int(nums[2])
        return (major, minor, micro)


if LINUX:
    RLIMIT_SUPPORT = get_kernel_version() >= (2, 6, 36)
else:
    RLIMIT_SUPPORT = False


def wait_for_pid(pid, timeout=GLOBAL_TIMEOUT):
    """Wait for pid to show up in the process list then return.
    Used in the test suite to give time the sub process to initialize.
    """
    raise_at = time.time() + timeout
    while True:
        if pid in psutil.pids():
            # give it one more iteration to allow full initialization
            time.sleep(0.01)
            return
        time.sleep(0.0001)
        if time.time() >= raise_at:
            raise RuntimeError("Timed out")


def wait_for_file(fname, timeout=GLOBAL_TIMEOUT, delete_file=True):
    """Wait for a file to be written on disk."""
    stop_at = time.time() + 3
    while time.time() < stop_at:
        try:
            with open(fname, "r") as f:
                data = f.read()
            if not data:
                continue
            if delete_file:
                os.remove(fname)
            return data
        except IOError:
            time.sleep(0.001)
    raise RuntimeError("timed out (couldn't read file)")


def reap_children(search_all=False):
    """Kill any subprocess started by this test suite and ensure that
    no zombies stick around to hog resources and create problems when
    looking for refleaks.
    """
    global _subprocesses_started
    procs = _subprocesses_started.copy()
    if search_all:
        this_process = psutil.Process()
        for p in this_process.children(recursive=True):
            procs.add(p)
    for p in procs:
        try:
            p.terminate()
        except psutil.NoSuchProcess:
            pass
    gone, alive = psutil.wait_procs(procs, timeout=GLOBAL_TIMEOUT)
    for p in alive:
        warn("couldn't terminate process %s" % p)
        try:
            p.kill()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(alive, timeout=GLOBAL_TIMEOUT)
    if alive:
        warn("couldn't not kill processes %s" % str(alive))
    _subprocesses_started = set(alive)


def check_ip_address(addr, family):
    """Attempts to check IP address's validity."""
    if enum and PY3:
        assert isinstance(family, enum.IntEnum), family
    if family == AF_INET:
        octs = [int(x) for x in addr.split('.')]
        assert len(octs) == 4, addr
        for num in octs:
            assert 0 <= num <= 255, addr
        if ipaddress:
            if not PY3:
                addr = unicode(addr)
            ipaddress.IPv4Address(addr)
    elif family == AF_INET6:
        assert isinstance(addr, str), addr
        if ipaddress:
            if not PY3:
                addr = unicode(addr)
            ipaddress.IPv6Address(addr)
    elif family == psutil.AF_LINK:
        assert re.match('([a-fA-F0-9]{2}[:|\-]?){6}', addr) is not None, addr
    else:
        raise ValueError("unknown family %r", family)


def check_connection_ntuple(conn):
    """Check validity of a connection namedtuple."""
    valid_conn_states = [getattr(psutil, x) for x in dir(psutil) if
                         x.startswith('CONN_')]
    assert conn[0] == conn.fd
    assert conn[1] == conn.family
    assert conn[2] == conn.type
    assert conn[3] == conn.laddr
    assert conn[4] == conn.raddr
    assert conn[5] == conn.status
    assert conn.type in (SOCK_STREAM, SOCK_DGRAM), repr(conn.type)
    assert conn.family in (AF_INET, AF_INET6, AF_UNIX), repr(conn.family)
    assert conn.status in valid_conn_states, conn.status

    # check IP address and port sanity
    for addr in (conn.laddr, conn.raddr):
        if not addr:
            continue
        if conn.family in (AF_INET, AF_INET6):
            assert isinstance(addr, tuple), addr
            ip, port = addr
            assert isinstance(port, int), port
            assert 0 <= port <= 65535, port
            check_ip_address(ip, conn.family)
        elif conn.family == AF_UNIX:
            assert isinstance(addr, (str, None)), addr
        else:
            raise ValueError("unknown family %r", conn.family)

    if conn.family in (AF_INET, AF_INET6):
        # actually try to bind the local socket; ignore IPv6
        # sockets as their address might be represented as
        # an IPv4-mapped-address (e.g. "::127.0.0.1")
        # and that's rejected by bind()
        if conn.family == AF_INET:
            s = socket.socket(conn.family, conn.type)
            with contextlib.closing(s):
                try:
                    s.bind((conn.laddr[0], 0))
                except socket.error as err:
                    if err.errno != errno.EADDRNOTAVAIL:
                        raise
    elif conn.family == AF_UNIX:
        assert not conn.raddr, repr(conn.raddr)
        assert conn.status == psutil.CONN_NONE, conn.status

    if getattr(conn, 'fd', -1) != -1:
        assert conn.fd > 0, conn
        if hasattr(socket, 'fromfd') and not WINDOWS:
            try:
                dupsock = socket.fromfd(conn.fd, conn.family, conn.type)
            except (socket.error, OSError) as err:
                if err.args[0] != errno.EBADF:
                    raise
            else:
                with contextlib.closing(dupsock):
                    assert dupsock.family == conn.family
                    assert dupsock.type == conn.type


def safe_remove(file):
    "Convenience function for removing temporary test files"
    try:
        os.remove(file)
    except OSError as err:
        if err.errno != errno.ENOENT:
            # file is being used by another process
            if WINDOWS and isinstance(err, WindowsError) and err.errno == 13:
                return
            raise


def safe_rmdir(dir):
    "Convenience function for removing temporary test directories"
    try:
        os.rmdir(dir)
    except OSError as err:
        if err.errno != errno.ENOENT:
            raise


def call_until(fun, expr, timeout=GLOBAL_TIMEOUT):
    """Keep calling function for timeout secs and exit if eval()
    expression is True.
    """
    stop_at = time.time() + timeout
    while time.time() < stop_at:
        ret = fun()
        if eval(expr):
            return ret
        time.sleep(0.001)
    raise RuntimeError('timed out (ret=%r)' % ret)


def retry_before_failing(ntimes=None):
    """Decorator which runs a test function and retries N times before
    actually failing.
    """
    def decorator(fun):
        @functools.wraps(fun)
        def wrapper(*args, **kwargs):
            for x in range(ntimes or NO_RETRIES):
                try:
                    return fun(*args, **kwargs)
                except AssertionError:
                    pass
            raise
        return wrapper
    return decorator


def skip_on_access_denied(only_if=None):
    """Decorator to Ignore AccessDenied exceptions."""
    def decorator(fun):
        @functools.wraps(fun)
        def wrapper(*args, **kwargs):
            try:
                return fun(*args, **kwargs)
            except psutil.AccessDenied:
                if only_if is not None:
                    if not only_if:
                        raise
                msg = "%r was skipped because it raised AccessDenied" \
                      % fun.__name__
                raise unittest.SkipTest(msg)
        return wrapper
    return decorator


def skip_on_not_implemented(only_if=None):
    """Decorator to Ignore NotImplementedError exceptions."""
    def decorator(fun):
        @functools.wraps(fun)
        def wrapper(*args, **kwargs):
            try:
                return fun(*args, **kwargs)
            except NotImplementedError:
                if only_if is not None:
                    if not only_if:
                        raise
                msg = "%r was skipped because it raised NotImplementedError" \
                      % fun.__name__
                raise unittest.SkipTest(msg)
        return wrapper
    return decorator


def supports_ipv6():
    """Return True if IPv6 is supported on this platform."""
    if not socket.has_ipv6 or not hasattr(socket, "AF_INET6"):
        return False
    sock = None
    try:
        sock = socket.socket(AF_INET6, SOCK_STREAM)
        sock.bind(("::1", 0))
    except (socket.error, socket.gaierror):
        return False
    else:
        return True
    finally:
        if sock is not None:
            sock.close()


if WINDOWS:
    def get_winver():
        wv = sys.getwindowsversion()
        if hasattr(wv, 'service_pack_major'):  # python >= 2.7
            sp = wv.service_pack_major or 0
        else:
            r = re.search("\s\d$", wv[4])
            if r:
                sp = int(r.group(0))
            else:
                sp = 0
        return (wv[0], wv[1], sp)


class ThreadTask(threading.Thread):
    """A thread object used for running process thread tests."""

    def __init__(self):
        threading.Thread.__init__(self)
        self._running = False
        self._interval = None
        self._flag = threading.Event()

    def __repr__(self):
        name = self.__class__.__name__
        return '<%s running=%s at %#x>' % (name, self._running, id(self))

    def start(self, interval=0.001):
        """Start thread and keep it running until an explicit
        stop() request. Polls for shutdown every 'timeout' seconds.
        """
        if self._running:
            raise ValueError("already started")
        self._interval = interval
        threading.Thread.start(self)
        self._flag.wait()

    def run(self):
        self._running = True
        self._flag.set()
        while self._running:
            time.sleep(self._interval)

    def stop(self):
        """Stop thread execution and and waits until it is stopped."""
        if not self._running:
            raise ValueError("already stopped")
        self._running = False
        self.join()


# ===================================================================
# --- System-related API tests
# ===================================================================

class TestSystemAPIs(unittest.TestCase):
    """Tests for system-related APIs."""

    def setUp(self):
        safe_remove(TESTFN)

    def tearDown(self):
        reap_children()

    def test_process_iter(self):
        self.assertIn(os.getpid(), [x.pid for x in psutil.process_iter()])
        sproc = get_test_subprocess()
        self.assertIn(sproc.pid, [x.pid for x in psutil.process_iter()])
        p = psutil.Process(sproc.pid)
        p.kill()
        p.wait()
        self.assertNotIn(sproc.pid, [x.pid for x in psutil.process_iter()])

    def test_wait_procs(self):
        def callback(p):
            l.append(p.pid)

        l = []
        sproc1 = get_test_subprocess()
        sproc2 = get_test_subprocess()
        sproc3 = get_test_subprocess()
        procs = [psutil.Process(x.pid) for x in (sproc1, sproc2, sproc3)]
        self.assertRaises(ValueError, psutil.wait_procs, procs, timeout=-1)
        self.assertRaises(TypeError, psutil.wait_procs, procs, callback=1)
        t = time.time()
        gone, alive = psutil.wait_procs(procs, timeout=0.01, callback=callback)

        self.assertLess(time.time() - t, 0.5)
        self.assertEqual(gone, [])
        self.assertEqual(len(alive), 3)
        self.assertEqual(l, [])
        for p in alive:
            self.assertFalse(hasattr(p, 'returncode'))

        @retry_before_failing(30)
        def test(procs, callback):
            gone, alive = psutil.wait_procs(procs, timeout=0.03,
                                            callback=callback)
            self.assertEqual(len(gone), 1)
            self.assertEqual(len(alive), 2)
            return gone, alive

        sproc3.terminate()
        gone, alive = test(procs, callback)
        self.assertIn(sproc3.pid, [x.pid for x in gone])
        if POSIX:
            self.assertEqual(gone.pop().returncode, signal.SIGTERM)
        else:
            self.assertEqual(gone.pop().returncode, 1)
        self.assertEqual(l, [sproc3.pid])
        for p in alive:
            self.assertFalse(hasattr(p, 'returncode'))

        @retry_before_failing(30)
        def test(procs, callback):
            gone, alive = psutil.wait_procs(procs, timeout=0.03,
                                            callback=callback)
            self.assertEqual(len(gone), 3)
            self.assertEqual(len(alive), 0)
            return gone, alive

        sproc1.terminate()
        sproc2.terminate()
        gone, alive = test(procs, callback)
        self.assertEqual(set(l), set([sproc1.pid, sproc2.pid, sproc3.pid]))
        for p in gone:
            self.assertTrue(hasattr(p, 'returncode'))

    def test_wait_procs_no_timeout(self):
        sproc1 = get_test_subprocess()
        sproc2 = get_test_subprocess()
        sproc3 = get_test_subprocess()
        procs = [psutil.Process(x.pid) for x in (sproc1, sproc2, sproc3)]
        for p in procs:
            p.terminate()
        gone, alive = psutil.wait_procs(procs)

    def test_boot_time(self):
        bt = psutil.boot_time()
        self.assertIsInstance(bt, float)
        self.assertGreater(bt, 0)
        self.assertLess(bt, time.time())

    @unittest.skipUnless(POSIX, 'posix only')
    def test_PAGESIZE(self):
        # pagesize is used internally to perform different calculations
        # and it's determined by using SC_PAGE_SIZE; make sure
        # getpagesize() returns the same value.
        import resource
        self.assertEqual(os.sysconf("SC_PAGE_SIZE"), resource.getpagesize())

    def test_virtual_memory(self):
        mem = psutil.virtual_memory()
        assert mem.total > 0, mem
        assert mem.available > 0, mem
        assert 0 <= mem.percent <= 100, mem
        assert mem.used > 0, mem
        assert mem.free >= 0, mem
        for name in mem._fields:
            value = getattr(mem, name)
            if name != 'percent':
                self.assertIsInstance(value, (int, long))
            if name != 'total':
                if not value >= 0:
                    self.fail("%r < 0 (%s)" % (name, value))
                if value > mem.total:
                    self.fail("%r > total (total=%s, %s=%s)"
                              % (name, mem.total, name, value))

    def test_swap_memory(self):
        mem = psutil.swap_memory()
        assert mem.total >= 0, mem
        assert mem.used >= 0, mem
        if mem.total > 0:
            # likely a system with no swap partition
            assert mem.free > 0, mem
        else:
            assert mem.free == 0, mem
        assert 0 <= mem.percent <= 100, mem
        assert mem.sin >= 0, mem
        assert mem.sout >= 0, mem

    def test_pid_exists(self):
        sproc = get_test_subprocess(wait=True)
        self.assertTrue(psutil.pid_exists(sproc.pid))
        p = psutil.Process(sproc.pid)
        p.kill()
        p.wait()
        self.assertFalse(psutil.pid_exists(sproc.pid))
        self.assertFalse(psutil.pid_exists(-1))
        self.assertEqual(psutil.pid_exists(0), 0 in psutil.pids())
        # pid 0
        psutil.pid_exists(0) == 0 in psutil.pids()

    def test_pid_exists_2(self):
        reap_children()
        pids = psutil.pids()
        for pid in pids:
            try:
                assert psutil.pid_exists(pid)
            except AssertionError:
                # in case the process disappeared in meantime fail only
                # if it is no longer in psutil.pids()
                time.sleep(.1)
                if pid in psutil.pids():
                    self.fail(pid)
        pids = range(max(pids) + 5000, max(pids) + 6000)
        for pid in pids:
            self.assertFalse(psutil.pid_exists(pid), msg=pid)

    def test_pids(self):
        plist = [x.pid for x in psutil.process_iter()]
        pidlist = psutil.pids()
        self.assertEqual(plist.sort(), pidlist.sort())
        # make sure every pid is unique
        self.assertEqual(len(pidlist), len(set(pidlist)))

    def test_test(self):
        # test for psutil.test() function
        stdout = sys.stdout
        sys.stdout = DEVNULL
        try:
            psutil.test()
        finally:
            sys.stdout = stdout

    def test_cpu_count(self):
        logical = psutil.cpu_count()
        self.assertEqual(logical, len(psutil.cpu_times(percpu=True)))
        self.assertGreaterEqual(logical, 1)
        #
        if LINUX:
            with open("/proc/cpuinfo") as fd:
                cpuinfo_data = fd.read()
            if "physical id" not in cpuinfo_data:
                raise unittest.SkipTest("cpuinfo doesn't include physical id")
        physical = psutil.cpu_count(logical=False)
        self.assertGreaterEqual(physical, 1)
        self.assertGreaterEqual(logical, physical)

    def test_sys_cpu_times(self):
        total = 0
        times = psutil.cpu_times()
        sum(times)
        for cp_time in times:
            self.assertIsInstance(cp_time, float)
            self.assertGreaterEqual(cp_time, 0.0)
            total += cp_time
        self.assertEqual(total, sum(times))
        str(times)
        if not WINDOWS:
            # CPU times are always supposed to increase over time or
            # remain the same but never go backwards, see:
            # https://github.com/giampaolo/psutil/issues/392
            last = psutil.cpu_times()
            for x in range(100):
                new = psutil.cpu_times()
                for field in new._fields:
                    new_t = getattr(new, field)
                    last_t = getattr(last, field)
                    self.assertGreaterEqual(new_t, last_t,
                                            msg="%s %s" % (new_t, last_t))
                last = new

    def test_sys_cpu_times2(self):
        t1 = sum(psutil.cpu_times())
        time.sleep(0.1)
        t2 = sum(psutil.cpu_times())
        difference = t2 - t1
        if not difference >= 0.05:
            self.fail("difference %s" % difference)

    def test_sys_per_cpu_times(self):
        for times in psutil.cpu_times(percpu=True):
            total = 0
            sum(times)
            for cp_time in times:
                self.assertIsInstance(cp_time, float)
                self.assertGreaterEqual(cp_time, 0.0)
                total += cp_time
            self.assertEqual(total, sum(times))
            str(times)
        self.assertEqual(len(psutil.cpu_times(percpu=True)[0]),
                         len(psutil.cpu_times(percpu=False)))

        # Note: in theory CPU times are always supposed to increase over
        # time or remain the same but never go backwards. In practice
        # sometimes this is not the case.
        # This issue seemd to be afflict Windows:
        # https://github.com/giampaolo/psutil/issues/392
        # ...but it turns out also Linux (rarely) behaves the same.
        # last = psutil.cpu_times(percpu=True)
        # for x in range(100):
        #     new = psutil.cpu_times(percpu=True)
        #     for index in range(len(new)):
        #         newcpu = new[index]
        #         lastcpu = last[index]
        #         for field in newcpu._fields:
        #             new_t = getattr(newcpu, field)
        #             last_t = getattr(lastcpu, field)
        #             self.assertGreaterEqual(
        #                 new_t, last_t, msg="%s %s" % (lastcpu, newcpu))
        #     last = new

    def test_sys_per_cpu_times_2(self):
        tot1 = psutil.cpu_times(percpu=True)
        stop_at = time.time() + 0.1
        while True:
            if time.time() >= stop_at:
                break
        tot2 = psutil.cpu_times(percpu=True)
        for t1, t2 in zip(tot1, tot2):
            t1, t2 = sum(t1), sum(t2)
            difference = t2 - t1
            if difference >= 0.05:
                return
        self.fail()

    def _test_cpu_percent(self, percent, last_ret, new_ret):
        try:
            self.assertIsInstance(percent, float)
            self.assertGreaterEqual(percent, 0.0)
            self.assertIsNot(percent, -0.0)
            self.assertLessEqual(percent, 100.0 * psutil.cpu_count())
        except AssertionError as err:
            raise AssertionError("\n%s\nlast=%s\nnew=%s" % (
                err, pprint.pformat(last_ret), pprint.pformat(new_ret)))

    def test_sys_cpu_percent(self):
        last = psutil.cpu_percent(interval=0.001)
        for x in range(100):
            new = psutil.cpu_percent(interval=None)
            self._test_cpu_percent(new, last, new)
            last = new

    def test_sys_per_cpu_percent(self):
        last = psutil.cpu_percent(interval=0.001, percpu=True)
        self.assertEqual(len(last), psutil.cpu_count())
        for x in range(100):
            new = psutil.cpu_percent(interval=None, percpu=True)
            for percent in new:
                self._test_cpu_percent(percent, last, new)
            last = new

    def test_sys_cpu_times_percent(self):
        last = psutil.cpu_times_percent(interval=0.001)
        for x in range(100):
            new = psutil.cpu_times_percent(interval=None)
            for percent in new:
                self._test_cpu_percent(percent, last, new)
            self._test_cpu_percent(sum(new), last, new)
            last = new

    def test_sys_per_cpu_times_percent(self):
        last = psutil.cpu_times_percent(interval=0.001, percpu=True)
        self.assertEqual(len(last), psutil.cpu_count())
        for x in range(100):
            new = psutil.cpu_times_percent(interval=None, percpu=True)
            for cpu in new:
                for percent in cpu:
                    self._test_cpu_percent(percent, last, new)
                self._test_cpu_percent(sum(cpu), last, new)
            last = new

    def test_sys_per_cpu_times_percent_negative(self):
        # see: https://github.com/giampaolo/psutil/issues/645
        psutil.cpu_times_percent(percpu=True)
        zero_times = [x._make([0 for x in range(len(x._fields))])
                      for x in psutil.cpu_times(percpu=True)]
        with mock.patch('psutil.cpu_times', return_value=zero_times):
            for cpu in psutil.cpu_times_percent(percpu=True):
                for percent in cpu:
                    self._test_cpu_percent(percent, None, None)

    @unittest.skipIf(POSIX and not hasattr(os, 'statvfs'),
                     "os.statvfs() function not available on this platform")
    def test_disk_usage(self):
        usage = psutil.disk_usage(os.getcwd())
        assert usage.total > 0, usage
        assert usage.used > 0, usage
        assert usage.free > 0, usage
        assert usage.total > usage.used, usage
        assert usage.total > usage.free, usage
        assert 0 <= usage.percent <= 100, usage.percent
        if hasattr(shutil, 'disk_usage'):
            # py >= 3.3, see: http://bugs.python.org/issue12442
            shutil_usage = shutil.disk_usage(os.getcwd())
            tolerance = 5 * 1024 * 1024  # 5MB
            self.assertEqual(usage.total, shutil_usage.total)
            self.assertAlmostEqual(usage.free, shutil_usage.free,
                                   delta=tolerance)
            self.assertAlmostEqual(usage.used, shutil_usage.used,
                                   delta=tolerance)

        # if path does not exist OSError ENOENT is expected across
        # all platforms
        fname = tempfile.mktemp()
        try:
            psutil.disk_usage(fname)
        except OSError as err:
            if err.args[0] != errno.ENOENT:
                raise
        else:
            self.fail("OSError not raised")

    @unittest.skipIf(POSIX and not hasattr(os, 'statvfs'),
                     "os.statvfs() function not available on this platform")
    def test_disk_usage_unicode(self):
        # see: https://github.com/giampaolo/psutil/issues/416
        # XXX this test is not really reliable as it always fails on
        # Python 3.X (2.X is fine)
        try:
            safe_rmdir(TESTFN_UNICODE)
            os.mkdir(TESTFN_UNICODE)
            psutil.disk_usage(TESTFN_UNICODE)
            safe_rmdir(TESTFN_UNICODE)
        except UnicodeEncodeError:
            pass

    @unittest.skipIf(POSIX and not hasattr(os, 'statvfs'),
                     "os.statvfs() function not available on this platform")
    @unittest.skipIf(LINUX and TRAVIS, "unknown failure on travis")
    def test_disk_partitions(self):
        # all = False
        ls = psutil.disk_partitions(all=False)
        # on travis we get:
        #     self.assertEqual(p.cpu_affinity(), [n])
        # AssertionError: Lists differ: [0, 1, 2, 3, 4, 5, 6, 7,... != [0]
        self.assertTrue(ls, msg=ls)
        for disk in ls:
            if WINDOWS and 'cdrom' in disk.opts:
                continue
            if not POSIX:
                assert os.path.exists(disk.device), disk
            else:
                # we cannot make any assumption about this, see:
                # http://goo.gl/p9c43
                disk.device
            if SUNOS:
                # on solaris apparently mount points can also be files
                assert os.path.exists(disk.mountpoint), disk
            else:
                assert os.path.isdir(disk.mountpoint), disk
            assert disk.fstype, disk
            self.assertIsInstance(disk.opts, str)

        # all = True
        ls = psutil.disk_partitions(all=True)
        self.assertTrue(ls, msg=ls)
        for disk in psutil.disk_partitions(all=True):
            if not WINDOWS:
                try:
                    os.stat(disk.mountpoint)
                except OSError as err:
                    # http://mail.python.org/pipermail/python-dev/
                    #     2012-June/120787.html
                    if err.errno not in (errno.EPERM, errno.EACCES):
                        raise
                else:
                    if SUNOS:
                        # on solaris apparently mount points can also be files
                        assert os.path.exists(disk.mountpoint), disk
                    else:
                        assert os.path.isdir(disk.mountpoint), disk
            self.assertIsInstance(disk.fstype, str)
            self.assertIsInstance(disk.opts, str)

        def find_mount_point(path):
            path = os.path.abspath(path)
            while not os.path.ismount(path):
                path = os.path.dirname(path)
            return path

        mount = find_mount_point(__file__)
        mounts = [x.mountpoint for x in psutil.disk_partitions(all=True)]
        self.assertIn(mount, mounts)
        psutil.disk_usage(mount)

    @skip_on_access_denied()
    def test_net_connections(self):
        def check(cons, families, types_):
            for conn in cons:
                self.assertIn(conn.family, families, msg=conn)
                if conn.family != getattr(socket, 'AF_UNIX', object()):
                    self.assertIn(conn.type, types_, msg=conn)

        from psutil._common import conn_tmap
        for kind, groups in conn_tmap.items():
            if SUNOS and kind == 'unix':
                continue
            families, types_ = groups
            cons = psutil.net_connections(kind)
            self.assertEqual(len(cons), len(set(cons)))
            check(cons, families, types_)

    def test_net_io_counters(self):
        def check_ntuple(nt):
            self.assertEqual(nt[0], nt.bytes_sent)
            self.assertEqual(nt[1], nt.bytes_recv)
            self.assertEqual(nt[2], nt.packets_sent)
            self.assertEqual(nt[3], nt.packets_recv)
            self.assertEqual(nt[4], nt.errin)
            self.assertEqual(nt[5], nt.errout)
            self.assertEqual(nt[6], nt.dropin)
            self.assertEqual(nt[7], nt.dropout)
            assert nt.bytes_sent >= 0, nt
            assert nt.bytes_recv >= 0, nt
            assert nt.packets_sent >= 0, nt
            assert nt.packets_recv >= 0, nt
            assert nt.errin >= 0, nt
            assert nt.errout >= 0, nt
            assert nt.dropin >= 0, nt
            assert nt.dropout >= 0, nt

        ret = psutil.net_io_counters(pernic=False)
        check_ntuple(ret)
        ret = psutil.net_io_counters(pernic=True)
        self.assertNotEqual(ret, [])
        for key in ret:
            self.assertTrue(key)
            check_ntuple(ret[key])

    def test_net_if_addrs(self):
        nics = psutil.net_if_addrs()
        assert nics, nics

        # Not reliable on all platforms (net_if_addrs() reports more
        # interfaces).
        # self.assertEqual(sorted(nics.keys()),
        #                  sorted(psutil.net_io_counters(pernic=True).keys()))

        families = set([socket.AF_INET, AF_INET6, psutil.AF_LINK])
        for nic, addrs in nics.items():
            self.assertEqual(len(set(addrs)), len(addrs))
            for addr in addrs:
                self.assertIsInstance(addr.family, int)
                self.assertIsInstance(addr.address, str)
                self.assertIsInstance(addr.netmask, (str, type(None)))
                self.assertIsInstance(addr.broadcast, (str, type(None)))
                self.assertIn(addr.family, families)
                if sys.version_info >= (3, 4):
                    self.assertIsInstance(addr.family, enum.IntEnum)
                if addr.family == socket.AF_INET:
                    s = socket.socket(addr.family)
                    with contextlib.closing(s):
                        s.bind((addr.address, 0))
                elif addr.family == socket.AF_INET6:
                    info = socket.getaddrinfo(
                        addr.address, 0, socket.AF_INET6, socket.SOCK_STREAM,
                        0, socket.AI_PASSIVE)[0]
                    af, socktype, proto, canonname, sa = info
                    s = socket.socket(af, socktype, proto)
                    with contextlib.closing(s):
                        s.bind(sa)
                for ip in (addr.address, addr.netmask, addr.broadcast):
                    if ip is not None:
                        # TODO: skip AF_INET6 for now because I get:
                        # AddressValueError: Only hex digits permitted in
                        # u'c6f3%lxcbr0' in u'fe80::c8e0:fff:fe54:c6f3%lxcbr0'
                        if addr.family != AF_INET6:
                            check_ip_address(ip, addr.family)

        if BSD or OSX or SUNOS:
            if hasattr(socket, "AF_LINK"):
                self.assertEqual(psutil.AF_LINK, socket.AF_LINK)
        elif LINUX:
            self.assertEqual(psutil.AF_LINK, socket.AF_PACKET)
        elif WINDOWS:
            self.assertEqual(psutil.AF_LINK, -1)

    @unittest.skipIf(TRAVIS, "EPERM on travis")
    def test_net_if_stats(self):
        nics = psutil.net_if_stats()
        assert nics, nics
        all_duplexes = (psutil.NIC_DUPLEX_FULL,
                        psutil.NIC_DUPLEX_HALF,
                        psutil.NIC_DUPLEX_UNKNOWN)
        for nic, stats in nics.items():
            isup, duplex, speed, mtu = stats
            self.assertIsInstance(isup, bool)
            self.assertIn(duplex, all_duplexes)
            self.assertIn(duplex, all_duplexes)
            self.assertGreaterEqual(speed, 0)
            self.assertGreaterEqual(mtu, 0)

    @unittest.skipIf(LINUX and not os.path.exists('/proc/diskstats'),
                     '/proc/diskstats not available on this linux version')
    @unittest.skipIf(APPVEYOR,
                     "can't find any physical disk on Appveyor")
    def test_disk_io_counters(self):
        def check_ntuple(nt):
            self.assertEqual(nt[0], nt.read_count)
            self.assertEqual(nt[1], nt.write_count)
            self.assertEqual(nt[2], nt.read_bytes)
            self.assertEqual(nt[3], nt.write_bytes)
            self.assertEqual(nt[4], nt.read_time)
            self.assertEqual(nt[5], nt.write_time)
            assert nt.read_count >= 0, nt
            assert nt.write_count >= 0, nt
            assert nt.read_bytes >= 0, nt
            assert nt.write_bytes >= 0, nt
            assert nt.read_time >= 0, nt
            assert nt.write_time >= 0, nt

        ret = psutil.disk_io_counters(perdisk=False)
        check_ntuple(ret)
        ret = psutil.disk_io_counters(perdisk=True)
        # make sure there are no duplicates
        self.assertEqual(len(ret), len(set(ret)))
        for key in ret:
            assert key, key
            check_ntuple(ret[key])
            if LINUX and key[-1].isdigit():
                # if 'sda1' is listed 'sda' shouldn't, see:
                # https://github.com/giampaolo/psutil/issues/338
                while key[-1].isdigit():
                    key = key[:-1]
                self.assertNotIn(key, ret.keys())

    def test_users(self):
        users = psutil.users()
        if not APPVEYOR:
            self.assertNotEqual(users, [])
        for user in users:
            assert user.name, user
            user.terminal
            user.host
            assert user.started > 0.0, user
            datetime.datetime.fromtimestamp(user.started)


# ===================================================================
# --- psutil.Process class tests
# ===================================================================

class TestProcess(unittest.TestCase):
    """Tests for psutil.Process class."""

    def setUp(self):
        safe_remove(TESTFN)

    def tearDown(self):
        reap_children()

    def test_pid(self):
        self.assertEqual(psutil.Process().pid, os.getpid())
        sproc = get_test_subprocess()
        self.assertEqual(psutil.Process(sproc.pid).pid, sproc.pid)

    def test_kill(self):
        sproc = get_test_subprocess(wait=True)
        test_pid = sproc.pid
        p = psutil.Process(test_pid)
        p.kill()
        sig = p.wait()
        self.assertFalse(psutil.pid_exists(test_pid))
        if POSIX:
            self.assertEqual(sig, signal.SIGKILL)

    def test_terminate(self):
        sproc = get_test_subprocess(wait=True)
        test_pid = sproc.pid
        p = psutil.Process(test_pid)
        p.terminate()
        sig = p.wait()
        self.assertFalse(psutil.pid_exists(test_pid))
        if POSIX:
            self.assertEqual(sig, signal.SIGTERM)

    def test_send_signal(self):
        sig = signal.SIGKILL if POSIX else signal.SIGTERM
        sproc = get_test_subprocess()
        p = psutil.Process(sproc.pid)
        p.send_signal(sig)
        exit_sig = p.wait()
        self.assertFalse(psutil.pid_exists(p.pid))
        if POSIX:
            self.assertEqual(exit_sig, sig)
            #
            sproc = get_test_subprocess()
            p = psutil.Process(sproc.pid)
            p.send_signal(sig)
            with mock.patch('psutil.os.kill',
                            side_effect=OSError(errno.ESRCH, "")) as fun:
                with self.assertRaises(psutil.NoSuchProcess):
                    p.send_signal(sig)
                assert fun.called
            #
            sproc = get_test_subprocess()
            p = psutil.Process(sproc.pid)
            p.send_signal(sig)
            with mock.patch('psutil.os.kill',
                            side_effect=OSError(errno.EPERM, "")) as fun:
                with self.assertRaises(psutil.AccessDenied):
                    p.send_signal(sig)
                assert fun.called

    def test_wait(self):
        # check exit code signal
        sproc = get_test_subprocess()
        p = psutil.Process(sproc.pid)
        p.kill()
        code = p.wait()
        if POSIX:
            self.assertEqual(code, signal.SIGKILL)
        else:
            self.assertEqual(code, 0)
        self.assertFalse(p.is_running())

        sproc = get_test_subprocess()
        p = psutil.Process(sproc.pid)
        p.terminate()
        code = p.wait()
        if POSIX:
            self.assertEqual(code, signal.SIGTERM)
        else:
            self.assertEqual(code, 0)
        self.assertFalse(p.is_running())

        # check sys.exit() code
        code = "import time, sys; time.sleep(0.01); sys.exit(5);"
        sproc = get_test_subprocess([PYTHON, "-c", code])
        p = psutil.Process(sproc.pid)
        self.assertEqual(p.wait(), 5)
        self.assertFalse(p.is_running())

        # Test wait() issued twice.
        # It is not supposed to raise NSP when the process is gone.
        # On UNIX this should return None, on Windows it should keep
        # returning the exit code.
        sproc = get_test_subprocess([PYTHON, "-c", code])
        p = psutil.Process(sproc.pid)
        self.assertEqual(p.wait(), 5)
        self.assertIn(p.wait(), (5, None))

        # test timeout
        sproc = get_test_subprocess()
        p = psutil.Process(sproc.pid)
        p.name()
        self.assertRaises(psutil.TimeoutExpired, p.wait, 0.01)

        # timeout < 0 not allowed
        self.assertRaises(ValueError, p.wait, -1)

    # XXX why is this skipped on Windows?
    @unittest.skipUnless(POSIX, 'skipped on Windows')
    def test_wait_non_children(self):
        # test wait() against processes which are not our children
        code = "import sys;"
        code += "from subprocess import Popen, PIPE;"
        code += "cmd = ['%s', '-c', 'import time; time.sleep(60)'];" % PYTHON
        code += "sp = Popen(cmd, stdout=PIPE);"
        code += "sys.stdout.write(str(sp.pid));"
        sproc = get_test_subprocess([PYTHON, "-c", code],
                                    stdout=subprocess.PIPE)
        grandson_pid = int(sproc.stdout.read())
        grandson_proc = psutil.Process(grandson_pid)
        try:
            self.assertRaises(psutil.TimeoutExpired, grandson_proc.wait, 0.01)
            grandson_proc.kill()
            ret = grandson_proc.wait()
            self.assertEqual(ret, None)
        finally:
            if grandson_proc.is_running():
                grandson_proc.kill()
                grandson_proc.wait()

    def test_wait_timeout_0(self):
        sproc = get_test_subprocess()
        p = psutil.Process(sproc.pid)
        self.assertRaises(psutil.TimeoutExpired, p.wait, 0)
        p.kill()
        stop_at = time.time() + 2
        while True:
            try:
                code = p.wait(0)
            except psutil.TimeoutExpired:
                if time.time() >= stop_at:
                    raise
            else:
                break
        if POSIX:
            self.assertEqual(code, signal.SIGKILL)
        else:
            self.assertEqual(code, 0)
        self.assertFalse(p.is_running())

    def test_cpu_percent(self):
        p = psutil.Process()
        p.cpu_percent(interval=0.001)
        p.cpu_percent(interval=0.001)
        for x in range(100):
            percent = p.cpu_percent(interval=None)
            self.assertIsInstance(percent, float)
            self.assertGreaterEqual(percent, 0.0)
            if not POSIX:
                self.assertLessEqual(percent, 100.0)
            else:
                self.assertGreaterEqual(percent, 0.0)

    def test_cpu_times(self):
        times = psutil.Process().cpu_times()
        assert (times.user > 0.0) or (times.system > 0.0), times
        # make sure returned values can be pretty printed with strftime
        time.strftime("%H:%M:%S", time.localtime(times.user))
        time.strftime("%H:%M:%S", time.localtime(times.system))

    # Test Process.cpu_times() against os.times()
    # os.times() is broken on Python 2.6
    # http://bugs.python.org/issue1040026
    # XXX fails on OSX: not sure if it's for os.times(). We should
    # try this with Python 2.7 and re-enable the test.

    @unittest.skipUnless(sys.version_info > (2, 6, 1) and not OSX,
                         'os.times() is not reliable on this Python version')
    def test_cpu_times2(self):
        user_time, kernel_time = psutil.Process().cpu_times()
        utime, ktime = os.times()[:2]

        # Use os.times()[:2] as base values to compare our results
        # using a tolerance  of +/- 0.1 seconds.
        # It will fail if the difference between the values is > 0.1s.
        if (max([user_time, utime]) - min([user_time, utime])) > 0.1:
            self.fail("expected: %s, found: %s" % (utime, user_time))

        if (max([kernel_time, ktime]) - min([kernel_time, ktime])) > 0.1:
            self.fail("expected: %s, found: %s" % (ktime, kernel_time))

    def test_create_time(self):
        sproc = get_test_subprocess(wait=True)
        now = time.time()
        p = psutil.Process(sproc.pid)
        create_time = p.create_time()

        # Use time.time() as base value to compare our result using a
        # tolerance of +/- 1 second.
        # It will fail if the difference between the values is > 2s.
        difference = abs(create_time - now)
        if difference > 2:
            self.fail("expected: %s, found: %s, difference: %s"
                      % (now, create_time, difference))

        # make sure returned value can be pretty printed with strftime
        time.strftime("%Y %m %d %H:%M:%S", time.localtime(p.create_time()))

    @unittest.skipIf(WINDOWS, 'Windows only')
    def test_terminal(self):
        terminal = psutil.Process().terminal()
        if sys.stdin.isatty():
            self.assertEqual(terminal, sh('tty'))
        else:
            assert terminal, repr(terminal)

    @unittest.skipUnless(LINUX or BSD or WINDOWS,
                         'not available on this platform')
    @skip_on_not_implemented(only_if=LINUX)
    def test_io_counters(self):
        p = psutil.Process()
        # test reads
        io1 = p.io_counters()
        with open(PYTHON, 'rb') as f:
            f.read()
        io2 = p.io_counters()
        if not BSD:
            assert io2.read_count > io1.read_count, (io1, io2)
            self.assertEqual(io2.write_count, io1.write_count)
        assert io2.read_bytes >= io1.read_bytes, (io1, io2)
        assert io2.write_bytes >= io1.write_bytes, (io1, io2)
        # test writes
        io1 = p.io_counters()
        with tempfile.TemporaryFile(prefix=TESTFILE_PREFIX) as f:
            if PY3:
                f.write(bytes("x" * 1000000, 'ascii'))
            else:
                f.write("x" * 1000000)
        io2 = p.io_counters()
        assert io2.write_count >= io1.write_count, (io1, io2)
        assert io2.write_bytes >= io1.write_bytes, (io1, io2)
        assert io2.read_count >= io1.read_count, (io1, io2)
        assert io2.read_bytes >= io1.read_bytes, (io1, io2)

    @unittest.skipUnless(LINUX or (WINDOWS and get_winver() >= WIN_VISTA),
                         'Linux and Windows Vista only')
    @unittest.skipIf(LINUX and TRAVIS, "unknown failure on travis")
    def test_ionice(self):
        if LINUX:
            from psutil import (IOPRIO_CLASS_NONE, IOPRIO_CLASS_RT,
                                IOPRIO_CLASS_BE, IOPRIO_CLASS_IDLE)
            self.assertEqual(IOPRIO_CLASS_NONE, 0)
            self.assertEqual(IOPRIO_CLASS_RT, 1)
            self.assertEqual(IOPRIO_CLASS_BE, 2)
            self.assertEqual(IOPRIO_CLASS_IDLE, 3)
            p = psutil.Process()
            try:
                p.ionice(2)
                ioclass, value = p.ionice()
                if enum is not None:
                    self.assertIsInstance(ioclass, enum.IntEnum)
                self.assertEqual(ioclass, 2)
                self.assertEqual(value, 4)
                #
                p.ionice(3)
                ioclass, value = p.ionice()
                self.assertEqual(ioclass, 3)
                self.assertEqual(value, 0)
                #
                p.ionice(2, 0)
                ioclass, value = p.ionice()
                self.assertEqual(ioclass, 2)
                self.assertEqual(value, 0)
                p.ionice(2, 7)
                ioclass, value = p.ionice()
                self.assertEqual(ioclass, 2)
                self.assertEqual(value, 7)
                #
                self.assertRaises(ValueError, p.ionice, 2, 10)
                self.assertRaises(ValueError, p.ionice, 2, -1)
                self.assertRaises(ValueError, p.ionice, 4)
                self.assertRaises(TypeError, p.ionice, 2, "foo")
                self.assertRaisesRegexp(
                    ValueError, "can't specify value with IOPRIO_CLASS_NONE",
                    p.ionice, psutil.IOPRIO_CLASS_NONE, 1)
                self.assertRaisesRegexp(
                    ValueError, "can't specify value with IOPRIO_CLASS_IDLE",
                    p.ionice, psutil.IOPRIO_CLASS_IDLE, 1)
                self.assertRaisesRegexp(
                    ValueError, "'ioclass' argument must be specified",
                    p.ionice, value=1)
            finally:
                p.ionice(IOPRIO_CLASS_NONE)
        else:
            p = psutil.Process()
            original = p.ionice()
            self.assertIsInstance(original, int)
            try:
                value = 0  # very low
                if original == value:
                    value = 1  # low
                p.ionice(value)
                self.assertEqual(p.ionice(), value)
            finally:
                p.ionice(original)
            #
            self.assertRaises(ValueError, p.ionice, 3)
            self.assertRaises(TypeError, p.ionice, 2, 1)

    @unittest.skipUnless(LINUX and RLIMIT_SUPPORT,
                         "only available on Linux >= 2.6.36")
    def test_rlimit_get(self):
        import resource
        p = psutil.Process(os.getpid())
        names = [x for x in dir(psutil) if x.startswith('RLIMIT')]
        assert names, names
        for name in names:
            value = getattr(psutil, name)
            self.assertGreaterEqual(value, 0)
            if name in dir(resource):
                self.assertEqual(value, getattr(resource, name))
                self.assertEqual(p.rlimit(value), resource.getrlimit(value))
            else:
                ret = p.rlimit(value)
                self.assertEqual(len(ret), 2)
                self.assertGreaterEqual(ret[0], -1)
                self.assertGreaterEqual(ret[1], -1)

    @unittest.skipUnless(LINUX and RLIMIT_SUPPORT,
                         "only available on Linux >= 2.6.36")
    def test_rlimit_set(self):
        sproc = get_test_subprocess()
        p = psutil.Process(sproc.pid)
        p.rlimit(psutil.RLIMIT_NOFILE, (5, 5))
        self.assertEqual(p.rlimit(psutil.RLIMIT_NOFILE), (5, 5))
        # If pid is 0 prlimit() applies to the calling process and
        # we don't want that.
        with self.assertRaises(ValueError):
            psutil._psplatform.Process(0).rlimit(0)
        with self.assertRaises(ValueError):
            p.rlimit(psutil.RLIMIT_NOFILE, (5, 5, 5))

    def test_num_threads(self):
        # on certain platforms such as Linux we might test for exact
        # thread number, since we always have with 1 thread per process,
        # but this does not apply across all platforms (OSX, Windows)
        p = psutil.Process()
        step1 = p.num_threads()

        thread = ThreadTask()
        thread.start()
        try:
            step2 = p.num_threads()
            self.assertEqual(step2, step1 + 1)
            thread.stop()
        finally:
            if thread._running:
                thread.stop()

    @unittest.skipUnless(WINDOWS, 'Windows only')
    def test_num_handles(self):
        # a better test is done later into test/_windows.py
        p = psutil.Process()
        self.assertGreater(p.num_handles(), 0)

    def test_threads(self):
        p = psutil.Process()
        step1 = p.threads()

        thread = ThreadTask()
        thread.start()

        try:
            step2 = p.threads()
            self.assertEqual(len(step2), len(step1) + 1)
            # on Linux, first thread id is supposed to be this process
            if LINUX:
                self.assertEqual(step2[0].id, os.getpid())
            athread = step2[0]
            # test named tuple
            self.assertEqual(athread.id, athread[0])
            self.assertEqual(athread.user_time, athread[1])
            self.assertEqual(athread.system_time, athread[2])
            # test num threads
            thread.stop()
        finally:
            if thread._running:
                thread.stop()

    def test_memory_info(self):
        p = psutil.Process()

        # step 1 - get a base value to compare our results
        rss1, vms1 = p.memory_info()
        percent1 = p.memory_percent()
        self.assertGreater(rss1, 0)
        self.assertGreater(vms1, 0)

        # step 2 - allocate some memory
        memarr = [None] * 1500000

        rss2, vms2 = p.memory_info()
        percent2 = p.memory_percent()
        # make sure that the memory usage bumped up
        self.assertGreater(rss2, rss1)
        self.assertGreaterEqual(vms2, vms1)  # vms might be equal
        self.assertGreater(percent2, percent1)
        del memarr

    # def test_memory_info_ex(self):
    # # tested later in fetch all test suite

    def test_memory_maps(self):
        p = psutil.Process()
        maps = p.memory_maps()
        paths = [x for x in maps]
        self.assertEqual(len(paths), len(set(paths)))
        ext_maps = p.memory_maps(grouped=False)

        for nt in maps:
            if not nt.path.startswith('['):
                assert os.path.isabs(nt.path), nt.path
                if POSIX:
                    assert os.path.exists(nt.path), nt.path
                else:
                    # XXX - On Windows we have this strange behavior with
                    # 64 bit dlls: they are visible via explorer but cannot
                    # be accessed via os.stat() (wtf?).
                    if '64' not in os.path.basename(nt.path):
                        assert os.path.exists(nt.path), nt.path
        for nt in ext_maps:
            for fname in nt._fields:
                value = getattr(nt, fname)
                if fname == 'path':
                    continue
                elif fname in ('addr', 'perms'):
                    assert value, value
                else:
                    self.assertIsInstance(value, (int, long))
                    assert value >= 0, value

    def test_memory_percent(self):
        p = psutil.Process()
        self.assertGreater(p.memory_percent(), 0.0)

    def test_is_running(self):
        sproc = get_test_subprocess(wait=True)
        p = psutil.Process(sproc.pid)
        assert p.is_running()
        assert p.is_running()
        p.kill()
        p.wait()
        assert not p.is_running()
        assert not p.is_running()

    def test_exe(self):
        sproc = get_test_subprocess(wait=True)
        exe = psutil.Process(sproc.pid).exe()
        try:
            self.assertEqual(exe, PYTHON)
        except AssertionError:
            if WINDOWS and len(exe) == len(PYTHON):
                # on Windows we don't care about case sensitivity
                self.assertEqual(exe.lower(), PYTHON.lower())
            else:
                # certain platforms such as BSD are more accurate returning:
                # "/usr/local/bin/python2.7"
                # ...instead of:
                # "/usr/local/bin/python"
                # We do not want to consider this difference in accuracy
                # an error.
                ver = "%s.%s" % (sys.version_info[0], sys.version_info[1])
                self.assertEqual(exe.replace(ver, ''), PYTHON.replace(ver, ''))

    def test_cmdline(self):
        cmdline = [PYTHON, "-c", "import time; time.sleep(60)"]
        sproc = get_test_subprocess(cmdline, wait=True)
        self.assertEqual(' '.join(psutil.Process(sproc.pid).cmdline()),
                         ' '.join(cmdline))

    def test_name(self):
        sproc = get_test_subprocess(PYTHON, wait=True)
        name = psutil.Process(sproc.pid).name().lower()
        pyexe = os.path.basename(os.path.realpath(sys.executable)).lower()
        assert pyexe.startswith(name), (pyexe, name)

    @unittest.skipUnless(POSIX, "posix only")
    # TODO: add support for other compilers
    @unittest.skipUnless(which("gcc"), "gcc not available")
    def test_prog_w_funky_name(self):
        # Test that name(), exe() and cmdline() correctly handle programs
        # with funky chars such as spaces and ")", see:
        # https://github.com/giampaolo/psutil/issues/628
        funky_name = "/tmp/foo bar )"
        _, c_file = tempfile.mkstemp(prefix='psutil-', suffix='.c', dir="/tmp")
        self.addCleanup(lambda: safe_remove(c_file))
        self.addCleanup(lambda: safe_remove(funky_name))
        with open(c_file, "w") as f:
            f.write("void main() { pause(); }")
        subprocess.check_call(["gcc", c_file, "-o", funky_name])
        sproc = get_test_subprocess(
            [funky_name, "arg1", "arg2", "", "arg3", ""])
        p = psutil.Process(sproc.pid)
        # ...in order to try to prevent occasional failures on travis
        wait_for_pid(p.pid)
        self.assertEqual(p.name(), "foo bar )")
        self.assertEqual(p.exe(), "/tmp/foo bar )")
        self.assertEqual(
            p.cmdline(), ["/tmp/foo bar )", "arg1", "arg2", "", "arg3", ""])

    @unittest.skipUnless(POSIX, 'posix only')
    def test_uids(self):
        p = psutil.Process()
        real, effective, saved = p.uids()
        # os.getuid() refers to "real" uid
        self.assertEqual(real, os.getuid())
        # os.geteuid() refers to "effective" uid
        self.assertEqual(effective, os.geteuid())
        # no such thing as os.getsuid() ("saved" uid), but starting
        # from python 2.7 we have os.getresuid()[2]
        if hasattr(os, "getresuid"):
            self.assertEqual(saved, os.getresuid()[2])

    @unittest.skipUnless(POSIX, 'posix only')
    def test_gids(self):
        p = psutil.Process()
        real, effective, saved = p.gids()
        # os.getuid() refers to "real" uid
        self.assertEqual(real, os.getgid())
        # os.geteuid() refers to "effective" uid
        self.assertEqual(effective, os.getegid())
        # no such thing as os.getsuid() ("saved" uid), but starting
        # from python 2.7 we have os.getresgid()[2]
        if hasattr(os, "getresuid"):
            self.assertEqual(saved, os.getresgid()[2])

    def test_nice(self):
        p = psutil.Process()
        self.assertRaises(TypeError, p.nice, "str")
        if WINDOWS:
            try:
                init = p.nice()
                if sys.version_info > (3, 4):
                    self.assertIsInstance(init, enum.IntEnum)
                else:
                    self.assertIsInstance(init, int)
                self.assertEqual(init, psutil.NORMAL_PRIORITY_CLASS)
                p.nice(psutil.HIGH_PRIORITY_CLASS)
                self.assertEqual(p.nice(), psutil.HIGH_PRIORITY_CLASS)
                p.nice(psutil.NORMAL_PRIORITY_CLASS)
                self.assertEqual(p.nice(), psutil.NORMAL_PRIORITY_CLASS)
            finally:
                p.nice(psutil.NORMAL_PRIORITY_CLASS)
        else:
            try:
                first_nice = p.nice()
                p.nice(1)
                self.assertEqual(p.nice(), 1)
                # going back to previous nice value raises
                # AccessDenied on OSX
                if not OSX:
                    p.nice(0)
                    self.assertEqual(p.nice(), 0)
            except psutil.AccessDenied:
                pass
            finally:
                try:
                    p.nice(first_nice)
                except psutil.AccessDenied:
                    pass

    def test_status(self):
        p = psutil.Process()
        self.assertEqual(p.status(), psutil.STATUS_RUNNING)

    def test_username(self):
        sproc = get_test_subprocess()
        p = psutil.Process(sproc.pid)
        if POSIX:
            import pwd
            self.assertEqual(p.username(), pwd.getpwuid(os.getuid()).pw_name)
            with mock.patch("psutil.pwd.getpwuid",
                            side_effect=KeyError) as fun:
                p.username() == str(p.uids().real)
                assert fun.called

        elif WINDOWS and 'USERNAME' in os.environ:
            expected_username = os.environ['USERNAME']
            expected_domain = os.environ['USERDOMAIN']
            domain, username = p.username().split('\\')
            self.assertEqual(domain, expected_domain)
            self.assertEqual(username, expected_username)
        else:
            p.username()

    def test_cwd(self):
        sproc = get_test_subprocess(wait=True)
        p = psutil.Process(sproc.pid)
        self.assertEqual(p.cwd(), os.getcwd())

    def test_cwd_2(self):
        cmd = [PYTHON, "-c", "import os, time; os.chdir('..'); time.sleep(60)"]
        sproc = get_test_subprocess(cmd, wait=True)
        p = psutil.Process(sproc.pid)
        call_until(p.cwd, "ret == os.path.dirname(os.getcwd())")

    @unittest.skipUnless(WINDOWS or LINUX or BSD,
                         'not available on this platform')
    @unittest.skipIf(LINUX and TRAVIS, "unknown failure on travis")
    def test_cpu_affinity(self):
        p = psutil.Process()
        initial = p.cpu_affinity()
        if hasattr(os, "sched_getaffinity"):
            self.assertEqual(initial, list(os.sched_getaffinity(p.pid)))
        self.assertEqual(len(initial), len(set(initial)))
        all_cpus = list(range(len(psutil.cpu_percent(percpu=True))))
        # setting on travis doesn't seem to work (always return all
        # CPUs on get):
        # AssertionError: Lists differ: [0, 1, 2, 3, 4, 5, 6, ... != [0]
        for n in all_cpus:
            p.cpu_affinity([n])
            self.assertEqual(p.cpu_affinity(), [n])
            if hasattr(os, "sched_getaffinity"):
                self.assertEqual(p.cpu_affinity(),
                                 list(os.sched_getaffinity(p.pid)))
        #
        p.cpu_affinity(all_cpus)
        self.assertEqual(p.cpu_affinity(), all_cpus)
        if hasattr(os, "sched_getaffinity"):
            self.assertEqual(p.cpu_affinity(),
                             list(os.sched_getaffinity(p.pid)))
        #
        self.assertRaises(TypeError, p.cpu_affinity, 1)
        p.cpu_affinity(initial)
        # it should work with all iterables, not only lists
        p.cpu_affinity(set(all_cpus))
        p.cpu_affinity(tuple(all_cpus))
        invalid_cpu = [len(psutil.cpu_times(percpu=True)) + 10]
        self.assertRaises(ValueError, p.cpu_affinity, invalid_cpu)
        self.assertRaises(ValueError, p.cpu_affinity, range(10000, 11000))
        self.assertRaises(TypeError, p.cpu_affinity, [0, "1"])

    # TODO
    @unittest.skipIf(BSD, "broken on BSD, see #595")
    @unittest.skipIf(APPVEYOR,
                     "can't find any process file on Appveyor")
    def test_open_files(self):
        # current process
        p = psutil.Process()
        files = p.open_files()
        self.assertFalse(TESTFN in files)
        with open(TESTFN, 'w'):
            # give the kernel some time to see the new file
            call_until(p.open_files, "len(ret) != %i" % len(files))
            filenames = [x.path for x in p.open_files()]
            self.assertIn(TESTFN, filenames)
        for file in filenames:
            assert os.path.isfile(file), file

        # another process
        cmdline = "import time; f = open(r'%s', 'r'); time.sleep(60);" % TESTFN
        sproc = get_test_subprocess([PYTHON, "-c", cmdline], wait=True)
        p = psutil.Process(sproc.pid)

        for x in range(100):
            filenames = [x.path for x in p.open_files()]
            if TESTFN in filenames:
                break
            time.sleep(.01)
        else:
            self.assertIn(TESTFN, filenames)
        for file in filenames:
            assert os.path.isfile(file), file

    # TODO
    @unittest.skipIf(BSD, "broken on BSD, see #595")
    @unittest.skipIf(APPVEYOR,
                     "can't find any process file on Appveyor")
    def test_open_files2(self):
        # test fd and path fields
        with open(TESTFN, 'w') as fileobj:
            p = psutil.Process()
            for path, fd in p.open_files():
                if path == fileobj.name or fd == fileobj.fileno():
                    break
            else:
                self.fail("no file found; files=%s" % repr(p.open_files()))
            self.assertEqual(path, fileobj.name)
            if WINDOWS:
                self.assertEqual(fd, -1)
            else:
                self.assertEqual(fd, fileobj.fileno())
            # test positions
            ntuple = p.open_files()[0]
            self.assertEqual(ntuple[0], ntuple.path)
            self.assertEqual(ntuple[1], ntuple.fd)
            # test file is gone
            self.assertTrue(fileobj.name not in p.open_files())

    def compare_proc_sys_cons(self, pid, proc_cons):
        from psutil._common import pconn
        sys_cons = []
        for c in psutil.net_connections(kind='all'):
            if c.pid == pid:
                sys_cons.append(pconn(*c[:-1]))
        if BSD:
            # on BSD all fds are set to -1
            proc_cons = [pconn(*[-1] + list(x[1:])) for x in proc_cons]
        self.assertEqual(sorted(proc_cons), sorted(sys_cons))

    @skip_on_access_denied(only_if=OSX)
    def test_connections(self):
        def check_conn(proc, conn, family, type, laddr, raddr, status, kinds):
            all_kinds = ("all", "inet", "inet4", "inet6", "tcp", "tcp4",
                         "tcp6", "udp", "udp4", "udp6")
            check_connection_ntuple(conn)
            self.assertEqual(conn.family, family)
            self.assertEqual(conn.type, type)
            self.assertEqual(conn.laddr, laddr)
            self.assertEqual(conn.raddr, raddr)
            self.assertEqual(conn.status, status)
            for kind in all_kinds:
                cons = proc.connections(kind=kind)
                if kind in kinds:
                    self.assertNotEqual(cons, [])
                else:
                    self.assertEqual(cons, [])
            # compare against system-wide connections
            # XXX Solaris can't retrieve system-wide UNIX
            # sockets.
            if not SUNOS:
                self.compare_proc_sys_cons(proc.pid, [conn])

        tcp_template = textwrap.dedent("""
            import socket, time
            s = socket.socket($family, socket.SOCK_STREAM)
            s.bind(('$addr', 0))
            s.listen(1)
            with open('$testfn', 'w') as f:
                f.write(str(s.getsockname()[:2]))
            time.sleep(60)
        """)

        udp_template = textwrap.dedent("""
            import socket, time
            s = socket.socket($family, socket.SOCK_DGRAM)
            s.bind(('$addr', 0))
            with open('$testfn', 'w') as f:
                f.write(str(s.getsockname()[:2]))
            time.sleep(60)
        """)

        from string import Template
        testfile = os.path.basename(TESTFN)
        tcp4_template = Template(tcp_template).substitute(
            family=int(AF_INET), addr="127.0.0.1", testfn=testfile)
        udp4_template = Template(udp_template).substitute(
            family=int(AF_INET), addr="127.0.0.1", testfn=testfile)
        tcp6_template = Template(tcp_template).substitute(
            family=int(AF_INET6), addr="::1", testfn=testfile)
        udp6_template = Template(udp_template).substitute(
            family=int(AF_INET6), addr="::1", testfn=testfile)

        # launch various subprocess instantiating a socket of various
        # families and types to enrich psutil results
        tcp4_proc = pyrun(tcp4_template)
        tcp4_addr = eval(wait_for_file(testfile))
        udp4_proc = pyrun(udp4_template)
        udp4_addr = eval(wait_for_file(testfile))
        if supports_ipv6():
            tcp6_proc = pyrun(tcp6_template)
            tcp6_addr = eval(wait_for_file(testfile))
            udp6_proc = pyrun(udp6_template)
            udp6_addr = eval(wait_for_file(testfile))
        else:
            tcp6_proc = None
            udp6_proc = None
            tcp6_addr = None
            udp6_addr = None

        for p in psutil.Process().children():
            cons = p.connections()
            self.assertEqual(len(cons), 1)
            for conn in cons:
                # TCP v4
                if p.pid == tcp4_proc.pid:
                    check_conn(p, conn, AF_INET, SOCK_STREAM, tcp4_addr, (),
                               psutil.CONN_LISTEN,
                               ("all", "inet", "inet4", "tcp", "tcp4"))
                # UDP v4
                elif p.pid == udp4_proc.pid:
                    check_conn(p, conn, AF_INET, SOCK_DGRAM, udp4_addr, (),
                               psutil.CONN_NONE,
                               ("all", "inet", "inet4", "udp", "udp4"))
                # TCP v6
                elif p.pid == getattr(tcp6_proc, "pid", None):
                    check_conn(p, conn, AF_INET6, SOCK_STREAM, tcp6_addr, (),
                               psutil.CONN_LISTEN,
                               ("all", "inet", "inet6", "tcp", "tcp6"))
                # UDP v6
                elif p.pid == getattr(udp6_proc, "pid", None):
                    check_conn(p, conn, AF_INET6, SOCK_DGRAM, udp6_addr, (),
                               psutil.CONN_NONE,
                               ("all", "inet", "inet6", "udp", "udp6"))

    @unittest.skipUnless(hasattr(socket, 'AF_UNIX'),
                         'AF_UNIX is not supported')
    @skip_on_access_denied(only_if=OSX)
    def test_connections_unix(self):
        def check(type):
            safe_remove(TESTFN)
            sock = socket.socket(AF_UNIX, type)
            with contextlib.closing(sock):
                sock.bind(TESTFN)
                cons = psutil.Process().connections(kind='unix')
                conn = cons[0]
                check_connection_ntuple(conn)
                if conn.fd != -1:  # != sunos and windows
                    self.assertEqual(conn.fd, sock.fileno())
                self.assertEqual(conn.family, AF_UNIX)
                self.assertEqual(conn.type, type)
                self.assertEqual(conn.laddr, TESTFN)
                if not SUNOS:
                    # XXX Solaris can't retrieve system-wide UNIX
                    # sockets.
                    self.compare_proc_sys_cons(os.getpid(), cons)

        check(SOCK_STREAM)
        check(SOCK_DGRAM)

    @unittest.skipUnless(hasattr(socket, "fromfd"),
                         'socket.fromfd() is not availble')
    @unittest.skipIf(WINDOWS or SUNOS,
                     'connection fd not available on this platform')
    def test_connection_fromfd(self):
        with contextlib.closing(socket.socket()) as sock:
            sock.bind(('localhost', 0))
            sock.listen(1)
            p = psutil.Process()
            for conn in p.connections():
                if conn.fd == sock.fileno():
                    break
            else:
                self.fail("couldn't find socket fd")
            dupsock = socket.fromfd(conn.fd, conn.family, conn.type)
            with contextlib.closing(dupsock):
                self.assertEqual(dupsock.getsockname(), conn.laddr)
                self.assertNotEqual(sock.fileno(), dupsock.fileno())

    def test_connection_constants(self):
        ints = []
        strs = []
        for name in dir(psutil):
            if name.startswith('CONN_'):
                num = getattr(psutil, name)
                str_ = str(num)
                assert str_.isupper(), str_
                assert str_ not in strs, str_
                assert num not in ints, num
                ints.append(num)
                strs.append(str_)
        if SUNOS:
            psutil.CONN_IDLE
            psutil.CONN_BOUND
        if WINDOWS:
            psutil.CONN_DELETE_TCB

    @unittest.skipUnless(POSIX, 'posix only')
    def test_num_fds(self):
        p = psutil.Process()
        start = p.num_fds()
        file = open(TESTFN, 'w')
        self.addCleanup(file.close)
        self.assertEqual(p.num_fds(), start + 1)
        sock = socket.socket()
        self.addCleanup(sock.close)
        self.assertEqual(p.num_fds(), start + 2)
        file.close()
        sock.close()
        self.assertEqual(p.num_fds(), start)

    @skip_on_not_implemented(only_if=LINUX)
    def test_num_ctx_switches(self):
        p = psutil.Process()
        before = sum(p.num_ctx_switches())
        for x in range(500000):
            after = sum(p.num_ctx_switches())
            if after > before:
                return
        self.fail("num ctx switches still the same after 50.000 iterations")

    def test_parent_ppid(self):
        this_parent = os.getpid()
        sproc = get_test_subprocess()
        p = psutil.Process(sproc.pid)
        self.assertEqual(p.ppid(), this_parent)
        self.assertEqual(p.parent().pid, this_parent)
        # no other process is supposed to have us as parent
        for p in psutil.process_iter():
            if p.pid == sproc.pid:
                continue
            self.assertTrue(p.ppid() != this_parent)

    def test_children(self):
        p = psutil.Process()
        self.assertEqual(p.children(), [])
        self.assertEqual(p.children(recursive=True), [])
        sproc = get_test_subprocess()
        children1 = p.children()
        children2 = p.children(recursive=True)
        for children in (children1, children2):
            self.assertEqual(len(children), 1)
            self.assertEqual(children[0].pid, sproc.pid)
            self.assertEqual(children[0].ppid(), os.getpid())

    def test_children_recursive(self):
        # here we create a subprocess which creates another one as in:
        # A (parent) -> B (child) -> C (grandchild)
        s = "import subprocess, os, sys, time;"
        s += "PYTHON = os.path.realpath(sys.executable);"
        s += "cmd = [PYTHON, '-c', 'import time; time.sleep(60);'];"
        s += "subprocess.Popen(cmd);"
        s += "time.sleep(60);"
        get_test_subprocess(cmd=[PYTHON, "-c", s])
        p = psutil.Process()
        self.assertEqual(len(p.children(recursive=False)), 1)
        # give the grandchild some time to start
        stop_at = time.time() + GLOBAL_TIMEOUT
        while time.time() < stop_at:
            children = p.children(recursive=True)
            if len(children) > 1:
                break
        self.assertEqual(len(children), 2)
        self.assertEqual(children[0].ppid(), os.getpid())
        self.assertEqual(children[1].ppid(), children[0].pid)

    def test_children_duplicates(self):
        # find the process which has the highest number of children
        table = collections.defaultdict(int)
        for p in psutil.process_iter():
            try:
                table[p.ppid()] += 1
            except psutil.Error:
                pass
        # this is the one, now let's make sure there are no duplicates
        pid = sorted(table.items(), key=lambda x: x[1])[-1][0]
        p = psutil.Process(pid)
        try:
            c = p.children(recursive=True)
        except psutil.AccessDenied:  # windows
            pass
        else:
            self.assertEqual(len(c), len(set(c)))

    def test_suspend_resume(self):
        sproc = get_test_subprocess(wait=True)
        p = psutil.Process(sproc.pid)
        p.suspend()
        for x in range(100):
            if p.status() == psutil.STATUS_STOPPED:
                break
            time.sleep(0.01)
        p.resume()
        self.assertNotEqual(p.status(), psutil.STATUS_STOPPED)

    def test_invalid_pid(self):
        self.assertRaises(TypeError, psutil.Process, "1")
        self.assertRaises(ValueError, psutil.Process, -1)

    def test_as_dict(self):
        p = psutil.Process()
        d = p.as_dict(attrs=['exe', 'name'])
        self.assertEqual(sorted(d.keys()), ['exe', 'name'])

        p = psutil.Process(min(psutil.pids()))
        d = p.as_dict(attrs=['connections'], ad_value='foo')
        if not isinstance(d['connections'], list):
            self.assertEqual(d['connections'], 'foo')

    def test_halfway_terminated_process(self):
        # Test that NoSuchProcess exception gets raised in case the
        # process dies after we create the Process object.
        # Example:
        #  >>> proc = Process(1234)
        # >>> time.sleep(2)  # time-consuming task, process dies in meantime
        #  >>> proc.name()
        # Refers to Issue #15
        sproc = get_test_subprocess()
        p = psutil.Process(sproc.pid)
        p.terminate()
        p.wait()
        if WINDOWS:
            wait_for_pid(p.pid)
        self.assertFalse(p.is_running())
        self.assertFalse(p.pid in psutil.pids())

        excluded_names = ['pid', 'is_running', 'wait', 'create_time']
        if LINUX and not RLIMIT_SUPPORT:
            excluded_names.append('rlimit')
        for name in dir(p):
            if (name.startswith('_') or
                    name in excluded_names):
                continue
            try:
                meth = getattr(p, name)
                # get/set methods
                if name == 'nice':
                    if POSIX:
                        ret = meth(1)
                    else:
                        ret = meth(psutil.NORMAL_PRIORITY_CLASS)
                elif name == 'ionice':
                    ret = meth()
                    ret = meth(2)
                elif name == 'rlimit':
                    ret = meth(psutil.RLIMIT_NOFILE)
                    ret = meth(psutil.RLIMIT_NOFILE, (5, 5))
                elif name == 'cpu_affinity':
                    ret = meth()
                    ret = meth([0])
                elif name == 'send_signal':
                    ret = meth(signal.SIGTERM)
                else:
                    ret = meth()
            except psutil.ZombieProcess:
                self.fail("ZombieProcess for %r was not supposed to happen" %
                          name)
            except psutil.NoSuchProcess:
                pass
            except NotImplementedError:
                pass
            else:
                self.fail(
                    "NoSuchProcess exception not raised for %r, retval=%s" % (
                        name, ret))

    @unittest.skipUnless(POSIX, 'posix only')
    def test_zombie_process(self):
        def succeed_or_zombie_p_exc(fun, *args, **kwargs):
            try:
                fun(*args, **kwargs)
            except (psutil.ZombieProcess, psutil.AccessDenied):
                pass

        # Note: in this test we'll be creating two sub processes.
        # Both of them are supposed to be freed / killed by
        # reap_children() as they are attributable to 'us'
        # (os.getpid()) via children(recursive=True).
        src = textwrap.dedent("""\
        import os, sys, time, socket, contextlib
        child_pid = os.fork()
        if child_pid > 0:
            time.sleep(3000)
        else:
            # this is the zombie process
            s = socket.socket(socket.AF_UNIX)
            with contextlib.closing(s):
                s.connect('%s')
                if sys.version_info < (3, ):
                    pid = str(os.getpid())
                else:
                    pid = bytes(str(os.getpid()), 'ascii')
                s.sendall(pid)
        """ % TESTFN)
        with contextlib.closing(socket.socket(socket.AF_UNIX)) as sock:
            try:
                sock.settimeout(GLOBAL_TIMEOUT)
                sock.bind(TESTFN)
                sock.listen(1)
                pyrun(src)
                conn, _ = sock.accept()
                select.select([conn.fileno()], [], [], GLOBAL_TIMEOUT)
                zpid = int(conn.recv(1024))
                zproc = psutil.Process(zpid)
                call_until(lambda: zproc.status(),
                           "ret == psutil.STATUS_ZOMBIE")
                # A zombie process should always be instantiable
                zproc = psutil.Process(zpid)
                # ...and at least its status always be querable
                self.assertEqual(zproc.status(), psutil.STATUS_ZOMBIE)
                # ...and it should be considered 'running'
                self.assertTrue(zproc.is_running())
                # ...and as_dict() shouldn't crash
                zproc.as_dict()
                if hasattr(zproc, "rlimit"):
                    succeed_or_zombie_p_exc(zproc.rlimit, psutil.RLIMIT_NOFILE)
                    succeed_or_zombie_p_exc(zproc.rlimit, psutil.RLIMIT_NOFILE,
                                            (5, 5))
                # set methods
                succeed_or_zombie_p_exc(zproc.parent)
                if hasattr(zproc, 'cpu_affinity'):
                    succeed_or_zombie_p_exc(zproc.cpu_affinity, [0])
                succeed_or_zombie_p_exc(zproc.nice, 0)
                if hasattr(zproc, 'ionice'):
                    if LINUX:
                        succeed_or_zombie_p_exc(zproc.ionice, 2, 0)
                    else:
                        succeed_or_zombie_p_exc(zproc.ionice, 0)  # Windows
                if hasattr(zproc, 'rlimit'):
                    succeed_or_zombie_p_exc(zproc.rlimit,
                                            psutil.RLIMIT_NOFILE, (5, 5))
                succeed_or_zombie_p_exc(zproc.suspend)
                succeed_or_zombie_p_exc(zproc.resume)
                succeed_or_zombie_p_exc(zproc.terminate)
                succeed_or_zombie_p_exc(zproc.kill)

                # ...its parent should 'see' it
                # edit: not true on BSD and OSX
                # descendants = [x.pid for x in psutil.Process().children(
                #                recursive=True)]
                # self.assertIn(zpid, descendants)
                # XXX should we also assume ppid be usable?  Note: this
                # would be an important use case as the only way to get
                # rid of a zombie is to kill its parent.
                # self.assertEqual(zpid.ppid(), os.getpid())
                # ...and all other APIs should be able to deal with it
                self.assertTrue(psutil.pid_exists(zpid))
                self.assertIn(zpid, psutil.pids())
                self.assertIn(zpid, [x.pid for x in psutil.process_iter()])
                psutil._pmap = {}
                self.assertIn(zpid, [x.pid for x in psutil.process_iter()])
            finally:
                reap_children(search_all=True)

    def test_pid_0(self):
        # Process(0) is supposed to work on all platforms except Linux
        if 0 not in psutil.pids():
            self.assertRaises(psutil.NoSuchProcess, psutil.Process, 0)
            return

        p = psutil.Process(0)
        self.assertTrue(p.name())

        if POSIX:
            try:
                self.assertEqual(p.uids().real, 0)
                self.assertEqual(p.gids().real, 0)
            except psutil.AccessDenied:
                pass

            self.assertRaisesRegexp(
                ValueError, "preventing sending signal to process with PID 0",
                p.send_signal, signal.SIGTERM)

        self.assertIn(p.ppid(), (0, 1))
        # self.assertEqual(p.exe(), "")
        p.cmdline()
        try:
            p.num_threads()
        except psutil.AccessDenied:
            pass

        try:
            p.memory_info()
        except psutil.AccessDenied:
            pass

        try:
            if POSIX:
                self.assertEqual(p.username(), 'root')
            elif WINDOWS:
                self.assertEqual(p.username(), 'NT AUTHORITY\\SYSTEM')
            else:
                p.username()
        except psutil.AccessDenied:
            pass

        self.assertIn(0, psutil.pids())
        self.assertTrue(psutil.pid_exists(0))

    def test_Popen(self):
        # Popen class test
        # XXX this test causes a ResourceWarning on Python 3 because
        # psutil.__subproc instance doesn't get propertly freed.
        # Not sure what to do though.
        cmd = [PYTHON, "-c", "import time; time.sleep(60);"]
        proc = psutil.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
        try:
            proc.name()
            proc.stdin
            self.assertTrue(hasattr(proc, 'name'))
            self.assertTrue(hasattr(proc, 'stdin'))
            self.assertTrue(dir(proc))
            self.assertRaises(AttributeError, getattr, proc, 'foo')
        finally:
            proc.kill()
            proc.wait()
            self.assertIsNotNone(proc.returncode)


# ===================================================================
# --- Featch all processes test
# ===================================================================

class TestFetchAllProcesses(unittest.TestCase):
    """Test which iterates over all running processes and performs
    some sanity checks against Process API's returned values.
    """

    def setUp(self):
        if POSIX:
            import pwd
            pall = pwd.getpwall()
            self._uids = set([x.pw_uid for x in pall])
            self._usernames = set([x.pw_name for x in pall])

    def test_fetch_all(self):
        valid_procs = 0
        excluded_names = set([
            'send_signal', 'suspend', 'resume', 'terminate', 'kill', 'wait',
            'as_dict', 'cpu_percent', 'parent', 'children', 'pid'])
        if LINUX and not RLIMIT_SUPPORT:
            excluded_names.add('rlimit')
        attrs = []
        for name in dir(psutil.Process):
            if name.startswith("_"):
                continue
            if name in excluded_names:
                continue
            attrs.append(name)

        default = object()
        failures = []
        for name in attrs:
            for p in psutil.process_iter():
                ret = default
                try:
                    try:
                        args = ()
                        attr = getattr(p, name, None)
                        if attr is not None and callable(attr):
                            if name == 'rlimit':
                                args = (psutil.RLIMIT_NOFILE,)
                            ret = attr(*args)
                        else:
                            ret = attr
                        valid_procs += 1
                    except NotImplementedError:
                        msg = "%r was skipped because not implemented" % (
                            self.__class__.__name__ + '.test_' + name)
                        warn(msg)
                    except (psutil.NoSuchProcess, psutil.AccessDenied) as err:
                        self.assertEqual(err.pid, p.pid)
                        if err.name:
                            # make sure exception's name attr is set
                            # with the actual process name
                            self.assertEqual(err.name, p.name())
                        self.assertTrue(str(err))
                        self.assertTrue(err.msg)
                    else:
                        if ret not in (0, 0.0, [], None, ''):
                            assert ret, ret
                        meth = getattr(self, name)
                        meth(ret)
                except Exception as err:
                    s = '\n' + '=' * 70 + '\n'
                    s += "FAIL: test_%s (proc=%s" % (name, p)
                    if ret != default:
                        s += ", ret=%s)" % repr(ret)
                    s += ')\n'
                    s += '-' * 70
                    s += "\n%s" % traceback.format_exc()
                    s = "\n".join((" " * 4) + i for i in s.splitlines())
                    failures.append(s)
                    break

        if failures:
            self.fail(''.join(failures))

        # we should always have a non-empty list, not including PID 0 etc.
        # special cases.
        self.assertTrue(valid_procs > 0)

    def cmdline(self, ret):
        pass

    def exe(self, ret):
        if not ret:
            self.assertEqual(ret, '')
        else:
            assert os.path.isabs(ret), ret
            # Note: os.stat() may return False even if the file is there
            # hence we skip the test, see:
            # http://stackoverflow.com/questions/3112546/os-path-exists-lies
            if POSIX and os.path.isfile(ret):
                if hasattr(os, 'access') and hasattr(os, "X_OK"):
                    # XXX may fail on OSX
                    self.assertTrue(os.access(ret, os.X_OK))

    def ppid(self, ret):
        self.assertTrue(ret >= 0)

    def name(self, ret):
        self.assertIsInstance(ret, (str, unicode))
        self.assertTrue(ret)

    def create_time(self, ret):
        self.assertTrue(ret > 0)
        # this can't be taken for granted on all platforms
        # self.assertGreaterEqual(ret, psutil.boot_time())
        # make sure returned value can be pretty printed
        # with strftime
        time.strftime("%Y %m %d %H:%M:%S", time.localtime(ret))

    def uids(self, ret):
        for uid in ret:
            self.assertTrue(uid >= 0)
            self.assertIn(uid, self._uids)

    def gids(self, ret):
        # note: testing all gids as above seems not to be reliable for
        # gid == 30 (nodoby); not sure why.
        for gid in ret:
            self.assertTrue(gid >= 0)
            # self.assertIn(uid, self.gids

    def username(self, ret):
        self.assertTrue(ret)
        if POSIX:
            self.assertIn(ret, self._usernames)

    def status(self, ret):
        self.assertTrue(ret != "")
        self.assertTrue(ret != '?')
        self.assertIn(ret, VALID_PROC_STATUSES)

    def io_counters(self, ret):
        for field in ret:
            if field != -1:
                self.assertTrue(field >= 0)

    def ionice(self, ret):
        if LINUX:
            self.assertTrue(ret.ioclass >= 0)
            self.assertTrue(ret.value >= 0)
        else:
            self.assertTrue(ret >= 0)
            self.assertIn(ret, (0, 1, 2))

    def num_threads(self, ret):
        self.assertTrue(ret >= 1)

    def threads(self, ret):
        for t in ret:
            self.assertTrue(t.id >= 0)
            self.assertTrue(t.user_time >= 0)
            self.assertTrue(t.system_time >= 0)

    def cpu_times(self, ret):
        self.assertTrue(ret.user >= 0)
        self.assertTrue(ret.system >= 0)

    def memory_info(self, ret):
        self.assertTrue(ret.rss >= 0)
        self.assertTrue(ret.vms >= 0)

    def memory_info_ex(self, ret):
        for name in ret._fields:
            self.assertTrue(getattr(ret, name) >= 0)
        if POSIX and ret.vms != 0:
            # VMS is always supposed to be the highest
            for name in ret._fields:
                if name != 'vms':
                    value = getattr(ret, name)
                    assert ret.vms > value, ret
        elif WINDOWS:
            assert ret.peak_wset >= ret.wset, ret
            assert ret.peak_paged_pool >= ret.paged_pool, ret
            assert ret.peak_nonpaged_pool >= ret.nonpaged_pool, ret
            assert ret.peak_pagefile >= ret.pagefile, ret

    def open_files(self, ret):
        for f in ret:
            if WINDOWS:
                assert f.fd == -1, f
            else:
                self.assertIsInstance(f.fd, int)
            assert os.path.isabs(f.path), f
            assert os.path.isfile(f.path), f

    def num_fds(self, ret):
        self.assertTrue(ret >= 0)

    def connections(self, ret):
        self.assertEqual(len(ret), len(set(ret)))
        for conn in ret:
            check_connection_ntuple(conn)

    def cwd(self, ret):
        if ret is not None:  # BSD may return None
            assert os.path.isabs(ret), ret
            try:
                st = os.stat(ret)
            except OSError as err:
                # directory has been removed in mean time
                if err.errno != errno.ENOENT:
                    raise
            else:
                self.assertTrue(stat.S_ISDIR(st.st_mode))

    def memory_percent(self, ret):
        assert 0 <= ret <= 100, ret

    def is_running(self, ret):
        self.assertTrue(ret)

    def cpu_affinity(self, ret):
        assert ret != [], ret

    def terminal(self, ret):
        if ret is not None:
            assert os.path.isabs(ret), ret
            assert os.path.exists(ret), ret

    def memory_maps(self, ret):
        for nt in ret:
            for fname in nt._fields:
                value = getattr(nt, fname)
                if fname == 'path':
                    if not value.startswith('['):
                        assert os.path.isabs(nt.path), nt.path
                        # commented as on Linux we might get
                        # '/foo/bar (deleted)'
                        # assert os.path.exists(nt.path), nt.path
                elif fname in ('addr', 'perms'):
                    self.assertTrue(value)
                else:
                    self.assertIsInstance(value, (int, long))
                    assert value >= 0, value

    def num_handles(self, ret):
        if WINDOWS:
            self.assertGreaterEqual(ret, 0)
        else:
            self.assertGreaterEqual(ret, 0)

    def nice(self, ret):
        if POSIX:
            assert -20 <= ret <= 20, ret
        else:
            priorities = [getattr(psutil, x) for x in dir(psutil)
                          if x.endswith('_PRIORITY_CLASS')]
            self.assertIn(ret, priorities)

    def num_ctx_switches(self, ret):
        self.assertTrue(ret.voluntary >= 0)
        self.assertTrue(ret.involuntary >= 0)

    def rlimit(self, ret):
        self.assertEqual(len(ret), 2)
        self.assertGreaterEqual(ret[0], -1)
        self.assertGreaterEqual(ret[1], -1)


# ===================================================================
# --- Limited user tests
# ===================================================================

@unittest.skipUnless(POSIX, "UNIX only")
@unittest.skipUnless(hasattr(os, 'getuid') and os.getuid() == 0,
                     "super user privileges are required")
class LimitedUserTestCase(TestProcess):
    """Repeat the previous tests by using a limited user.
    Executed only on UNIX and only if the user who run the test script
    is root.
    """
    # the uid/gid the test suite runs under
    if hasattr(os, 'getuid'):
        PROCESS_UID = os.getuid()
        PROCESS_GID = os.getgid()

    def __init__(self, *args, **kwargs):
        TestProcess.__init__(self, *args, **kwargs)
        # re-define all existent test methods in order to
        # ignore AccessDenied exceptions
        for attr in [x for x in dir(self) if x.startswith('test')]:
            meth = getattr(self, attr)

            def test_(self):
                try:
                    meth()
                except psutil.AccessDenied:
                    pass
            setattr(self, attr, types.MethodType(test_, self))

    def setUp(self):
        safe_remove(TESTFN)
        TestProcess.setUp(self)
        os.setegid(1000)
        os.seteuid(1000)

    def tearDown(self):
        os.setegid(self.PROCESS_UID)
        os.seteuid(self.PROCESS_GID)
        TestProcess.tearDown(self)

    def test_nice(self):
        try:
            psutil.Process().nice(-1)
        except psutil.AccessDenied:
            pass
        else:
            self.fail("exception not raised")

    def test_zombie_process(self):
        # causes problems if test test suite is run as root
        pass


# ===================================================================
# --- Misc tests
# ===================================================================

class TestMisc(unittest.TestCase):
    """Misc / generic tests."""

    def test_process__repr__(self, func=repr):
        p = psutil.Process()
        r = func(p)
        self.assertIn("psutil.Process", r)
        self.assertIn("pid=%s" % p.pid, r)
        self.assertIn("name=", r)
        self.assertIn(p.name(), r)
        with mock.patch.object(psutil.Process, "name",
                               side_effect=psutil.ZombieProcess(os.getpid())):
            p = psutil.Process()
            r = func(p)
            self.assertIn("pid=%s" % p.pid, r)
            self.assertIn("zombie", r)
            self.assertNotIn("name=", r)
        with mock.patch.object(psutil.Process, "name",
                               side_effect=psutil.NoSuchProcess(os.getpid())):
            p = psutil.Process()
            r = func(p)
            self.assertIn("pid=%s" % p.pid, r)
            self.assertIn("terminated", r)
            self.assertNotIn("name=", r)

    def test_process__str__(self):
        self.test_process__repr__(func=str)

    def test_no_such_process__repr__(self, func=repr):
        self.assertEqual(
            repr(psutil.NoSuchProcess(321)),
            "psutil.NoSuchProcess process no longer exists (pid=321)")
        self.assertEqual(
            repr(psutil.NoSuchProcess(321, name='foo')),
            "psutil.NoSuchProcess process no longer exists (pid=321, "
            "name='foo')")
        self.assertEqual(
            repr(psutil.NoSuchProcess(321, msg='foo')),
            "psutil.NoSuchProcess foo")

    def test_zombie_process__repr__(self, func=repr):
        self.assertEqual(
            repr(psutil.ZombieProcess(321)),
            "psutil.ZombieProcess process still exists but it's a zombie "
            "(pid=321)")
        self.assertEqual(
            repr(psutil.ZombieProcess(321, name='foo')),
            "psutil.ZombieProcess process still exists but it's a zombie "
            "(pid=321, name='foo')")
        self.assertEqual(
            repr(psutil.ZombieProcess(321, name='foo', ppid=1)),
            "psutil.ZombieProcess process still exists but it's a zombie "
            "(pid=321, name='foo', ppid=1)")
        self.assertEqual(
            repr(psutil.ZombieProcess(321, msg='foo')),
            "psutil.ZombieProcess foo")

    def test_access_denied__repr__(self, func=repr):
        self.assertEqual(
            repr(psutil.AccessDenied(321)),
            "psutil.AccessDenied (pid=321)")
        self.assertEqual(
            repr(psutil.AccessDenied(321, name='foo')),
            "psutil.AccessDenied (pid=321, name='foo')")
        self.assertEqual(
            repr(psutil.AccessDenied(321, msg='foo')),
            "psutil.AccessDenied foo")

    def test_timeout_expired__repr__(self, func=repr):
        self.assertEqual(
            repr(psutil.TimeoutExpired(321)),
            "psutil.TimeoutExpired timeout after 321 seconds")
        self.assertEqual(
            repr(psutil.TimeoutExpired(321, pid=111)),
            "psutil.TimeoutExpired timeout after 321 seconds (pid=111)")
        self.assertEqual(
            repr(psutil.TimeoutExpired(321, pid=111, name='foo')),
            "psutil.TimeoutExpired timeout after 321 seconds "
            "(pid=111, name='foo')")

    def test_process__eq__(self):
        p1 = psutil.Process()
        p2 = psutil.Process()
        self.assertEqual(p1, p2)
        p2._ident = (0, 0)
        self.assertNotEqual(p1, p2)
        self.assertNotEqual(p1, 'foo')

    def test_process__hash__(self):
        s = set([psutil.Process(), psutil.Process()])
        self.assertEqual(len(s), 1)

    def test__all__(self):
        dir_psutil = dir(psutil)
        for name in dir_psutil:
            if name in ('callable', 'error', 'namedtuple',
                        'long', 'test', 'NUM_CPUS', 'BOOT_TIME',
                        'TOTAL_PHYMEM'):
                continue
            if not name.startswith('_'):
                try:
                    __import__(name)
                except ImportError:
                    if name not in psutil.__all__:
                        fun = getattr(psutil, name)
                        if fun is None:
                            continue
                        if (fun.__doc__ is not None and
                                'deprecated' not in fun.__doc__.lower()):
                            self.fail('%r not in psutil.__all__' % name)

        # Import 'star' will break if __all__ is inconsistent, see:
        # https://github.com/giampaolo/psutil/issues/656
        # Can't do `from psutil import *` as it won't work on python 3
        # so we simply iterate over __all__.
        for name in psutil.__all__:
            self.assertIn(name, dir_psutil)

    def test_version(self):
        self.assertEqual('.'.join([str(x) for x in psutil.version_info]),
                         psutil.__version__)

    def test_memoize(self):
        from psutil._common import memoize

        @memoize
        def foo(*args, **kwargs):
            "foo docstring"
            calls.append(None)
            return (args, kwargs)

        calls = []
        # no args
        for x in range(2):
            ret = foo()
            expected = ((), {})
            self.assertEqual(ret, expected)
            self.assertEqual(len(calls), 1)
        # with args
        for x in range(2):
            ret = foo(1)
            expected = ((1, ), {})
            self.assertEqual(ret, expected)
            self.assertEqual(len(calls), 2)
        # with args + kwargs
        for x in range(2):
            ret = foo(1, bar=2)
            expected = ((1, ), {'bar': 2})
            self.assertEqual(ret, expected)
            self.assertEqual(len(calls), 3)
        # clear cache
        foo.cache_clear()
        ret = foo()
        expected = ((), {})
        self.assertEqual(ret, expected)
        self.assertEqual(len(calls), 4)
        # docstring
        self.assertEqual(foo.__doc__, "foo docstring")

    def test_isfile_strict(self):
        from psutil._common import isfile_strict
        this_file = os.path.abspath(__file__)
        assert isfile_strict(this_file)
        assert not isfile_strict(os.path.dirname(this_file))
        with mock.patch('psutil._common.os.stat',
                        side_effect=OSError(errno.EPERM, "foo")):
            self.assertRaises(OSError, isfile_strict, this_file)
        with mock.patch('psutil._common.os.stat',
                        side_effect=OSError(errno.EACCES, "foo")):
            self.assertRaises(OSError, isfile_strict, this_file)
        with mock.patch('psutil._common.os.stat',
                        side_effect=OSError(errno.EINVAL, "foo")):
            assert not isfile_strict(this_file)
        with mock.patch('psutil._common.stat.S_ISREG', return_value=False):
            assert not isfile_strict(this_file)

    def test_serialization(self):
        def check(ret):
            if json is not None:
                json.loads(json.dumps(ret))
            a = pickle.dumps(ret)
            b = pickle.loads(a)
            self.assertEqual(ret, b)

        check(psutil.Process().as_dict())
        check(psutil.virtual_memory())
        check(psutil.swap_memory())
        check(psutil.cpu_times())
        check(psutil.cpu_times_percent(interval=0))
        check(psutil.net_io_counters())
        if LINUX and not os.path.exists('/proc/diskstats'):
            pass
        else:
            if not APPVEYOR:
                check(psutil.disk_io_counters())
        check(psutil.disk_partitions())
        check(psutil.disk_usage(os.getcwd()))
        check(psutil.users())

    def test_setup_script(self):
        here = os.path.abspath(os.path.dirname(__file__))
        setup_py = os.path.realpath(os.path.join(here, '..', 'setup.py'))
        module = imp.load_source('setup', setup_py)
        self.assertRaises(SystemExit, module.setup)
        self.assertEqual(module.get_version(), psutil.__version__)

    def test_ad_on_process_creation(self):
        # We are supposed to be able to instantiate Process also in case
        # of zombie processes or access denied.
        with mock.patch.object(psutil.Process, 'create_time',
                               side_effect=psutil.AccessDenied) as meth:
            psutil.Process()
            assert meth.called
        with mock.patch.object(psutil.Process, 'create_time',
                               side_effect=psutil.ZombieProcess(1)) as meth:
            psutil.Process()
            assert meth.called
        with mock.patch.object(psutil.Process, 'create_time',
                               side_effect=ValueError) as meth:
            with self.assertRaises(ValueError):
                psutil.Process()
            assert meth.called


# ===================================================================
# --- Example script tests
# ===================================================================

class TestExampleScripts(unittest.TestCase):
    """Tests for scripts in the examples directory."""

    def assert_stdout(self, exe, args=None):
        exe = os.path.join(EXAMPLES_DIR, exe)
        if args:
            exe = exe + ' ' + args
        try:
            out = sh(sys.executable + ' ' + exe).strip()
        except RuntimeError as err:
            if 'AccessDenied' in str(err):
                return str(err)
            else:
                raise
        assert out, out
        return out

    def assert_syntax(self, exe, args=None):
        exe = os.path.join(EXAMPLES_DIR, exe)
        with open(exe, 'r') as f:
            src = f.read()
        ast.parse(src)

    def test_check_presence(self):
        # make sure all example scripts have a test method defined
        meths = dir(self)
        for name in os.listdir(EXAMPLES_DIR):
            if name.endswith('.py'):
                if 'test_' + os.path.splitext(name)[0] not in meths:
                    # self.assert_stdout(name)
                    self.fail('no test defined for %r script'
                              % os.path.join(EXAMPLES_DIR, name))

    def test_disk_usage(self):
        self.assert_stdout('disk_usage.py')

    def test_free(self):
        self.assert_stdout('free.py')

    def test_meminfo(self):
        self.assert_stdout('meminfo.py')

    def test_process_detail(self):
        self.assert_stdout('process_detail.py')

    @unittest.skipIf(APPVEYOR, "can't find users on Appveyor")
    def test_who(self):
        self.assert_stdout('who.py')

    def test_ps(self):
        self.assert_stdout('ps.py')

    def test_pstree(self):
        self.assert_stdout('pstree.py')

    def test_netstat(self):
        self.assert_stdout('netstat.py')

    @unittest.skipIf(TRAVIS, "permission denied on travis")
    def test_ifconfig(self):
        self.assert_stdout('ifconfig.py')

    def test_pmap(self):
        self.assert_stdout('pmap.py', args=str(os.getpid()))

    @unittest.skipIf(ast is None,
                     'ast module not available on this python version')
    def test_killall(self):
        self.assert_syntax('killall.py')

    @unittest.skipIf(ast is None,
                     'ast module not available on this python version')
    def test_nettop(self):
        self.assert_syntax('nettop.py')

    @unittest.skipIf(ast is None,
                     'ast module not available on this python version')
    def test_top(self):
        self.assert_syntax('top.py')

    @unittest.skipIf(ast is None,
                     'ast module not available on this python version')
    def test_iotop(self):
        self.assert_syntax('iotop.py')

    def test_pidof(self):
        output = self.assert_stdout('pidof.py %s' % psutil.Process().name())
        self.assertIn(str(os.getpid()), output)


def main():
    tests = []
    test_suite = unittest.TestSuite()
    tests.append(TestSystemAPIs)
    tests.append(TestProcess)
    tests.append(TestFetchAllProcesses)
    tests.append(TestMisc)
    tests.append(TestExampleScripts)
    tests.append(LimitedUserTestCase)

    if POSIX:
        from _posix import PosixSpecificTestCase
        tests.append(PosixSpecificTestCase)

    # import the specific platform test suite
    stc = None
    if LINUX:
        from _linux import LinuxSpecificTestCase as stc
    elif WINDOWS:
        from _windows import WindowsSpecificTestCase as stc
        from _windows import TestDualProcessImplementation
        tests.append(TestDualProcessImplementation)
    elif OSX:
        from _osx import OSXSpecificTestCase as stc
    elif BSD:
        from _bsd import BSDSpecificTestCase as stc
    elif SUNOS:
        from _sunos import SunOSSpecificTestCase as stc
    if stc is not None:
        tests.append(stc)

    for test_class in tests:
        test_suite.addTest(unittest.makeSuite(test_class))
    result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    return result.wasSuccessful()

if __name__ == '__main__':
    if not main():
        sys.exit(1)
