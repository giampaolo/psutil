#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests which are meant to be run as root."""

import time
import unittest

import pytest

import psutil
from psutil.tests import PsutilTestCase


@pytest.mark.skipif(
    not all((
        hasattr(time, "clock_gettime"),
        hasattr(time, "clock_settime"),
        hasattr(time, "CLOCK_REALTIME"),
    )),
    reason="clock_(get|set)_time() not available",
)
class TestUpdatedSystemTime(PsutilTestCase):
    def setUp(self):
        self.time_updated = False
        self.time_before = time.clock_gettime(time.CLOCK_REALTIME)

    def tearDown(self):
        if self.time_updated:
            time.clock_settime(time.CLOCK_REALTIME, self.time_before)

    def update_systime(self):
        # set system time 1 hour later
        try:
            time.clock_settime(time.CLOCK_REALTIME, self.time_before + 3600)
        except PermissionError:
            # Need to use unittest since this particular file is run
            # with the unittest runner (in order to avoid installing
            # pytest for the sudo user).
            raise unittest.SkipTest("needs root")
        else:
            self.time_updated = True

    def test_boot_time(self):
        # Test that boot_time() reflects system clock updates.
        t1 = psutil.boot_time()
        self.update_systime()
        t2 = psutil.boot_time()
        assert t2 > t1
        diff = t2 - t1
        assert diff == 3600

    def test_proc_create_time(self):
        # Test that Process.create_time() reflects system clock updates.
        t1 = psutil.Process().create_time()
        self.update_systime()
        t2 = psutil.Process().create_time()
        assert t2 > t1
        diff = t2 - t1
        assert diff == 3600

    # def test_proc_ident(self):
    #     t1 = psutil.Process()._get_ident()[1]
    #     self.update_systime()
    #     t2 = psutil.Process()._get_ident()[1]
    #     if LINUX or FREEBSD:
    #         assert t1 == t2
    #     else:
    #         assert t1 != t2
