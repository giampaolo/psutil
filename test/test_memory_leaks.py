#!/usr/bin/env python
# test_memory_leaks.oy

import os
import gc
import unittest

import psutil

LOOPS = 250


class TestCase(unittest.TestCase):

    def test_memory_leak(self):

        def execute(method):
            # step 1
            for x in xrange(LOOPS):
                p = psutil.Process(os.getpid())
                obj = getattr(p, method)
                if callable(obj):
                    retvalue = obj()
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
                    retvalue = obj()
                else:
                    retvalue = obj  # property
            del x, p, obj, retvalue
            gc.collect()
            rss2 = psutil.Process(os.getpid()).get_memory_info()[0]

            # comparison
            self.assertEqual(rss1, rss2)

        execute('create_time')
        execute('get_cpu_times')
        execute('get_cpu_percent')
        execute('get_memory_info')
        execute('get_memory_percent')
        execute('__str__')


def test_main():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(TestCase))
    unittest.TextTestRunner(verbosity=2).run(test_suite)

if __name__ == '__main__':
    test_main()