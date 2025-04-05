#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests which are meant to be run as root."""

import time

import pytest

import psutil
from psutil.tests import PsutilTestCase


def can_update_systime():
    t = time.clock_gettime(time.CLOCK_REALTIME)
    try:
        time.clock_settime(time.CLOCK_REALTIME, t)
    except PermissionError:
        return False
    return True


@pytest.mark.skipif(not can_update_systime(), reason="needs root")
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
        self.time_before = time.clock_gettime(time.CLOCK_REALTIME)

    def tearDown(self):
        time.clock_settime(time.CLOCK_REALTIME, self.time_before)

    def update_systime(self):
        # set system time 1 hour later
        time.clock_settime(time.CLOCK_REALTIME, self.time_before + 3600)

    def test_boot_time(self):
        bt1 = psutil.boot_time()
        self.update_systime()
        bt2 = psutil.boot_time()
        assert bt2 > bt1
        assert bt2 - bt1 == 3600
