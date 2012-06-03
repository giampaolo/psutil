#!/usr/bin/env python
#
# $Id$
#
# Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""OSX specific tests.  These are implicitly run by test_psutil.py."""

import unittest
import subprocess
import time
import sys
import os

import psutil

from psutil._compat import PY3
from test_psutil import reap_children, get_test_subprocess, sh


def sysctl(cmdline):
    """Expects a sysctl command with an argument and parse the result
    returning only the value of interest.
    """
    p = subprocess.Popen(cmdline, shell=1, stdout=subprocess.PIPE)
    result = p.communicate()[0].strip().split()[1]
    if PY3:
        result = str(result, sys.stdout.encoding)
    try:
        return int(result)
    except ValueError:
        return result


class OSXSpecificTestCase(unittest.TestCase):

    def setUp(self):
        self.pid = get_test_subprocess().pid

    def tearDown(self):
        reap_children()

    def test_TOTAL_PHYMEM(self):
        sysctl_hwphymem = sysctl('sysctl hw.memsize')
        self.assertEqual(sysctl_hwphymem, psutil.TOTAL_PHYMEM)

    def test_total_virtmem(self):
        tot1 = psutil.virtmem_usage().total
        tot2 = os.path.getsize("/var/vm/swapfile0")
        self.assertEqual(tot1, tot2)

    def test_process_create_time(self):
        cmdline = "ps -o lstart -p %s" %self.pid
        p = subprocess.Popen(cmdline, shell=1, stdout=subprocess.PIPE)
        output = p.communicate()[0]
        if PY3:
            output = str(output, sys.stdout.encoding)
        start_ps = output.replace('STARTED', '').strip()
        start_psutil = psutil.Process(self.pid).create_time
        start_psutil = time.strftime("%a %b %e %H:%M:%S %Y",
                                     time.localtime(start_psutil))
        self.assertEqual(start_ps, start_psutil)

    def test_disks(self):
        # test psutil.disk_usage() and psutil.disk_partitions()
        # against "df -a"
        def df(path):
            out = sh('df -k "%s"' % path).strip()
            lines = out.split('\n')
            lines.pop(0)
            line = lines.pop(0)
            dev, total, used, free = line.split()[:4]
            if dev == 'none':
                dev = ''
            total = int(total) * 1024
            used = int(used) * 1024
            free = int(free) * 1024
            return dev, total, used, free

        for part in psutil.disk_partitions(all=False):
            usage = psutil.disk_usage(part.mountpoint)
            dev, total, used, free = df(part.mountpoint)
            self.assertEqual(part.device, dev)
            self.assertEqual(usage.total, total)
            # 10 MB tollerance
            if abs(usage.free - free) > 10 * 1024 * 1024:
                self.fail("psutil=%s, df=%s" % usage.free, free)
            if abs(usage.used - used) > 10 * 1024 * 1024:
                self.fail("psutil=%s, df=%s" % usage.used, used)


if __name__ == '__main__':
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(OSXSpecificTestCase))
    unittest.TextTestRunner(verbosity=2).run(test_suite)
