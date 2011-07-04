#!/usr/bin/env python
#
# $Id$
#

"""
Note: this is targeted for python 2.x.
To run it under python 3.x you need to use 2to3 tool first:

$ 2to3 -w test/test_memory_leaks.py
"""


import os
import gc
import unittest

import psutil
from test_psutil import reap_children, skipUnless, skipIf, \
                        POSIX, LINUX, WINDOWS, OSX, BSD, PY3

LOOPS = 1000
TOLERANCE = 4096

if PY3:
    xrange = range


class TestProcessObjectLeaks(unittest.TestCase):
    """Test leaks of Process class methods and properties"""

    def setUp(self):
        gc.collect()

    def tearDown(self):
        reap_children()

    def execute(self, method, *args, **kwarks):
        # step 1
        p = psutil.Process(os.getpid())
        for x in xrange(LOOPS):
            obj = getattr(p, method)
            if callable(obj):
                retvalue = obj(*args, **kwarks)
            else:
                retvalue = obj  # property
        del x, p, obj, retvalue
        gc.collect()
        rss1 = psutil.Process(os.getpid()).get_memory_info()[0]

        # step 2
        p = psutil.Process(os.getpid())
        for x in xrange(LOOPS):
            obj = getattr(p, method)
            if callable(obj):
                retvalue = obj(*args, **kwarks)
            else:
                retvalue = obj  # property
        del x, p, obj, retvalue
        gc.collect()
        rss2 = psutil.Process(os.getpid()).get_memory_info()[0]

        # comparison
        difference = rss2 - rss1
        if difference > TOLERANCE:
            self.fail("rss1=%s, rss2=%s, difference=%s" %(rss1, rss2, difference))

    def test_name(self):
        self.execute('name')

    def test_cmdline(self):
        self.execute('cmdline')

    def test_ppid(self):
        self.execute('ppid')

    def test_uids(self):
        self.execute('uids')

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
        self.execute('get_num_threads')

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

    @skipUnless(WINDOWS)
    def test_getcwd(self):
        self.execute('getcwd')

    @skipUnless(WINDOWS or OSX)
    def test_get_open_files(self):
        self.execute('get_open_files')

    @skipUnless(WINDOWS or OSX)
    def test_get_connections(self):
        self.execute('get_connections')


class TestModuleFunctionsLeaks(unittest.TestCase):
    """Test leaks of psutil module functions."""

    def setUp(self):
        gc.collect()

    def execute(self, function, *args, **kwarks):
        # step 1
        for x in xrange(LOOPS):
            obj = getattr(psutil, function)
            if callable(obj):
                retvalue = obj(*args, **kwarks)
            else:
                retvalue = obj  # property
        del x, obj, retvalue
        gc.collect()
        rss1 = psutil.Process(os.getpid()).get_memory_info()[0]

        # step 2
        for x in xrange(LOOPS):
            obj = getattr(psutil, function)
            if callable(obj):
                retvalue = obj(*args, **kwarks)
            else:
                retvalue = obj  # property
        del x, obj, retvalue
        gc.collect()
        rss2 = psutil.Process(os.getpid()).get_memory_info()[0]

        # comparison
        difference = rss2 - rss1
        if difference > TOLERANCE:
            self.fail("rss1=%s, rss2=%s, difference=%s" %(rss1, rss2, difference))

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
        self.execute('per_cpu_times')

    @skipUnless(WINDOWS)
    def test_disk_usage(self):
        self.execute('disk_usage')

    def test_disk_partitions(self):
        self.execute('disk_partitions')


def test_main():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(TestProcessObjectLeaks))
    test_suite.addTest(unittest.makeSuite(TestModuleFunctionsLeaks))
    unittest.TextTestRunner(verbosity=2).run(test_suite)

if __name__ == '__main__':
    test_main()

