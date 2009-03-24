#!/usr/bin/env python
# test_memory_leaks.py

import os
import gc
import unittest

import psutil

LOOPS = 250


class TestMemoryLeaks(unittest.TestCase):

    def setUp(self):
        gc.collect()

    def execute(self, method, *args, **kwarks):
        # step 1
        for x in xrange(LOOPS):
            p = psutil.Process(os.getpid())
            obj = getattr(p, method)
            if callable(obj):
                retvalue = obj(*args, **kwarks)
            else:
                retvalue = obj  # property
        del x, p, obj, retvalue
        gc.collect()
        rss1 = psutil.Process(os.getpid()).get_memory_info()[0]

        # step 2
        for x in xrange(LOOPS):
            p = psutil.Process(os.getpid())
            obj = getattr(p, method)
            if callable(obj):
                retvalue = obj(*args, **kwarks)
            else:
                retvalue = obj  # property
        del x, p, obj, retvalue

        rss2 = psutil.Process(os.getpid()).get_memory_info()[0]

        # comparison
        self.assertEqual(rss1, rss2)

    def test_pid(self):
        self.execute('pid')

    def test__str__(self):
        # includes name, ppid, path, cmdline, uid, gid properties
        self.execute('__str__')

    def test_create_time(self):
        self.execute('create_time')

    def test_get_cpu_times(self):
        self.execute('get_cpu_times')

    def test_get_cpu_percent(self):
        self.execute('get_cpu_percent')

    def test_get_memory_info(self):
        self.execute('get_memory_info')

    def test_get_memory_percent(self):
        self.execute('get_memory_percent')

    def test_is_running(self):
        self.execute('is_running')


def test_main():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(TestMemoryLeaks))
    unittest.TextTestRunner(verbosity=2).run(test_suite)

if __name__ == '__main__':
    test_main()