#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A test script which attempts to detect memory leaks by calling C
functions many times and compare process memory usage before and
after the calls.  It might produce false positives.
"""

import os
import gc
import unittest
import time
import socket
import threading
import types
import sys

import psutil
import psutil._common
from psutil._compat import PY3, callable, xrange
from test_psutil import *

# disable cache for Process class properties
psutil._common.cached_property.enabled = False

LOOPS = 1000
TOLERANCE = 4096


class Base(unittest.TestCase):

    proc = psutil.Process(os.getpid())

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
        if difference > TOLERANCE:
            # This doesn't necessarily mean we have a leak yet.
            # At this point we assume that after having called the
            # function so many times the memory usage is stabilized
            # and if there are no leaks it should not increase any
            # more.
            # Let's keep calling fun for 3 more seconds and fail if
            # we notice any difference.
            stop_at = time.time() + 3
            while 1:
                self.call(function, *args, **kwargs)
                if time.time() >= stop_at:
                    break
            del stop_at
            gc.collect()
            rss3 = self.get_mem()
            difference = rss3 - rss2
            if rss3 > rss2:
                self.fail("rss2=%s, rss3=%s, difference=%s" \
                          % (rss2, rss3, difference))

    def get_mem(self):
        return psutil.Process(os.getpid()).get_memory_info()[0]

    def call(self, *args, **kwargs):
        raise NotImplementedError("must be implemented in subclass")


class TestProcessObjectLeaks(Base):
    """Test leaks of Process class methods and properties"""

    def __init__(self, *args, **kwargs):
        Base.__init__(self, *args, **kwargs)
        # skip tests which are not supported by Process API
        supported_attrs = dir(psutil.Process)
        for attr in [x for x in dir(self) if x.startswith('test')]:
            if attr[5:] not in supported_attrs:
                meth = getattr(self, attr)
                name = meth.__func__.__name__.replace('test_', '')
                @unittest.skipIf(True,
                                 "%s not supported on this platform" % name)
                def test_(self):
                    pass
                setattr(self, attr, types.MethodType(test_, self))

    def setUp(self):
        gc.collect()

    def tearDown(self):
        reap_children()

    def call(self, function, *args, **kwargs):
        try:
            obj = getattr(self.proc, function)
            if callable(obj):
                obj(*args, **kwargs)
        except psutil.Error:
            pass

    def test_name(self):
        self.execute('name')

    def test_cmdline(self):
        self.execute('cmdline')

    def test_exe(self):
        self.execute('exe')

    def test_ppid(self):
        self.execute('ppid')

    def test_uids(self):
        self.execute('uids')

    def test_gids(self):
        self.execute('gids')

    def test_status(self):
        self.execute('status')

    def test_get_nice(self):
        self.execute('get_nice')

    def test_set_nice(self):
        niceness = psutil.Process(os.getpid()).get_nice()
        self.execute('set_nice', niceness)

    def test_get_io_counters(self):
        self.execute('get_io_counters')

    def test_get_ionice(self):
        self.execute('get_ionice')

    def test_set_ionice(self):
        if WINDOWS:
            value = psutil.Process(os.getpid()).get_ionice()
            self.execute('set_ionice', value)
        else:
            self.execute('set_ionice', psutil.IOPRIO_CLASS_NONE)

    def test_username(self):
        self.execute('username')

    def test_create_time(self):
        self.execute('create_time')

    def test_get_num_threads(self):
        self.execute('get_num_threads')

    def test_get_num_handles(self):
        self.execute('get_num_handles')

    def test_get_num_fds(self):
        self.execute('get_num_fds')

    def test_get_threads(self):
        self.execute('get_threads')

    def test_get_cpu_times(self):
        self.execute('get_cpu_times')

    def test_get_memory_info(self):
        self.execute('get_memory_info')

    def test_get_ext_memory_info(self):
        self.execute('get_ext_memory_info')

    def test_terminal(self):
        self.execute('terminal')

    @unittest.skipIf(POSIX, "not worth being tested on POSIX (pure python)")
    def test_resume(self):
        self.execute('resume')

    def test_getcwd(self):
        self.execute('getcwd')

    def test_get_cpu_affinity(self):
        self.execute('get_cpu_affinity')

    def test_set_cpu_affinity(self):
        affinity = psutil.Process(os.getpid()).get_cpu_affinity()
        self.execute('set_cpu_affinity', affinity)

    def test_get_open_files(self):
        safe_remove(TESTFN)  # needed after UNIX socket test has run
        f = open(TESTFN, 'w')
        try:
            self.execute('get_open_files')
        finally:
            f.close()

    # OSX implementation is unbelievably slow
    @unittest.skipIf(OSX, "OSX implementation is too slow")
    def test_get_memory_maps(self):
        self.execute('get_memory_maps')

    # Linux implementation is pure python so since it's slow we skip it
    @unittest.skipIf(LINUX, "not worth being tested on Linux (pure python)")
    def test_get_connections(self):
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
            self.execute('get_connections', kind=kind)
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
        obj = getattr(psutil, function)
        if callable(obj):
            retvalue = obj(*args, **kwargs)

    @unittest.skipIf(POSIX, "not worth being tested on POSIX (pure python)")
    def test_pid_exists(self):
        self.execute('pid_exists', os.getpid())

    def test_virtual_memory(self):
        self.execute('virtual_memory')

    # TODO: remove this skip when this gets fixed
    @unittest.skipIf(SUNOS,
                     "not worth being tested on SUNOS (uses a subprocess)")
    def test_swap_memory(self):
        self.execute('swap_memory')

    def test_cpu_times(self):
        self.execute('cpu_times')

    def test_per_cpu_times(self):
        self.execute('cpu_times', percpu=True)

    @unittest.skipIf(POSIX, "not worth being tested on POSIX (pure python)")
    def test_disk_usage(self):
        self.execute('disk_usage', '.')

    def test_disk_partitions(self):
        self.execute('disk_partitions')

    def test_net_io_counters(self):
        self.execute('net_io_counters')

    def test_disk_io_counters(self):
        self.execute('disk_io_counters')

    # XXX - on Windows this produces a false positive
    @unittest.skipIf(WINDOWS,
                     "XXX produces a false positive on Windows")
    def test_get_users(self):
        self.execute('get_users')


def test_main():
    test_suite = unittest.TestSuite()
    tests = [TestProcessObjectLeaksZombie,
             TestProcessObjectLeaks,
             TestModuleFunctionsLeaks,]
    for test in tests:
        test_suite.addTest(unittest.makeSuite(test))
    result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    return result.wasSuccessful()

if __name__ == '__main__':
    if not test_main():
        sys.exit(1)
