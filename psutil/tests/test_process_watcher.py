#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for psutil.ProcessWatcher class."""

import psutil
from psutil.tests import PsutilTestCase


class TestProcessWatcher(PsutilTestCase):
    def setUp(self):
        self.pw = psutil.ProcessWatcher()

    def tearDown(self):
        self.pw.close()

    def test_it(self):
        pass
        # proc = self.spawn_testproc()
