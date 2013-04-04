#!/usr/bin/env python

# Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
psutil test suite.

Note: this is targeted for both python 2.x and 3.x so there's no need
to use 2to3 tool first.
"""

from __future__ import division
import unittest
import os
import sys
import subprocess
import time
import signal
import types
import traceback
import socket
import warnings
import atexit
import errno
import threading
import tempfile
import stat
import collections
import datetime

import psutil
from psutil._compat import PY3, callable, long, wraps


PYTHON = os.path.realpath(sys.executable)
DEVNULL = open(os.devnull, 'r+')
TESTFN = os.path.join(os.getcwd(), "$testfile")
POSIX = os.name == 'posix'
LINUX = sys.platform.startswith("linux")
WINDOWS = sys.platform.startswith("win32")
OSX = sys.platform.startswith("darwin")
BSD = sys.platform.startswith("freebsd")


_subprocesses_started = set()

def get_test_subprocess(cmd=None, stdout=DEVNULL, stderr=DEVNULL, stdin=DEVNULL,
                        wait=False):
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
        pyline += "import time; time.sleep(3600);"
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
    _subprocesses_started.add(sproc.pid)
    return sproc

def warn(msg, warntype=RuntimeWarning):
    """Raise a warning msg."""
    warnings.warn(msg, warntype)

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

def wait_for_pid(pid, timeout=1):
    """Wait for pid to show up in the process list then return.
    Used in the test suite to give time the sub process to initialize.
    """
    raise_at = time.time() + timeout
    while 1:
        if pid in psutil.get_pid_list():
            # give it one more iteration to allow full initialization
            time.sleep(0.01)
            return
        time.sleep(0.0001)
        if time.time() >= raise_at:
            raise RuntimeError("Timed out")

def reap_children(search_all=False):
    """Kill any subprocess started by this test suite and ensure that
    no zombies stick around to hog resources and create problems when
    looking for refleaks.
    """
    pids = _subprocesses_started
    if search_all:
        this_process = psutil.Process(os.getpid())
        for p in this_process.get_children(recursive=True):
            pids.add(p.pid)
    while pids:
        pid = pids.pop()
        try:
            child = psutil.Process(pid)
            child.kill()
        except psutil.NoSuchProcess:
            pass
        except psutil.AccessDenied:
            warn("couldn't kill child process with pid %s" % pid)
        else:
            child.wait(timeout=3)

def check_ip_address(addr, family):
    """Attempts to check IP address's validity."""
    if not addr:
        return
    ip, port = addr
    assert isinstance(port, int), port
    if family == socket.AF_INET:
        ip = list(map(int, ip.split('.')))
        assert len(ip) == 4, ip
        for num in ip:
            assert 0 <= num <= 255, ip
    assert 0 <= port <= 65535, port

def safe_remove(fname):
    try:
        os.remove(fname)
    except OSError:
        err = sys.exc_info()[1]
        if err.args[0] != errno.ENOENT:
            raise

def call_until(fun, expr, timeout=1):
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


def skipIf(condition, reason="", warn=False):
    """Decorator which skip a test under if condition is satisfied.
    This is a substitute of unittest.skipIf which is available
    only in python 2.7 and 3.2.
    If 'reason' argument is provided this will be printed during
    tests execution.
    If 'warn' is provided a RuntimeWarning will be shown when all
    tests are run.
    """
    def outer(fun, *args, **kwargs):
        def inner(self):
            if condition:
                sys.stdout.write("skipped-")
                sys.stdout.flush()
                if warn:
                    objname = "%s.%s" % (self.__class__.__name__, fun.__name__)
                    msg = "%s was skipped" % objname
                    if reason:
                        msg += "; reason: " + repr(reason)
                    atexit.register(warn, msg)
                return
            else:
                return fun(self, *args, **kwargs)
        return inner
    return outer

def skipUnless(condition, reason="", warn=False):
    """Contrary of skipIf."""
    if not condition:
        return skipIf(True, reason, warn)
    return skipIf(False)

def skip_on_access_denied(only_if=None):
    """Decorator to Ignore AccessDenied exceptions."""
    def decorator(fun):
        @wraps(fun)
        def wrapper(*args, **kwargs):
            try:
                return fun(*args, **kwargs)
            except psutil.AccessDenied:
                if only_if is not None:
                    if not only_if:
                        raise
                atexit.register(warn, "%r was skipped because it raised " \
                                      "AccessDenied" % fun.__name__)
        return wrapper
    return decorator


def supports_ipv6():
    """Return True if IPv6 is supported on this platform."""
    if not socket.has_ipv6 or not hasattr(socket, "AF_INET6"):
        return False
    sock = None
    try:
        try:
            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            sock.bind(("::1", 0))
        except (socket.error, socket.gaierror):
            return False
        else:
            return True
    finally:
        if sock is not None:
            sock.close()


class ThreadTask(threading.Thread):
    """A thread object used for running process thread tests."""

    def __init__(self):
        threading.Thread.__init__(self)
        self._running = False
        self._interval = None
        self._flag = threading.Event()

    def __repr__(self):
        name =  self.__class__.__name__
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


class TestCase(unittest.TestCase):

    def setUp(self):
        safe_remove(TESTFN)

    def tearDown(self):
        reap_children()

    if not hasattr(unittest.TestCase, "assertIn"):
        def assertIn(self, member, container, msg=None):
            if member not in container:
                self.fail(msg or \
                        '%s not found in %s' % (repr(member), repr(container)))

    def assert_eq_w_tol(self, first, second, tolerance):
        difference = abs(first - second)
        if difference <= tolerance:
            return
        msg = '%r != %r within %r delta (%r difference)' \
              % (first, second, tolerance, difference)
        raise AssertionError(msg)

    # ============================
    # tests for system-related API
    # ============================

    def test_process_iter(self):
        assert os.getpid() in [x.pid for x in psutil.process_iter()]
        sproc = get_test_subprocess()
        assert sproc.pid in [x.pid for x in psutil.process_iter()]
        p = psutil.Process(sproc.pid)
        p.kill()
        p.wait()
        assert sproc.pid not in [x.pid for x in psutil.process_iter()]

    def test_TOTAL_PHYMEM(self):
        x = psutil.TOTAL_PHYMEM
        assert isinstance(x, (int, long))
        assert x > 0
        self.assertEqual(x, psutil.virtual_memory().total)

    def test_BOOT_TIME(self, arg=None):
        x = arg or psutil.BOOT_TIME
        assert isinstance(x, float), x
        assert x > 0, x
        assert x < time.time(), x

    def test_get_boot_time(self):
        self.test_BOOT_TIME(psutil.get_boot_time())
        if WINDOWS:
            # work around float precision issues; give it 1 secs tolerance
            diff = abs(psutil.get_boot_time() - psutil.BOOT_TIME)
            assert diff < 1, diff
        else:
            self.assertEqual(psutil.get_boot_time(), psutil.BOOT_TIME)

    def test_NUM_CPUS(self):
        self.assertEqual(psutil.NUM_CPUS, len(psutil.cpu_times(percpu=True)))
        assert psutil.NUM_CPUS >= 1, psutil.NUM_CPUS

    @skipUnless(POSIX)
    def test_PAGESIZE(self):
        # pagesize is used internally to perform different calculations
        # and it's determined by using SC_PAGE_SIZE; make sure
        # getpagesize() returns the same value.
        import resource
        self.assertEqual(os.sysconf("SC_PAGE_SIZE"), resource.getpagesize())

    def test_deprecated_apis(self):
        warnings.filterwarnings("error")
        p = psutil.Process(os.getpid())
        try:
            self.assertRaises(DeprecationWarning, __import__, 'psutil.error')
            self.assertRaises(DeprecationWarning, psutil.virtmem_usage)
            self.assertRaises(DeprecationWarning, psutil.used_phymem)
            self.assertRaises(DeprecationWarning, psutil.avail_phymem)
            self.assertRaises(DeprecationWarning, psutil.total_virtmem)
            self.assertRaises(DeprecationWarning, psutil.used_virtmem)
            self.assertRaises(DeprecationWarning, psutil.avail_virtmem)
            self.assertRaises(DeprecationWarning, psutil.phymem_usage)
            self.assertRaises(DeprecationWarning, psutil.get_process_list)
            self.assertRaises(DeprecationWarning, psutil.get_process_list)
            if LINUX:
                self.assertRaises(DeprecationWarning, psutil.phymem_buffers)
                self.assertRaises(DeprecationWarning, psutil.cached_phymem)
            try:
                p.nice
            except DeprecationWarning:
                pass
            else:
                self.fail("p.nice didn't raise DeprecationWarning")
        finally:
            warnings.resetwarnings()

    def test_deprecated_apis_retval(self):
        warnings.filterwarnings("ignore")
        p = psutil.Process(os.getpid())
        try:
            self.assertEqual(psutil.total_virtmem(), psutil.swap_memory().total)
            self.assertEqual(psutil.get_process_list(), list(psutil.process_iter()))
            self.assertEqual(p.nice, p.get_nice())
        finally:
            warnings.resetwarnings()

    def test_virtual_memory(self):
        mem = psutil.virtual_memory()
        assert mem.total > 0, mem
        assert mem.available > 0, mem
        assert 0 <= mem.percent <= 100, mem
        assert mem.used > 0, mem
        assert mem.free >= 0, mem
        for name in mem._fields:
            if name != 'total':
                value = getattr(mem, name)
                if not value >= 0:
                    self.fail("%r < 0 (%s)" % (name, value))
                if value > mem.total:
                    self.fail("%r > total (total=%s, %s=%s)" \
                              % (name, mem.total, name, value))

    def test_swap_memory(self):
        mem = psutil.swap_memory()
        assert mem.total > 0, mem
        assert mem.used >= 0, mem
        assert mem.free > 0, mem
        assert 0 <= mem.percent <= 100, mem
        assert mem.sin >= 0, mem
        assert mem.sout >= 0, mem

    def test_pid_exists(self):
        sproc = get_test_subprocess(wait=True)
        assert psutil.pid_exists(sproc.pid)
        p = psutil.Process(sproc.pid)
        p.kill()
        p.wait()
        self.assertFalse(psutil.pid_exists(sproc.pid))
        self.assertFalse(psutil.pid_exists(-1))

    def test_pid_exists_2(self):
        reap_children()
        pids = psutil.get_pid_list()
        for pid in pids:
            try:
                assert psutil.pid_exists(pid)
            except AssertionError:
                # in case the process disappeared in meantime fail only
                # if it is no longer in get_pid_list()
                time.sleep(.1)
                if pid in psutil.get_pid_list():
                    self.fail(pid)
        pids = range(max(pids) + 5000, max(pids) + 6000)
        for pid in pids:
            self.assertFalse(psutil.pid_exists(pid))

    def test_get_pid_list(self):
        plist = [x.pid for x in psutil.process_iter()]
        pidlist = psutil.get_pid_list()
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

    def test_sys_cpu_times(self):
        total = 0
        times = psutil.cpu_times()
        sum(times)
        for cp_time in times:
            assert isinstance(cp_time, float)
            assert cp_time >= 0.0, cp_time
            total += cp_time
        self.assertEqual(total, sum(times))
        str(times)

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
                assert isinstance(cp_time, float)
                assert cp_time >= 0.0, cp_time
                total += cp_time
            self.assertEqual(total, sum(times))
            str(times)
        self.assertEqual(len(psutil.cpu_times(percpu=True)[0]),
                         len(psutil.cpu_times(percpu=False)))

    def test_sys_per_cpu_times2(self):
        tot1 = psutil.cpu_times(percpu=True)
        stop_at = time.time() + 0.1
        while 1:
            if time.time() >= stop_at:
                break
        tot2 = psutil.cpu_times(percpu=True)
        for t1, t2 in zip(tot1, tot2):
            t1, t2 = sum(t1), sum(t2)
            difference = t2 - t1
            if difference >= 0.05:
                return
        self.fail()

    def _test_cpu_percent(self, percent):
        assert isinstance(percent, float), percent
        assert percent >= 0.0, percent
        assert percent <= 100.0, percent

    def test_sys_cpu_percent(self):
        psutil.cpu_percent(interval=0.001)
        for x in range(1000):
            self._test_cpu_percent(psutil.cpu_percent(interval=None))

    def test_sys_per_cpu_percent(self):
        self.assertEqual(len(psutil.cpu_percent(interval=0.001, percpu=True)),
                         psutil.NUM_CPUS)
        for x in range(1000):
            percents = psutil.cpu_percent(interval=None, percpu=True)
            for percent in percents:
                self._test_cpu_percent(percent)

    def test_sys_cpu_times_percent(self):
        psutil.cpu_times_percent(interval=0.001)
        for x in range(1000):
            cpu = psutil.cpu_times_percent(interval=None)
            for percent in cpu:
                self._test_cpu_percent(percent)
            self._test_cpu_percent(sum(cpu))

    def test_sys_per_cpu_times_percent(self):
        self.assertEqual(len(psutil.cpu_times_percent(interval=0.001,
                                                      percpu=True)),
                         psutil.NUM_CPUS)
        for x in range(1000):
            cpus = psutil.cpu_times_percent(interval=None, percpu=True)
            for cpu in cpus:
                for percent in cpu:
                    self._test_cpu_percent(percent)
                self._test_cpu_percent(sum(cpu))

    def test_disk_usage(self):
        usage = psutil.disk_usage(os.getcwd())
        assert usage.total > 0, usage
        assert usage.used > 0, usage
        assert usage.free > 0, usage
        assert usage.total > usage.used, usage
        assert usage.total > usage.free, usage
        assert 0 <= usage.percent <= 100, usage.percent

        # if path does not exist OSError ENOENT is expected across
        # all platforms
        fname = tempfile.mktemp()
        try:
            psutil.disk_usage(fname)
        except OSError:
            err = sys.exc_info()[1]
            if err.args[0] != errno.ENOENT:
                raise
        else:
            self.fail("OSError not raised")

    def test_disk_partitions(self):
        for disk in psutil.disk_partitions(all=False):
            if WINDOWS and 'cdrom' in disk.opts:
                continue
            assert os.path.exists(disk.device), disk
            assert os.path.isdir(disk.mountpoint), disk
            assert disk.fstype, disk
            assert isinstance(disk.opts, str)
        for disk in psutil.disk_partitions(all=True):
            if not WINDOWS:
                try:
                    os.stat(disk.mountpoint)
                except OSError:
                    # http://mail.python.org/pipermail/python-dev/2012-June/120787.html
                    err = sys.exc_info()[1]
                    if err.errno not in (errno.EPERM, errno.EACCES):
                        raise
                else:
                    assert os.path.isdir(disk.mountpoint), disk.mountpoint
            assert isinstance(disk.fstype, str)
            assert isinstance(disk.opts, str)

        def find_mount_point(path):
            path = os.path.abspath(path)
            while not os.path.ismount(path):
                path = os.path.dirname(path)
            return path

        mount = find_mount_point(__file__)
        mounts = [x.mountpoint for x in psutil.disk_partitions(all=True)]
        self.assertIn(mount, mounts)
        psutil.disk_usage(mount)

    def test_network_io_counters(self):
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

        ret = psutil.network_io_counters(pernic=False)
        check_ntuple(ret)
        ret = psutil.network_io_counters(pernic=True)
        assert ret != []
        for key in ret:
            assert key
            check_ntuple(ret[key])

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
                # http://code.google.com/p/psutil/issues/detail?id=338
                while key[-1].isdigit():
                    key = key[:-1]
                assert key not in ret, (key, ret.keys())

    def test_get_users(self):
        users = psutil.get_users()
        assert users
        for user in users:
            assert user.name, user
            user.terminal
            user.host
            assert user.started > 0.0, user
            datetime.datetime.fromtimestamp(user.started)

    # ====================
    # Process object tests
    # ====================

    def test_kill(self):
        sproc = get_test_subprocess(wait=True)
        test_pid = sproc.pid
        p = psutil.Process(test_pid)
        name = p.name
        p.kill()
        p.wait()
        self.assertFalse(psutil.pid_exists(test_pid) and name == PYTHON)

    def test_terminate(self):
        sproc = get_test_subprocess(wait=True)
        test_pid = sproc.pid
        p = psutil.Process(test_pid)
        name = p.name
        p.terminate()
        p.wait()
        self.assertFalse(psutil.pid_exists(test_pid) and name == PYTHON)

    def test_send_signal(self):
        if POSIX:
            sig = signal.SIGKILL
        else:
            sig = signal.SIGTERM
        sproc = get_test_subprocess()
        test_pid = sproc.pid
        p = psutil.Process(test_pid)
        name = p.name
        p.send_signal(sig)
        p.wait()
        self.assertFalse(psutil.pid_exists(test_pid) and name == PYTHON)

    def test_wait(self):
        # check exit code signal
        sproc = get_test_subprocess()
        p = psutil.Process(sproc.pid)
        p.kill()
        code = p.wait()
        if os.name == 'posix':
            self.assertEqual(code, signal.SIGKILL)
        else:
            self.assertEqual(code, 0)
        self.assertFalse(p.is_running())

        sproc = get_test_subprocess()
        p = psutil.Process(sproc.pid)
        p.terminate()
        code = p.wait()
        if os.name == 'posix':
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
        p.name
        self.assertRaises(psutil.TimeoutExpired, p.wait, 0.01)

        # timeout < 0 not allowed
        self.assertRaises(ValueError, p.wait, -1)

    @skipUnless(POSIX)
    def test_wait_non_children(self):
        # test wait() against processes which are not our children
        code = "import sys;"
        code += "from subprocess import Popen, PIPE;"
        code += "cmd = ['%s', '-c', 'import time; time.sleep(10)'];" %PYTHON
        code += "sp = Popen(cmd, stdout=PIPE);"
        code += "sys.stdout.write(str(sp.pid));"
        sproc = get_test_subprocess([PYTHON, "-c", code], stdout=subprocess.PIPE)

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
        while 1:
            try:
                code = p.wait(0)
            except psutil.TimeoutExpired:
                if time.time() >= stop_at:
                    raise
            else:
                break
        if os.name == 'posix':
            self.assertEqual(code, signal.SIGKILL)
        else:
            self.assertEqual(code, 0)
        self.assertFalse(p.is_running())

    def test_cpu_percent(self):
        p = psutil.Process(os.getpid())
        p.get_cpu_percent(interval=0.001)
        p.get_cpu_percent(interval=0.001)
        for x in range(100):
            percent = p.get_cpu_percent(interval=None)
            assert isinstance(percent, float)
            assert percent >= 0.0, percent
            if os.name != 'posix':
                assert percent <= 100.0, percent
            else:
                assert percent >= 0.0, percent

    def test_cpu_times(self):
        times = psutil.Process(os.getpid()).get_cpu_times()
        assert (times.user > 0.0) or (times.system > 0.0), times
        # make sure returned values can be pretty printed with strftime
        time.strftime("%H:%M:%S", time.localtime(times.user))
        time.strftime("%H:%M:%S", time.localtime(times.system))

    # Test Process.cpu_times() against os.times()
    # os.times() is broken on Python 2.6
    # http://bugs.python.org/issue1040026
    # XXX fails on OSX: not sure if it's for os.times(). We should
    # try this with Python 2.7 and re-enable the test.

    @skipUnless(sys.version_info > (2, 6, 1) and not OSX)
    def test_cpu_times2(self):
        user_time, kernel_time = psutil.Process(os.getpid()).get_cpu_times()
        utime, ktime = os.times()[:2]

        # Use os.times()[:2] as base values to compare our results
        # using a tolerance  of +/- 0.1 seconds.
        # It will fail if the difference between the values is > 0.1s.
        if (max([user_time, utime]) - min([user_time, utime])) > 0.1:
            self.fail("expected: %s, found: %s" %(utime, user_time))

        if (max([kernel_time, ktime]) - min([kernel_time, ktime])) > 0.1:
            self.fail("expected: %s, found: %s" %(ktime, kernel_time))

    def test_create_time(self):
        sproc = get_test_subprocess(wait=True)
        now = time.time()
        p = psutil.Process(sproc.pid)
        create_time = p.create_time

        # Use time.time() as base value to compare our result using a
        # tolerance of +/- 1 second.
        # It will fail if the difference between the values is > 2s.
        difference = abs(create_time - now)
        if difference > 2:
            self.fail("expected: %s, found: %s, difference: %s"
                      % (now, create_time, difference))

        # make sure returned value can be pretty printed with strftime
        time.strftime("%Y %m %d %H:%M:%S", time.localtime(p.create_time))

    @skipIf(WINDOWS)
    def test_terminal(self):
        tty = sh('tty')
        p = psutil.Process(os.getpid())
        self.assertEqual(p.terminal, tty)

    @skipIf(OSX, warn=False)
    def test_get_io_counters(self):
        p = psutil.Process(os.getpid())
        # test reads
        io1 = p.get_io_counters()
        f = open(PYTHON, 'rb')
        f.read()
        f.close()
        io2 = p.get_io_counters()
        if not BSD:
            assert io2.read_count > io1.read_count, (io1, io2)
            self.assertEqual(io2.write_count, io1.write_count)
        assert io2.read_bytes >= io1.read_bytes, (io1, io2)
        assert io2.write_bytes >= io1.write_bytes, (io1, io2)
        # test writes
        io1 = p.get_io_counters()
        f = tempfile.TemporaryFile()
        if PY3:
            f.write(bytes("x" * 1000000, 'ascii'))
        else:
            f.write("x" * 1000000)
        f.close()
        io2 = p.get_io_counters()
        assert io2.write_count >= io1.write_count, (io1, io2)
        assert io2.write_bytes >= io1.write_bytes, (io1, io2)
        assert io2.read_count >= io1.read_count, (io1, io2)
        assert io2.read_bytes >= io1.read_bytes, (io1, io2)

    # Linux and Windows Vista+
    @skipUnless(hasattr(psutil.Process, 'get_ionice'))
    def test_get_set_ionice(self):
        if LINUX:
            from psutil import (IOPRIO_CLASS_NONE, IOPRIO_CLASS_RT,
                                IOPRIO_CLASS_BE, IOPRIO_CLASS_IDLE)
            self.assertEqual(IOPRIO_CLASS_NONE, 0)
            self.assertEqual(IOPRIO_CLASS_RT, 1)
            self.assertEqual(IOPRIO_CLASS_BE, 2)
            self.assertEqual(IOPRIO_CLASS_IDLE, 3)
            p = psutil.Process(os.getpid())
            try:
                p.set_ionice(2)
                ioclass, value = p.get_ionice()
                self.assertEqual(ioclass, 2)
                self.assertEqual(value, 4)
                #
                p.set_ionice(3)
                ioclass, value = p.get_ionice()
                self.assertEqual(ioclass, 3)
                self.assertEqual(value, 0)
                #
                p.set_ionice(2, 0)
                ioclass, value = p.get_ionice()
                self.assertEqual(ioclass, 2)
                self.assertEqual(value, 0)
                p.set_ionice(2, 7)
                ioclass, value = p.get_ionice()
                self.assertEqual(ioclass, 2)
                self.assertEqual(value, 7)
                self.assertRaises(ValueError, p.set_ionice, 2, 10)
            finally:
                p.set_ionice(IOPRIO_CLASS_NONE)
        else:
            p = psutil.Process(os.getpid())
            original = p.get_ionice()
            try:
                value = 0  # very low
                if original == value:
                    value = 1  # low
                p.set_ionice(value)
                self.assertEqual(p.get_ionice(), value)
            finally:
                p.set_ionice(original)
            #
            self.assertRaises(ValueError, p.set_ionice, 3)
            self.assertRaises(TypeError, p.set_ionice, 2, 1)

    def test_get_num_threads(self):
        # on certain platforms such as Linux we might test for exact
        # thread number, since we always have with 1 thread per process,
        # but this does not apply across all platforms (OSX, Windows)
        p = psutil.Process(os.getpid())
        step1 = p.get_num_threads()

        thread = ThreadTask()
        thread.start()
        try:
            step2 = p.get_num_threads()
            self.assertEqual(step2, step1 + 1)
            thread.stop()
        finally:
            if thread._running:
                thread.stop()

    @skipUnless(WINDOWS)
    def test_get_num_handles(self):
        # a better test is done later into test/_windows.py
        p = psutil.Process(os.getpid())
        assert p.get_num_handles() > 0

    def test_get_threads(self):
        p = psutil.Process(os.getpid())
        step1 = p.get_threads()

        thread = ThreadTask()
        thread.start()

        try:
            step2 = p.get_threads()
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

    def test_get_memory_info(self):
        p = psutil.Process(os.getpid())

        # step 1 - get a base value to compare our results
        rss1, vms1 = p.get_memory_info()
        percent1 = p.get_memory_percent()
        assert rss1 > 0
        assert vms1 > 0

        # step 2 - allocate some memory
        memarr = [None] * 1500000

        rss2, vms2 = p.get_memory_info()
        percent2 = p.get_memory_percent()
        # make sure that the memory usage bumped up
        assert rss2 > rss1
        assert vms2 >= vms1  # vms might be equal
        assert percent2 > percent1
        del memarr

#    def test_get_ext_memory_info(self):
#       # tested later in fetch all test suite

    def test_get_memory_maps(self):
        p = psutil.Process(os.getpid())
        maps = p.get_memory_maps()
        paths = [x for x in maps]
        self.assertEqual(len(paths), len(set(paths)))
        ext_maps = p.get_memory_maps(grouped=False)

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
                    assert isinstance(value, (int, long))
                    assert value >= 0, value

    def test_get_memory_percent(self):
        p = psutil.Process(os.getpid())
        assert p.get_memory_percent() > 0.0

    def test_pid(self):
        sproc = get_test_subprocess()
        self.assertEqual(psutil.Process(sproc.pid).pid, sproc.pid)

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
        exe = psutil.Process(sproc.pid).exe
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
        sproc = get_test_subprocess([PYTHON, "-E"], wait=True)
        self.assertEqual(psutil.Process(sproc.pid).cmdline, [PYTHON, "-E"])

    def test_name(self):
        sproc = get_test_subprocess(PYTHON, wait=True)
        name = psutil.Process(sproc.pid).name.lower()
        pyexe = os.path.basename(os.path.realpath(sys.executable)).lower()
        assert pyexe.startswith(name), (pyexe, name)

    if os.name == 'posix':

        def test_uids(self):
            p = psutil.Process(os.getpid())
            real, effective, saved = p.uids
            # os.getuid() refers to "real" uid
            self.assertEqual(real, os.getuid())
            # os.geteuid() refers to "effective" uid
            self.assertEqual(effective, os.geteuid())
            # no such thing as os.getsuid() ("saved" uid), but starting
            # from python 2.7 we have os.getresuid()[2]
            if hasattr(os, "getresuid"):
                self.assertEqual(saved, os.getresuid()[2])

        def test_gids(self):
            p = psutil.Process(os.getpid())
            real, effective, saved = p.gids
            # os.getuid() refers to "real" uid
            self.assertEqual(real, os.getgid())
            # os.geteuid() refers to "effective" uid
            self.assertEqual(effective, os.getegid())
            # no such thing as os.getsuid() ("saved" uid), but starting
            # from python 2.7 we have os.getresgid()[2]
            if hasattr(os, "getresuid"):
                self.assertEqual(saved, os.getresgid()[2])

        def test_nice(self):
            p = psutil.Process(os.getpid())
            self.assertRaises(TypeError, p.set_nice, "str")
            try:
                try:
                    first_nice = p.get_nice()
                    p.set_nice(1)
                    self.assertEqual(p.get_nice(), 1)
                    # going back to previous nice value raises AccessDenied on OSX
                    if not OSX:
                        p.set_nice(0)
                        self.assertEqual(p.get_nice(), 0)
                except psutil.AccessDenied:
                    pass
            finally:
                try:
                    p.set_nice(first_nice)
                except psutil.AccessDenied:
                    pass

    if os.name == 'nt':

        def test_nice(self):
            p = psutil.Process(os.getpid())
            self.assertRaises(TypeError, p.set_nice, "str")
            try:
                self.assertEqual(p.get_nice(), psutil.NORMAL_PRIORITY_CLASS)
                p.set_nice(psutil.HIGH_PRIORITY_CLASS)
                self.assertEqual(p.get_nice(), psutil.HIGH_PRIORITY_CLASS)
                p.set_nice(psutil.NORMAL_PRIORITY_CLASS)
                self.assertEqual(p.get_nice(), psutil.NORMAL_PRIORITY_CLASS)
            finally:
                p.set_nice(psutil.NORMAL_PRIORITY_CLASS)

    def test_status(self):
        p = psutil.Process(os.getpid())
        self.assertEqual(p.status, psutil.STATUS_RUNNING)
        self.assertEqual(str(p.status), "running")

    def test_status_constants(self):
        # STATUS_* constants are supposed to be comparable also by
        # using their str representation
        self.assertTrue(psutil.STATUS_RUNNING == 0)
        self.assertTrue(psutil.STATUS_RUNNING == long(0))
        self.assertTrue(psutil.STATUS_RUNNING == 'running')
        self.assertFalse(psutil.STATUS_RUNNING == 1)
        self.assertFalse(psutil.STATUS_RUNNING == 'sleeping')
        self.assertFalse(psutil.STATUS_RUNNING != 0)
        self.assertFalse(psutil.STATUS_RUNNING != 'running')
        self.assertTrue(psutil.STATUS_RUNNING != 1)
        self.assertTrue(psutil.STATUS_RUNNING != 'sleeping')

    def test_username(self):
        sproc = get_test_subprocess()
        p = psutil.Process(sproc.pid)
        if POSIX:
            import pwd
            self.assertEqual(p.username, pwd.getpwuid(os.getuid()).pw_name)
        elif WINDOWS:
            expected_username = os.environ['USERNAME']
            expected_domain = os.environ['USERDOMAIN']
            domain, username = p.username.split('\\')
            self.assertEqual(domain, expected_domain)
            self.assertEqual(username, expected_username)
        else:
            p.username

    @skipIf(not hasattr(psutil.Process, "getcwd"))
    def test_getcwd(self):
        sproc = get_test_subprocess(wait=True)
        p = psutil.Process(sproc.pid)
        self.assertEqual(p.getcwd(), os.getcwd())

    @skipIf(not hasattr(psutil.Process, "getcwd"))
    def test_getcwd_2(self):
        cmd = [PYTHON, "-c", "import os, time; os.chdir('..'); time.sleep(10)"]
        sproc = get_test_subprocess(cmd, wait=True)
        p = psutil.Process(sproc.pid)
        call_until(p.getcwd, "ret == os.path.dirname(os.getcwd())", timeout=1)

    @skipIf(not hasattr(psutil.Process, "get_cpu_affinity"))
    def test_cpu_affinity(self):
        p = psutil.Process(os.getpid())
        initial = p.get_cpu_affinity()
        all_cpus = list(range(len(psutil.cpu_percent(percpu=True))))
        #
        for n in all_cpus:
            p.set_cpu_affinity([n])
            self.assertEqual(p.get_cpu_affinity(), [n])
        #
        p.set_cpu_affinity(all_cpus)
        self.assertEqual(p.get_cpu_affinity(), all_cpus)
        #
        p.set_cpu_affinity(initial)
        invalid_cpu = [len(psutil.cpu_times(percpu=True)) + 10]
        self.assertRaises(ValueError, p.set_cpu_affinity, invalid_cpu)

    def test_get_open_files(self):
        # current process
        p = psutil.Process(os.getpid())
        files = p.get_open_files()
        self.assertFalse(TESTFN in files)
        f = open(TESTFN, 'w')
        call_until(p.get_open_files, "len(ret) != %i" % len(files))
        filenames = [x.path for x in p.get_open_files()]
        self.assertIn(TESTFN, filenames)
        f.close()
        for file in filenames:
            assert os.path.isfile(file), file

        # another process
        cmdline = "import time; f = open(r'%s', 'r'); time.sleep(100);" % TESTFN
        sproc = get_test_subprocess([PYTHON, "-c", cmdline], wait=True)
        p = psutil.Process(sproc.pid)
        for x in range(100):
            filenames = [x.path for x in p.get_open_files()]
            if TESTFN in filenames:
                break
            time.sleep(.01)
        else:
            self.assertIn(TESTFN, filenames)
        for file in filenames:
            assert os.path.isfile(file), file

    def test_get_open_files2(self):
        # test fd and path fields
        fileobj = open(TESTFN, 'w')
        p = psutil.Process(os.getpid())
        for path, fd in p.get_open_files():
            if path == fileobj.name or fd == fileobj.fileno():
                break
        else:
            self.fail("no file found; files=%s" % repr(p.get_open_files()))
        self.assertEqual(path, fileobj.name)
        if WINDOWS:
            self.assertEqual(fd, -1)
        else:
            self.assertEqual(fd, fileobj.fileno())
        # test positions
        ntuple = p.get_open_files()[0]
        self.assertEqual(ntuple[0], ntuple.path)
        self.assertEqual(ntuple[1], ntuple.fd)
        # test file is gone
        fileobj.close()
        self.assertTrue(fileobj.name not in p.get_open_files())

    def test_get_connections(self):
        arg = "import socket, time;" \
              "s = socket.socket();" \
              "s.bind(('127.0.0.1', 0));" \
              "s.listen(1);" \
              "conn, addr = s.accept();" \
              "time.sleep(100);"
        sproc = get_test_subprocess([PYTHON, "-c", arg])
        p = psutil.Process(sproc.pid)
        for x in range(100):
            cons = p.get_connections()
            if cons:
                break
            time.sleep(.01)
        self.assertEqual(len(cons), 1)
        con = cons[0]
        self.assertEqual(con.family, socket.AF_INET)
        self.assertEqual(con.type, socket.SOCK_STREAM)
        self.assertEqual(con.status, "LISTEN")
        ip, port = con.local_address
        self.assertEqual(ip, '127.0.0.1')
        self.assertEqual(con.remote_address, ())
        if WINDOWS:
            self.assertEqual(con.fd, -1)
        else:
            assert con.fd > 0, con
        # test positions
        self.assertEqual(con[0], con.fd)
        self.assertEqual(con[1], con.family)
        self.assertEqual(con[2], con.type)
        self.assertEqual(con[3], con.local_address)
        self.assertEqual(con[4], con.remote_address)
        self.assertEqual(con[5], con.status)
        # test kind arg
        self.assertRaises(ValueError, p.get_connections, 'foo')

    @skipUnless(supports_ipv6())
    def test_get_connections_ipv6(self):
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.bind(('::1', 0))
        s.listen(1)
        cons = psutil.Process(os.getpid()).get_connections()
        s.close()
        self.assertEqual(len(cons), 1)
        self.assertEqual(cons[0].local_address[0], '::1')

    @skipUnless(hasattr(socket, 'AF_UNIX'))
    def test_get_connections_unix(self):
        # tcp
        safe_remove(TESTFN)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(TESTFN)
        conn = psutil.Process(os.getpid()).get_connections(kind='unix')[0]
        self.assertEqual(conn.fd, sock.fileno())
        self.assertEqual(conn.family, socket.AF_UNIX)
        self.assertEqual(conn.type, socket.SOCK_STREAM)
        self.assertEqual(conn.local_address, TESTFN)
        self.assertTrue(not conn.remote_address)
        self.assertTrue(not conn.status)
        sock.close()
        # udp
        safe_remove(TESTFN)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        sock.bind(TESTFN)
        conn = psutil.Process(os.getpid()).get_connections(kind='unix')[0]
        self.assertEqual(conn.type, socket.SOCK_DGRAM)
        sock.close()

    @skipUnless(hasattr(socket, "fromfd") and not WINDOWS)
    def test_connection_fromfd(self):
        sock = socket.socket()
        sock.bind(('localhost', 0))
        sock.listen(1)
        p = psutil.Process(os.getpid())
        for conn in p.get_connections():
            if conn.fd == sock.fileno():
                break
        else:
            sock.close()
            self.fail("couldn't find socket fd")
        dupsock = socket.fromfd(conn.fd, conn.family, conn.type)
        try:
            self.assertEqual(dupsock.getsockname(), conn.local_address)
            self.assertNotEqual(sock.fileno(), dupsock.fileno())
        finally:
            sock.close()
            dupsock.close()

    def test_get_connections_all(self):
        tcp_template = "import socket;" \
                       "s = socket.socket($family, socket.SOCK_STREAM);" \
                       "s.bind(('$addr', 0));" \
                       "s.listen(1);" \
                       "conn, addr = s.accept();"

        udp_template = "import socket, time;" \
                       "s = socket.socket($family, socket.SOCK_DGRAM);" \
                       "s.bind(('$addr', 0));" \
                       "time.sleep(100);"

        from string import Template
        tcp4_template = Template(tcp_template).substitute(family=socket.AF_INET,
                                                          addr="127.0.0.1")
        udp4_template = Template(udp_template).substitute(family=socket.AF_INET,
                                                          addr="127.0.0.1")
        tcp6_template = Template(tcp_template).substitute(family=socket.AF_INET6,
                                                          addr="::1")
        udp6_template = Template(udp_template).substitute(family=socket.AF_INET6,
                                                          addr="::1")

        # launch various subprocess instantiating a socket of various
        # families and types to enrich psutil results
        tcp4_proc = get_test_subprocess([PYTHON, "-c", tcp4_template])
        udp4_proc = get_test_subprocess([PYTHON, "-c", udp4_template])
        if supports_ipv6():
            tcp6_proc = get_test_subprocess([PYTHON, "-c", tcp6_template])
            udp6_proc = get_test_subprocess([PYTHON, "-c", udp6_template])
        else:
            tcp6_proc = None
            udp6_proc = None

        # check matches against subprocesses just created
        all_kinds = ("all", "inet", "inet4", "inet6", "tcp", "tcp4", "tcp6",
                     "udp", "udp4", "udp6")
        for p in psutil.Process(os.getpid()).get_children():
            for conn in p.get_connections():
                # TCP v4
                if p.pid == tcp4_proc.pid:
                    self.assertEqual(conn.family, socket.AF_INET)
                    self.assertEqual(conn.type, socket.SOCK_STREAM)
                    self.assertEqual(conn.local_address[0], "127.0.0.1")
                    self.assertEqual(conn.remote_address, ())
                    self.assertEqual(conn.status, "LISTEN")
                    for kind in all_kinds:
                        cons = p.get_connections(kind=kind)
                        if kind in ("all", "inet", "inet4", "tcp", "tcp4"):
                            assert cons != [], cons
                        else:
                            self.assertEqual(cons, [], cons)
                # UDP v4
                elif p.pid == udp4_proc.pid:
                    self.assertEqual(conn.family, socket.AF_INET)
                    self.assertEqual(conn.type, socket.SOCK_DGRAM)
                    self.assertEqual(conn.local_address[0], "127.0.0.1")
                    self.assertEqual(conn.remote_address, ())
                    self.assertEqual(conn.status, "")
                    for kind in all_kinds:
                        cons = p.get_connections(kind=kind)
                        if kind in ("all", "inet", "inet4", "udp", "udp4"):
                            assert cons != [], cons
                        else:
                            self.assertEqual(cons, [], cons)
                # TCP v6
                elif p.pid == getattr(tcp6_proc, "pid", None):
                    self.assertEqual(conn.family, socket.AF_INET6)
                    self.assertEqual(conn.type, socket.SOCK_STREAM)
                    self.assertIn(conn.local_address[0], ("::", "::1"))
                    self.assertEqual(conn.remote_address, ())
                    self.assertEqual(conn.status, "LISTEN")
                    for kind in all_kinds:
                        cons = p.get_connections(kind=kind)
                        if kind in ("all", "inet", "inet6", "tcp", "tcp6"):
                            assert cons != [], cons
                        else:
                            self.assertEqual(cons, [], cons)
                # UDP v6
                elif p.pid == getattr(udp6_proc, "pid", None):
                    self.assertEqual(conn.family, socket.AF_INET6)
                    self.assertEqual(conn.type, socket.SOCK_DGRAM)
                    self.assertIn(conn.local_address[0], ("::", "::1"))
                    self.assertEqual(conn.remote_address, ())
                    self.assertEqual(conn.status, "")
                    for kind in all_kinds:
                        cons = p.get_connections(kind=kind)
                        if kind in ("all", "inet", "inet6", "udp", "udp6"):
                            assert cons != [], cons
                        else:
                            self.assertEqual(cons, [], cons)

    @skipUnless(POSIX)
    def test_get_num_fds(self):
        p = psutil.Process(os.getpid())
        start = p.get_num_fds()
        file = open(TESTFN, 'w')
        self.assertEqual(p.get_num_fds(), start + 1)
        sock = socket.socket()
        self.assertEqual(p.get_num_fds(), start + 2)
        file.close()
        sock.close()
        self.assertEqual(p.get_num_fds(), start)

    def test_get_num_ctx_switches(self):
        p = psutil.Process(os.getpid())
        before = sum(p.get_num_ctx_switches())
        for x in range(500000):
            after = sum(p.get_num_ctx_switches())
            if after > before:
                return
        self.fail("num ctx switches still the same after 50.000 iterations")

    def test_parent_ppid(self):
        this_parent = os.getpid()
        sproc = get_test_subprocess()
        p = psutil.Process(sproc.pid)
        self.assertEqual(p.ppid, this_parent)
        self.assertEqual(p.parent.pid, this_parent)
        # no other process is supposed to have us as parent
        for p in psutil.process_iter():
            if p.pid == sproc.pid:
                continue
            self.assertTrue(p.ppid != this_parent)

    def test_get_children(self):
        p = psutil.Process(os.getpid())
        self.assertEqual(p.get_children(), [])
        self.assertEqual(p.get_children(recursive=True), [])
        sproc = get_test_subprocess()
        children1 = p.get_children()
        children2 = p.get_children(recursive=True)
        for children in (children1, children2):
            self.assertEqual(len(children), 1)
            self.assertEqual(children[0].pid, sproc.pid)
            self.assertEqual(children[0].ppid, os.getpid())

    def test_get_children_recursive(self):
        # here we create a subprocess which creates another one as in:
        # A (parent) -> B (child) -> C (grandchild)
        s =  "import subprocess, os, sys, time;"
        s += "PYTHON = os.path.realpath(sys.executable);"
        s += "cmd = [PYTHON, '-c', 'import time; time.sleep(3600);'];"
        s += "subprocess.Popen(cmd);"
        s += "time.sleep(3600);"
        get_test_subprocess(cmd=[PYTHON, "-c", s])
        p = psutil.Process(os.getpid())
        self.assertEqual(len(p.get_children(recursive=False)), 1)
        # give the grandchild some time to start
        stop_at = time.time() + 1.5
        while time.time() < stop_at:
            children = p.get_children(recursive=True)
            if len(children) > 1:
                break
        self.assertEqual(len(children), 2)
        self.assertEqual(children[0].ppid, os.getpid())
        self.assertEqual(children[1].ppid, children[0].pid)

    def test_get_children_duplicates(self):
        # find the process which has the highest number of children
        from psutil._compat import defaultdict
        table = defaultdict(int)
        for p in psutil.process_iter():
            try:
                table[p.ppid] += 1
            except psutil.Error:
                pass
        # this is the one, now let's make sure there are no duplicates
        pid = sorted(table.items(), key=lambda x: x[1])[-1][0]
        p = psutil.Process(pid)
        try:
            c = p.get_children(recursive=True)
        except psutil.AccessDenied:  # windows
            pass
        else:
            self.assertEqual(len(c), len(set(c)))

    def test_suspend_resume(self):
        sproc = get_test_subprocess(wait=True)
        p = psutil.Process(sproc.pid)
        p.suspend()
        for x in range(100):
            if p.status == psutil.STATUS_STOPPED:
                break
            time.sleep(0.01)
        self.assertEqual(str(p.status), "stopped")
        p.resume()
        assert p.status != psutil.STATUS_STOPPED, p.status

    def test_invalid_pid(self):
        self.assertRaises(TypeError, psutil.Process, "1")
        self.assertRaises(TypeError, psutil.Process, None)
        self.assertRaises(ValueError, psutil.Process, -1)

    def test_as_dict(self):
        sproc = get_test_subprocess()
        p = psutil.Process(sproc.pid)
        d = p.as_dict()
        try:
            import json
        except ImportError:
            pass
        else:
            # dict is supposed to be hashable
            json.dumps(d)
        #
        d = p.as_dict(attrs=['exe', 'name'])
        self.assertEqual(sorted(d.keys()), ['exe', 'name'])
        #
        p = psutil.Process(min(psutil.get_pid_list()))
        d = p.as_dict(attrs=['get_connections'], ad_value='foo')
        if not isinstance(d['connections'], list):
            self.assertEqual(d['connections'], 'foo')

    def test_zombie_process(self):
        # Test that NoSuchProcess exception gets raised in case the
        # process dies after we create the Process object.
        # Example:
        #  >>> proc = Process(1234)
        #  >>> time.sleep(5)  # time-consuming task, process dies in meantime
        #  >>> proc.name
        # Refers to Issue #15
        sproc = get_test_subprocess()
        p = psutil.Process(sproc.pid)
        p.kill()
        p.wait()

        for name in dir(p):
            if name.startswith('_')\
            or name in ('pid', 'send_signal', 'is_running', 'set_ionice',
                        'wait', 'set_cpu_affinity', 'create_time', 'set_nice',
                        'nice'):
                continue
            try:
                meth = getattr(p, name)
                if callable(meth):
                    meth()
            except psutil.NoSuchProcess:
                pass
            else:
                self.fail("NoSuchProcess exception not raised for %r" % name)

        # other methods
        try:
            if os.name == 'posix':
                p.set_nice(1)
            else:
                p.set_nice(psutil.NORMAL_PRIORITY_CLASS)
        except psutil.NoSuchProcess:
            pass
        else:
            self.fail("exception not raised")
        if hasattr(p, 'set_ionice'):
            self.assertRaises(psutil.NoSuchProcess, p.set_ionice, 2)
        self.assertRaises(psutil.NoSuchProcess, p.send_signal, signal.SIGTERM)
        self.assertRaises(psutil.NoSuchProcess, p.set_nice, 0)
        self.assertFalse(p.is_running())
        if hasattr(p, "set_cpu_affinity"):
            self.assertRaises(psutil.NoSuchProcess, p.set_cpu_affinity, [0])

    def test__str__(self):
        sproc = get_test_subprocess()
        p = psutil.Process(sproc.pid)
        self.assertIn(str(sproc.pid), str(p))
        # python shows up as 'Python' in cmdline on OS X so test fails on OS X
        if not OSX:
            self.assertIn(os.path.basename(PYTHON), str(p))
        sproc = get_test_subprocess()
        p = psutil.Process(sproc.pid)
        p.kill()
        p.wait()
        self.assertIn(str(sproc.pid), str(p))
        self.assertIn("terminated", str(p))

    @skipIf(LINUX)
    def test_pid_0(self):
        # Process(0) is supposed to work on all platforms except Linux
        p = psutil.Process(0)
        self.assertTrue(p.name)

        if os.name == 'posix':
            self.assertEqual(p.uids.real, 0)
            self.assertEqual(p.gids.real, 0)

        self.assertIn(p.ppid, (0, 1))
        #self.assertEqual(p.exe, "")
        self.assertEqual(p.cmdline, [])
        try:
            p.get_num_threads()
        except psutil.AccessDenied:
            pass

        try:
            p.get_memory_info()
        except psutil.AccessDenied:
            pass

        # username property
        if POSIX:
            self.assertEqual(p.username, 'root')
        elif WINDOWS:
            self.assertEqual(p.username, 'NT AUTHORITY\\SYSTEM')
        else:
            p.username

        self.assertIn(0, psutil.get_pid_list())
        self.assertTrue(psutil.pid_exists(0))

    def test__all__(self):
        for name in dir(psutil):
            if name in ('callable', 'defaultdict', 'error', 'namedtuple'):
                continue
            if not name.startswith('_'):
                try:
                    __import__(name)
                except ImportError:
                    if name not in psutil.__all__:
                        fun = getattr(psutil, name)
                        if fun is None:
                            continue
                        if 'deprecated' not in fun.__doc__.lower():
                            self.fail('%r not in psutil.__all__' % name)

    def test_Popen(self):
        # Popen class test
        # XXX this test causes a ResourceWarning on Python 3 because
        # psutil.__subproc instance doesn't get propertly freed.
        # Not sure what to do though.
        cmd = [PYTHON, "-c", "import time; time.sleep(3600);"]
        proc = psutil.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            proc.name
            proc.stdin
            self.assertTrue(hasattr(proc, 'name'))
            self.assertTrue(hasattr(proc, 'stdin'))
            self.assertRaises(AttributeError, getattr, proc, 'foo')
        finally:
            proc.kill()
            proc.wait()


class TestFetchAllProcesses(unittest.TestCase):
    # Iterates over all running processes and performs some sanity
    # checks against Process API's returned values.

    # Python 2.4 compatibility
    if not hasattr(unittest.TestCase, "assertIn"):
        def assertIn(self, member, container, msg=None):
            if member not in container:
                self.fail(msg or \
                        '%s not found in %s' % (repr(member), repr(container)))

    def setUp(self):
        if POSIX:
            import pwd
            pall = pwd.getpwall()
            self._uids = set([x.pw_uid for x in pall])
            self._usernames = set([x.pw_name for x in pall])

    def test_fetch_all(self):
        valid_procs = 0
        excluded_names = ['send_signal', 'suspend', 'resume', 'terminate',
                          'kill', 'wait', 'as_dict', 'get_cpu_percent', 'nice',
                          'parent', 'get_children', 'pid']
        attrs = []
        for name in dir(psutil.Process):
            if name.startswith("_"):
                continue
            if name.startswith("set_"):
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
                        attr = getattr(p, name, None)
                        if attr is not None and callable(attr):
                            ret = attr()
                        else:
                            ret = attr
                        valid_procs += 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        err = sys.exc_info()[1]
                        if isinstance(err, psutil.NoSuchProcess):
                            if psutil.pid_exists(p.pid):
                                # XXX race condition; we probably need
                                # to try figuring out the process
                                # identity before failing
                                self.fail("PID still exists but fun raised " \
                                          "NoSuchProcess")
                        self.assertEqual(err.pid, p.pid)
                        if err.name:
                            # make sure exception's name attr is set
                            # with the actual process name
                            self.assertEqual(err.name, p.name)
                        self.assertTrue(str(err))
                        self.assertTrue(err.msg)
                    else:
                        if ret not in (0, 0.0, [], None, ''):
                            assert ret, ret
                        meth = getattr(self, name)
                        meth(ret)
                except Exception:
                    err = sys.exc_info()[1]
                    s = '\n' + '=' * 70 + '\n'
                    s += "FAIL: test_%s (proc=%s" % (name, p)
                    if ret != default:
                        s += ", ret=%s)" % repr(ret)
                    s += ')\n'
                    s += '-' * 70
                    s += "\n%s" % traceback.format_exc()
                    s =  "\n".join((" " * 4) + i for i in s.splitlines())
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
            assert ret == ''
        else:
            assert os.path.isabs(ret), ret
            # Note: os.stat() may return False even if the file is there
            # hence we skip the test, see:
            # http://stackoverflow.com/questions/3112546/os-path-exists-lies
            if POSIX:
                assert os.path.isfile(ret), ret
                if hasattr(os, 'access') and hasattr(os, "X_OK"):
                    # XXX may fail on OSX
                    self.assertTrue(os.access(ret, os.X_OK))

    def ppid(self, ret):
        self.assertTrue(ret >= 0)

    def name(self, ret):
        self.assertTrue(isinstance(ret, str))
        self.assertTrue(ret)

    def create_time(self, ret):
        self.assertTrue(ret > 0)
        if not WINDOWS:
            assert ret >= psutil.BOOT_TIME, (ret, psutil.BOOT_TIME)
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
            #self.assertIn(uid, self.gids)

    def username(self, ret):
        self.assertTrue(ret)
        if os.name == 'posix':
            self.assertIn(ret, self._usernames)

    def status(self, ret):
        self.assertTrue(ret >= 0)
        self.assertTrue(str(ret) != '?')

    def get_io_counters(self, ret):
        for field in ret:
            if field != -1:
                self.assertTrue(field >= 0)

    def get_ionice(self, ret):
        if LINUX:
            self.assertTrue(ret.ioclass >= 0)
            self.assertTrue(ret.value >= 0)
        else:
            self.assertTrue(ret >= 0)
            self.assertIn(ret, (0, 1, 2))

    def get_num_threads(self, ret):
        self.assertTrue(ret >= 1)

    def get_threads(self, ret):
        for t in ret:
            self.assertTrue(t.id >= 0)
            self.assertTrue(t.user_time >= 0)
            self.assertTrue(t.system_time >= 0)

    def get_cpu_times(self, ret):
        self.assertTrue(ret.user >= 0)
        self.assertTrue(ret.system >= 0)

    def get_memory_info(self, ret):
        self.assertTrue(ret.rss >= 0)
        self.assertTrue(ret.vms >= 0)

    def get_ext_memory_info(self, ret):
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

    def get_open_files(self, ret):
        for f in ret:
            if WINDOWS:
                assert f.fd == -1, f
            else:
                assert isinstance(f.fd, int), f
            assert os.path.isabs(f.path), f
            assert os.path.isfile(f.path), f

    def get_num_fds(self, ret):
        self.assertTrue(ret >= 0)

    def get_connections(self, ret):
        # all values are supposed to match Linux's tcp_states.h states
        # table across all platforms.
        valid_conn_states = ["ESTABLISHED", "SYN_SENT", "SYN_RECV", "FIN_WAIT1",
                             "FIN_WAIT2", "TIME_WAIT", "CLOSE", "CLOSE_WAIT",
                             "LAST_ACK", "LISTEN", "CLOSING", ""]
        for conn in ret:
            self.assertIn(conn.type, (socket.SOCK_STREAM, socket.SOCK_DGRAM))
            self.assertIn(conn.family, (socket.AF_INET, socket.AF_INET6))
            check_ip_address(conn.local_address, conn.family)
            check_ip_address(conn.remote_address, conn.family)
            if conn.status not in valid_conn_states:
                self.fail("%s is not a valid status" %conn.status)
            # actually try to bind the local socket; ignore IPv6
            # sockets as their address might be represented as
            # an IPv4-mapped-address (e.g. "::127.0.0.1")
            # and that's rejected by bind()
            if conn.family == socket.AF_INET:
                s = socket.socket(conn.family, conn.type)
                s.bind((conn.local_address[0], 0))
                s.close()

            if not WINDOWS and hasattr(socket, 'fromfd'):
                dupsock = None
                try:
                    try:
                        dupsock = socket.fromfd(conn.fd, conn.family, conn.type)
                    except (socket.error, OSError):
                        err = sys.exc_info()[1]
                        if err.args[0] == errno.EBADF:
                            continue
                        raise
                    # python >= 2.5
                    if hasattr(dupsock, "family"):
                        self.assertEqual(dupsock.family, conn.family)
                        self.assertEqual(dupsock.type, conn.type)
                finally:
                    if dupsock is not None:
                        dupsock.close()

    def getcwd(self, ret):
        if ret is not None:  # BSD may return None
            assert os.path.isabs(ret), ret
            try:
                st = os.stat(ret)
            except OSError:
                err = sys.exc_info()[1]
                # directory has been removed in mean time
                if err.errno != errno.ENOENT:
                    raise
            else:
                self.assertTrue(stat.S_ISDIR(st.st_mode))

    def get_memory_percent(self, ret):
        assert 0 <= ret <= 100, ret

    def is_running(self, ret):
        self.assertTrue(ret)

    def get_cpu_affinity(self, ret):
        assert ret != [], ret

    def terminal(self, ret):
        if ret is not None:
            assert os.path.isabs(ret), ret
            assert os.path.exists(ret), ret

    def get_memory_maps(self, ret):
        for nt in ret:
            for fname in nt._fields:
                value = getattr(nt, fname)
                if fname == 'path':
                    if not value.startswith('['):
                        assert os.path.isabs(nt.path), nt.path
                        # commented as on Linux we might get '/foo/bar (deleted)'
                        #assert os.path.exists(nt.path), nt.path
                elif fname in ('addr', 'perms'):
                    self.assertTrue(value)
                else:
                    assert isinstance(value, (int, long))
                    assert value >= 0, value

    def get_num_handles(self, ret):
        if WINDOWS:
            assert ret >= 0
        else:
            assert ret > 0

    def get_nice(self, ret):
        if POSIX:
            assert -20 <= ret <= 20, ret
        else:
            priorities = [getattr(psutil, x) for x in dir(psutil)
                          if x.endswith('_PRIORITY_CLASS')]
            self.assertIn(ret, priorities)

    def get_num_ctx_switches(self, ret):
        self.assertTrue(ret.voluntary >= 0)
        self.assertTrue(ret.involuntary >= 0)

if hasattr(os, 'getuid'):
    class LimitedUserTestCase(TestCase):
        """Repeat the previous tests by using a limited user.
        Executed only on UNIX and only if the user who run the test script
        is root.
        """
        # the uid/gid the test suite runs under
        PROCESS_UID = os.getuid()
        PROCESS_GID = os.getgid()

        def __init__(self, *args, **kwargs):
            TestCase.__init__(self, *args, **kwargs)
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
            os.setegid(1000)
            os.seteuid(1000)
            TestCase.setUp(self)

        def tearDown(self):
            os.setegid(self.PROCESS_UID)
            os.seteuid(self.PROCESS_GID)
            TestCase.tearDown(self)

        def test_nice(self):
            try:
                psutil.Process(os.getpid()).set_nice(-1)
            except psutil.AccessDenied:
                pass
            else:
                self.fail("exception not raised")


def cleanup():
    reap_children(search_all=True)
    DEVNULL.close()
    safe_remove(TESTFN)

atexit.register(cleanup)
safe_remove(TESTFN)

def test_main():
    tests = []
    test_suite = unittest.TestSuite()
    tests.append(TestCase)
    tests.append(TestFetchAllProcesses)

    if POSIX:
        from _posix import PosixSpecificTestCase
        tests.append(PosixSpecificTestCase)

    # import the specific platform test suite
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
    tests.append(stc)

    if hasattr(os, 'getuid'):
        if os.getuid() == 0:
            tests.append(LimitedUserTestCase)
        else:
            atexit.register(warn, "Couldn't run limited user tests ("
                                  "super-user privileges are required)")

    for test_class in tests:
        test_suite.addTest(unittest.makeSuite(test_class))
    unittest.TextTestRunner(verbosity=2).run(test_suite)

if __name__ == '__main__':
    test_main()
