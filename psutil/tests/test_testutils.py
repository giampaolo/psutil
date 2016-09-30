#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Unit tests for the test utilities (oh boy!).
"""

from psutil.tests import unittest
from psutil.tests import retry
from psutil.tests import mock
from psutil.tests import run_test_module_by_name


class TestRetryDecorator(unittest.TestCase):

    @mock.patch('time.sleep')
    def test_retry_success(self, sleep):
        # Fail 3 times out of 5; make sure the decorated fun returns.

        @retry(retries=5, logfun=None)
        def foo():
            while queue:
                queue.pop()
                1 / 0
            return 1

        queue = list(range(3))
        self.assertEqual(foo(), 1)

    @mock.patch('time.sleep')
    def test_retry_failure(self, sleep):
        # Fail 6 times out of 5; th function is supposed to raise exc.

        @retry(retries=5, logfun=None)
        def foo():
            while queue:
                queue.pop()
                1 / 0
            return 1

        queue = list(range(6))
        self.assertRaises(ZeroDivisionError, foo)

    @mock.patch('time.sleep')
    def test_exception(self, sleep):

        @retry(exception=ValueError)
        def foo():
            raise TypeError

        self.assertRaises(TypeError, foo)

    @mock.patch('time.sleep')
    def test_retries_and_timeout(self, sleep):
        self.assertRaises(ValueError, retry, retries=5, timeout=1)


if __name__ == '__main__':
    run_test_module_by_name(__file__)
