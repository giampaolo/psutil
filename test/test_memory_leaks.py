#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A test script which attempts to detect memory leaks by calling C
functions many times and compare process memory usage before and
after the calls.  It might produce false positives.
"""

import functools
import gc
import os
import socket
import sys
import threading
import time

import psutil
import psutil._common

from psutil._compat import xrange, callable
from test_psutil import (WINDOWS, POSIX, OSX, LINUX, SUNOS, BSD, TESTFN,
                         RLIMIT_SUPPORT, TRAVIS)
from test_psutil import (reap_children, supports_ipv6, safe_remove,
                         get_test_subprocess)

if sys.version_info < (2, 7):
    import unittest2 as unittest  # https://pypi.python.org/pypi/unittest2
else:
    import unittest


LOOPS = 1000
MEMORY_TOLERANCE = 4096
SKIP_PYTHON_IMPL = True


def skip_if_linux():
    return unittest.skipIf(LINUX and SKIP_PYTHON_IMPL,
                           "not worth being tested on LINUX (pure python)")


class Base(unittest.TestCase):
    proc = psutil.Process()

    def execute(self, function, *args, **kwargs):
        def call_many_times():
            for x in xrange(LOOPS - 1):
                self.call(function, *args, **kwargs)
            del x
            gc.collect()
            return self.get_mem()

        self.call(function, *args, **kwargs)
        self.assertEqual(gc.garbage, [])
        self.assertEqual(threading.active_count(), 1)

        # RSS comparison
        # step 1
        rss1 = call_many_times()
        # step 2
        rss2 = call_many_times()

        difference = rss2 - rss1
        if difference > MEMORY_TOLERANCE:
            # This doesn't necessarily mean we have a leak yet.
            # At this point we assume that after having called the
            # function so many times the memory usage is stabilized
            # and if there are no leaks it should not increase any
            # more.
            # Let's keep calling fun for 3 more seconds and fail if
            # we notice any difference.
            stop_at = time.time() + 3
            while True:
                self.call(function, *args, **kwargs)
                if time.time() >= stop_at:
                    break
            del stop_at
            gc.collect()
            rss3 = self.get_mem()
            difference = rss3 - rss2
            if rss3 > rss2:
                self.fail("rss2=%s, rss3=%s, difference=%s"
                          % (rss2, rss3, difference))

    def execute_w_exc(self, exc, function, *args, **kwargs):
        kwargs['_exc'] = exc
        self.execute(function, *args, **kwargs)

    def get_mem(self):
        return psutil.Process().memory_info()[0]

    def call(self, function, *args, **kwargs):
        raise NotImplementedError("must be implemented in subclass")


class TestProcessObjectLeaks(Base):
    """Test leaks of Process class methods and properties"""

    def setUp(self):
        gc.collect()

    def tearDown(self):
        reap_children()

    def call(self, function, *args, **kwargs):
        if callable(function):
            if '_exc' in kwargs:
                exc = kwargs.pop('_exc')
                self.assertRaises(exc, function, *args, **kwargs)
            else:
                try:
                    function(*args, **kwargs)
                except psutil.Error:
                    pass
        else:
            meth = getattr(self.proc, function)
            if '_exc' in kwargs:
                exc = kwargs.pop('_exc')
                self.assertRaises(exc, meth, *args, **kwargs)
            else:
                try:
                    meth(*args, **kwargs)
                except psutil.Error:
                    pass

    @skip_if_linux()
    def test_name(self):
        self.execute('name')

    @skip_if_linux()
    def test_cmdline(self):
        self.execute('cmdline')

    @skip_if_linux()
    def test_exe(self):
        self.execute('exe')

    @skip_if_linux()
    def test_ppid(self):
        self.execute('ppid')

    @unittest.skipUnless(POSIX, "POSIX only")
    @skip_if_linux()
    def test_uids(self):
        self.execute('uids')

    @unittest.skipUnless(POSIX, "POSIX only")
    @skip_if_linux()
    def test_gids(self):
        self.execute('gids')

    @skip_if_linux()
    def test_status(self):
        self.execute('status')

    def test_nice_get(self):
        self.execute('nice')

    def test_nice_set(self):
        niceness = psutil.Process().nice()
        self.execute('nice', niceness)

    @unittest.skipUnless(hasattr(psutil.Process, 'ionice'),
                         "Linux and Windows Vista only")
    def test_ionice_get(self):
        self.execute('ionice')

    @unittest.skipUnless(hasattr(psutil.Process, 'ionice'),
                         "Linux and Windows Vista only")
    def test_ionice_set(self):
        if WINDOWS:
            value = psutil.Process().ionice()
            self.execute('ionice', value)
        else:
            from psutil._pslinux import cext
            self.execute('ionice', psutil.IOPRIO_CLASS_NONE)
            fun = functools.partial(cext.proc_ioprio_set, os.getpid(), -1, 0)
            self.execute_w_exc(OSError, fun)

    @unittest.skipIf(OSX or SUNOS, "feature not supported on this platform")
    @skip_if_linux()
    def test_io_counters(self):
        self.execute('io_counters')

    @unittest.skipUnless(WINDOWS, "not worth being tested on posix")
    def test_username(self):
        self.execute('username')

    @skip_if_linux()
    def test_create_time(self):
        self.execute('create_time')

    @skip_if_linux()
    def test_num_threads(self):
        self.execute('num_threads')

    @unittest.skipUnless(WINDOWS, "Windows only")
    def test_num_handles(self):
        self.execute('num_handles')

    @unittest.skipUnless(POSIX, "POSIX only")
    @skip_if_linux()
    def test_num_fds(self):
        self.execute('num_fds')

    @skip_if_linux()
    def test_threads(self):
        self.execute('threads')

    @skip_if_linux()
    def test_cpu_times(self):
        self.execute('cpu_times')

    @skip_if_linux()
    def test_memory_info(self):
        self.execute('memory_info')

    @skip_if_linux()
    def test_memory_info_ex(self):
        self.execute('memory_info_ex')

    @unittest.skipUnless(POSIX, "POSIX only")
    @skip_if_linux()
    def test_terminal(self):
        self.execute('terminal')

    @unittest.skipIf(POSIX and SKIP_PYTHON_IMPL,
                     "not worth being tested on POSIX (pure python)")
    def test_resume(self):
        self.execute('resume')

    @skip_if_linux()
    def test_cwd(self):
        self.execute('cwd')

    @unittest.skipUnless(WINDOWS or LINUX or BSD,
                         "Windows or Linux or BSD only")
    def test_cpu_affinity_get(self):
        self.execute('cpu_affinity')

    @unittest.skipUnless(WINDOWS or LINUX or BSD,
                         "Windows or Linux or BSD only")
    def test_cpu_affinity_set(self):
        affinity = psutil.Process().cpu_affinity()
        self.execute('cpu_affinity', affinity)
        if not TRAVIS:
            self.execute_w_exc(ValueError, 'cpu_affinity', [-1])

    @skip_if_linux()
    def test_open_files(self):
        safe_remove(TESTFN)  # needed after UNIX socket test has run
        with open(TESTFN, 'w'):
            self.execute('open_files')

    # OSX implementation is unbelievably slow
    @unittest.skipIf(OSX, "OSX implementation is too slow")
    @skip_if_linux()
    def test_memory_maps(self):
        self.execute('memory_maps')

    @unittest.skipUnless(LINUX, "Linux only")
    @unittest.skipUnless(LINUX and RLIMIT_SUPPORT,
                         "only available on Linux >= 2.6.36")
    def test_rlimit_get(self):
        self.execute('rlimit', psutil.RLIMIT_NOFILE)

    @unittest.skipUnless(LINUX, "Linux only")
    @unittest.skipUnless(LINUX and RLIMIT_SUPPORT,
                         "only available on Linux >= 2.6.36")
    def test_rlimit_set(self):
        limit = psutil.Process().rlimit(psutil.RLIMIT_NOFILE)
        self.execute('rlimit', psutil.RLIMIT_NOFILE, limit)
        self.execute_w_exc(OSError, 'rlimit', -1)

    @skip_if_linux()
    # Windows implementation is based on a single system-wide function
    @unittest.skipIf(WINDOWS, "tested later")
    def test_connections(self):
        def create_socket(family, type):
            sock = socket.socket(family, type)
            sock.bind(('', 0))
            if type == socket.SOCK_STREAM:
                sock.listen(1)
            return sock

        socks = []
        socks.append(create_socket(socket.AF_INET, socket.SOCK_STREAM))
        socks.append(create_socket(socket.AF_INET, socket.SOCK_DGRAM))
        if supports_ipv6():
            socks.append(create_socket(socket.AF_INET6, socket.SOCK_STREAM))
            socks.append(create_socket(socket.AF_INET6, socket.SOCK_DGRAM))
        if hasattr(socket, 'AF_UNIX'):
            safe_remove(TESTFN)
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.bind(TESTFN)
            s.listen(1)
            socks.append(s)
        kind = 'all'
        # TODO: UNIX sockets are temporarily implemented by parsing
        # 'pfiles' cmd  output; we don't want that part of the code to
        # be executed.
        if SUNOS:
            kind = 'inet'
        try:
            self.execute('connections', kind=kind)
        finally:
            for s in socks:
                s.close()


p = get_test_subprocess()
DEAD_PROC = psutil.Process(p.pid)
DEAD_PROC.kill()
DEAD_PROC.wait()
del p


class TestProcessObjectLeaksZombie(TestProcessObjectLeaks):
    """Same as above but looks for leaks occurring when dealing with
    zombie processes raising NoSuchProcess exception.
    """
    proc = DEAD_PROC

    def call(self, *args, **kwargs):
        try:
            TestProcessObjectLeaks.call(self, *args, **kwargs)
        except psutil.NoSuchProcess:
            pass

    if not POSIX:
        def test_kill(self):
            self.execute('kill')

        def test_terminate(self):
            self.execute('terminate')

        def test_suspend(self):
            self.execute('suspend')

        def test_resume(self):
            self.execute('resume')

        def test_wait(self):
            self.execute('wait')


class TestModuleFunctionsLeaks(Base):
    """Test leaks of psutil module functions."""

    def setUp(self):
        gc.collect()

    def call(self, function, *args, **kwargs):
        fun = getattr(psutil, function)
        fun(*args, **kwargs)

    @skip_if_linux()
    def test_cpu_count_logical(self):
        self.execute('cpu_count', logical=True)

    @skip_if_linux()
    def test_cpu_count_physical(self):
        self.execute('cpu_count', logical=False)

    @skip_if_linux()
    def test_boot_time(self):
        self.execute('boot_time')

    @unittest.skipIf(POSIX and SKIP_PYTHON_IMPL,
                     "not worth being tested on POSIX (pure python)")
    def test_pid_exists(self):
        self.execute('pid_exists', os.getpid())

    def test_virtual_memory(self):
        self.execute('virtual_memory')

    # TODO: remove this skip when this gets fixed
    @unittest.skipIf(SUNOS,
                     "not worth being tested on SUNOS (uses a subprocess)")
    def test_swap_memory(self):
        self.execute('swap_memory')

    @skip_if_linux()
    def test_cpu_times(self):
        self.execute('cpu_times')

    @skip_if_linux()
    def test_per_cpu_times(self):
        self.execute('cpu_times', percpu=True)

    @unittest.skipIf(POSIX and SKIP_PYTHON_IMPL,
                     "not worth being tested on POSIX (pure python)")
    def test_disk_usage(self):
        self.execute('disk_usage', '.')

    def test_disk_partitions(self):
        self.execute('disk_partitions')

    @skip_if_linux()
    def test_net_io_counters(self):
        self.execute('net_io_counters')

    @unittest.skipIf(LINUX and not os.path.exists('/proc/diskstats'),
                     '/proc/diskstats not available on this Linux version')
    @skip_if_linux()
    def test_disk_io_counters(self):
        self.execute('disk_io_counters')

    # XXX - on Windows this produces a false positive
    @unittest.skipIf(WINDOWS, "XXX produces a false positive on Windows")
    def test_users(self):
        self.execute('users')

    @unittest.skipIf(LINUX,
                     "not worth being tested on Linux (pure python)")
    @unittest.skipIf(OSX and os.getuid() != 0, "need root access")
    def test_net_connections(self):
        self.execute('net_connections')

    def test_net_if_addrs(self):
        self.execute('net_if_addrs')

    @unittest.skipIf(TRAVIS, "EPERM on travis")
    def test_net_if_stats(self):
        self.execute('net_if_stats')


def main():
    test_suite = unittest.TestSuite()
    tests = [TestProcessObjectLeaksZombie,
             TestProcessObjectLeaks,
             TestModuleFunctionsLeaks]
    for test in tests:
        test_suite.addTest(unittest.makeSuite(test))
    result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    return result.wasSuccessful()

if __name__ == '__main__':
    if not main():
        sys.exit(1)
