#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests which are meant to be run as root.

NOTE: keep this module compatible with unittest: we want to run this
file with the unittest runner, since pytest may not be installed for
the root user.
"""

import time
import unittest

import psutil
from psutil import LINUX
from psutil import MACOS
from psutil.tests import PsutilTestCase


@unittest.skipIf(
    not all((
        hasattr(time, "clock_gettime"),
        hasattr(time, "clock_settime"),
        hasattr(time, "CLOCK_REALTIME"),
    )),
    "clock_(get|set)_time() not available",
)
class TestUpdatedSystemTime(PsutilTestCase):
    """Tests which update the system clock."""

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
            raise unittest.SkipTest("needs root")
        else:
            self.time_updated = True

    def test_boot_time(self):
        # Test that boot_time() reflects system clock updates.
        t1 = psutil.boot_time()
        self.update_systime()
        t2 = psutil.boot_time()
        self.assertGreater(t2, t1)
        diff = int(t2 - t1)
        self.assertAlmostEqual(diff, 3600, delta=1)

    @unittest.skipIf(MACOS, "broken on MACOS")  # TODO: fix it on MACOS
    def test_proc_create_time(self):
        # Test that Process.create_time() reflects system clock
        # updates. On systems such as Linux this is added on top of the
        # process monotonic time returned by the kernel.
        t1 = psutil.Process().create_time()
        self.update_systime()
        t2 = psutil.Process().create_time()
        self.assertGreater(t2, t1)
        diff = int(t2 - t1)
        self.assertAlmostEqual(diff, 3600, delta=1)

    @unittest.skipIf(not LINUX, "LINUX only")
    def test_linux_monotonic_proc_time(self):
        t1 = psutil.Process()._proc.create_time(monotonic=True)
        self.update_systime()
        t2 = psutil.Process()._proc.create_time(monotonic=True)
        self.assertEqual(t1, t2)
