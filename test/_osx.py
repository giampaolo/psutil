#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""OSX specific tests.  These are implicitly run by test_psutil.py."""

import os
import re
import subprocess
import sys
import time

import psutil

from psutil._compat import PY3
from test_psutil import (TOLERANCE, OSX, sh, get_test_subprocess,
                         reap_children, retry_before_failing, unittest)


PAGESIZE = os.sysconf("SC_PAGE_SIZE")


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


def vm_stat(field):
    """Wrapper around 'vm_stat' cmdline utility."""
    out = sh('vm_stat')
    for line in out.split('\n'):
        if field in line:
            break
    else:
        raise ValueError("line not found")
    return int(re.search('\d+', line).group(0)) * PAGESIZE


@unittest.skipUnless(OSX, "not an OSX system")
class OSXSpecificTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.pid = get_test_subprocess().pid

    @classmethod
    def tearDownClass(cls):
        reap_children()

    def test_process_create_time(self):
        cmdline = "ps -o lstart -p %s" % self.pid
        p = subprocess.Popen(cmdline, shell=1, stdout=subprocess.PIPE)
        output = p.communicate()[0]
        if PY3:
            output = str(output, sys.stdout.encoding)
        start_ps = output.replace('STARTED', '').strip()
        start_psutil = psutil.Process(self.pid).create_time()
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

    # --- virtual mem

    def test_vmem_total(self):
        sysctl_hwphymem = sysctl('sysctl hw.memsize')
        self.assertEqual(sysctl_hwphymem, psutil.virtual_memory().total)

    @retry_before_failing()
    def test_vmem_free(self):
        num = vm_stat("free")
        self.assertAlmostEqual(psutil.virtual_memory().free, num,
                               delta=TOLERANCE)

    @retry_before_failing()
    def test_vmem_active(self):
        num = vm_stat("active")
        self.assertAlmostEqual(psutil.virtual_memory().active, num,
                               delta=TOLERANCE)

    @retry_before_failing()
    def test_vmem_inactive(self):
        num = vm_stat("inactive")
        self.assertAlmostEqual(psutil.virtual_memory().inactive, num,
                               delta=TOLERANCE)

    @retry_before_failing()
    def test_vmem_wired(self):
        num = vm_stat("wired")
        self.assertAlmostEqual(psutil.virtual_memory().wired, num,
                               delta=TOLERANCE)

    # --- swap mem

    def test_swapmem_sin(self):
        num = vm_stat("Pageins")
        self.assertEqual(psutil.swap_memory().sin, num)

    def test_swapmem_sout(self):
        num = vm_stat("Pageouts")
        self.assertEqual(psutil.swap_memory().sout, num)

    def test_swapmem_total(self):
        tot1 = psutil.swap_memory().total
        tot2 = 0
        # OSX uses multiple cache files:
        # http://en.wikipedia.org/wiki/Paging#OS_X
        for name in os.listdir("/var/vm/"):
            file = os.path.join("/var/vm", name)
            if os.path.isfile(file):
                tot2 += os.path.getsize(file)
        self.assertEqual(tot1, tot2)


def main():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(OSXSpecificTestCase))
    result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    return result.wasSuccessful()

if __name__ == '__main__':
    if not main():
        sys.exit(1)
