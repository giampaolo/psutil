#!/usr/bin/env python
#
# $Id$
#
# Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
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

import psutil
from psutil._compat import PY3, callable, xrange
from test_psutil import reap_children, skipUnless, skipIf, supports_ipv6, \
                        POSIX, LINUX, WINDOWS, OSX, BSD

LOOPS = 1000
TOLERANCE = 4096


class Base(unittest.TestCase):

    def execute(self, function, *args, **kwargs):
        # step 1
        for x in xrange(LOOPS):
            self.call(function, *args, **kwargs)
        del x
        gc.collect()
        rss1 = self.get_mem()

        # step 2
        for x in xrange(LOOPS):
            self.call(function, *args, **kwargs)
        del x
        gc.collect()
        rss2 = self.get_mem()

        # comparison
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

    @staticmethod
    def get_mem():
        return psutil.Process(os.getpid()).get_memory_info()[0]

    def call(self, *args, **kwargs):
        raise NotImplementedError("must be implemented in subclass")


class TestProcessObjectLeaks(Base):
    """Test leaks of Process class methods and properties"""

    def setUp(self):
        gc.collect()

    def tearDown(self):
        reap_children()

    def call(self, function, *args, **kwargs):
        p = psutil.Process(os.getpid())
        obj = getattr(p, function)
        if callable(obj):
            obj(*args, **kwargs)

    def test_name(self):
        self.execute('name')

    def test_cmdline(self):
        self.execute('cmdline')

    def test_ppid(self):
        self.execute('ppid')

    @skipIf(WINDOWS)
    def test_uids(self):
        self.execute('uids')

    @skipIf(WINDOWS)
    def test_gids(self):
        self.execute('gids')

    def test_status(self):
        self.execute('status')

    @skipIf(POSIX)
    def test_username(self):
        self.execute('username')

    def test_create_time(self):
        self.execute('create_time')

    def test_get_num_threads(self):
        self.execute('get_num_threads')

    def test_get_threads(self):
        self.execute('get_threads')

    def test_get_cpu_times(self):
        self.execute('get_cpu_times')

    def test_get_memory_info(self):
        self.execute('get_memory_info')

    def test_is_running(self):
        self.execute('is_running')

    @skipIf(WINDOWS)
    def test_terminal(self):
        self.execute('terminal')

    @skipUnless(WINDOWS)
    def test_resume(self):
        self.execute('resume')

    @skipIf(not hasattr(psutil.Process, 'getcwd'))
    def test_getcwd(self):
        self.execute('getcwd')

    @skipUnless(WINDOWS)
    def test_getcwd(self):
        self.execute('get_num_handles')

    @skipUnless(LINUX or WINDOWS)
    def test_get_cpu_affinity(self):
        self.execute('get_cpu_affinity')

    @skipUnless(LINUX or WINDOWS)
    def test_get_cpu_affinity(self):
        affinity = psutil.Process(os.getpid()).get_cpu_affinity()
        self.execute('set_cpu_affinity', affinity)

    def test_get_open_files(self):
        self.execute('get_open_files')

    # OSX implementation is unbelievably slow
    @skipIf(OSX)
    def test_get_memory_maps(self):
        self.execute('get_memory_maps')

    # XXX - BSD still uses provisional lsof implementation
    # Linux implementation is pure python so since it's slow we skip it
    @skipIf(BSD or LINUX)
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
        try:
            self.execute('get_connections', kind='all')
        finally:
            for s in socks:
                s.close()


class TestModuleFunctionsLeaks(Base):
    """Test leaks of psutil module functions."""

    def setUp(self):
        gc.collect()

    def call(self, function, *args, **kwargs):
        obj = getattr(psutil, function)
        if callable(obj):
            retvalue = obj(*args, **kwargs)

    def test_get_pid_list(self):
        self.execute('get_pid_list')

    @skipIf(POSIX)
    def test_pid_exists(self):
        self.execute('pid_exists', os.getpid())

    def test_process_iter(self):
        self.execute('process_iter')

    def test_phymem_usage(self):
        self.execute('phymem_usage')

    def test_virtmem_usage(self):
        self.execute('virtmem_usage')

    def test_cpu_times(self):
        self.execute('cpu_times')

    def test_per_cpu_times(self):
        self.execute('cpu_times', percpu=True)

    @skipUnless(WINDOWS)
    def test_disk_usage(self):
        self.execute('disk_usage', '.')

    def test_disk_partitions(self):
        self.execute('disk_partitions')

    def test_network_io_counters(self):
        self.execute('network_io_counters')

    def test_disk_io_counters(self):
        self.execute('disk_io_counters')

    # XXX - on Windows this produces a false positive
    @skipIf(WINDOWS)
    def test_get_users(self):
        self.execute('get_users')


def test_main():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(TestProcessObjectLeaks))
    test_suite.addTest(unittest.makeSuite(TestModuleFunctionsLeaks))
    unittest.TextTestRunner(verbosity=2).run(test_suite)

if __name__ == '__main__':
    test_main()
