#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""BSD specific tests.  These are implicitly run by test_psutil.py."""

import unittest
import subprocess
import time
import re
import sys
import os

import psutil

from psutil._compat import PY3
from test_psutil import *


PAGESIZE = os.sysconf("SC_PAGE_SIZE")
MUSE_AVAILABLE = which('muse')


def sysctl(cmdline):
    """Expects a sysctl command with an argument and parse the result
    returning only the value of interest.
    """
    result = sh("sysctl " + cmdline)
    result = result[result.find(": ") + 2:]
    try:
        return int(result)
    except ValueError:
        return result

def muse(field):
    """Thin wrapper around 'muse' cmdline utility."""
    out = sh('muse', stderr=DEVNULL)
    for line in out.split('\n'):
        if line.startswith(field):
            break
    else:
        raise ValueError("line not found")
    return int(line.split()[1])


class BSDSpecificTestCase(unittest.TestCase):

    def setUp(self):
        self.pid = get_test_subprocess().pid

    def tearDown(self):
        reap_children()

    def test_BOOT_TIME(self):
        s = sysctl('sysctl kern.boottime')
        s = s[s.find(" sec = ") + 7:]
        s = s[:s.find(',')]
        btime = int(s)
        self.assertEqual(btime, psutil.BOOT_TIME)

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
                self.fail("psutil=%s, df=%s" % (usage.free, free))
            if abs(usage.used - used) > 10 * 1024 * 1024:
                self.fail("psutil=%s, df=%s" % (usage.used, used))

    def test_memory_maps(self):
        out = sh('procstat -v %s' % self.pid)
        maps = psutil.Process(self.pid).get_memory_maps(grouped=False)
        lines = out.split('\n')[1:]
        while lines:
            line = lines.pop()
            fields = line.split()
            _, start, stop, perms, res = fields[:5]
            map = maps.pop()
            self.assertEqual("%s-%s" % (start, stop), map.addr)
            self.assertEqual(int(res), map.rss)
            if not map.path.startswith('['):
                self.assertEqual(fields[10], map.path)

    # --- virtual_memory(); tests against sysctl

    def test_vmem_total(self):
        syst = sysctl("sysctl vm.stats.vm.v_page_count") * PAGESIZE
        self.assertEqual(psutil.virtual_memory().total, syst)

    @retry_before_failing()
    def test_vmem_active(self):
        syst = sysctl("vm.stats.vm.v_active_count") * PAGESIZE
        self.assertAlmostEqual(psutil.virtual_memory().active, syst,
                               delta=TOLERANCE)

    @retry_before_failing()
    def test_vmem_inactive(self):
        syst = sysctl("vm.stats.vm.v_inactive_count") * PAGESIZE
        self.assertAlmostEqual(psutil.virtual_memory().inactive, syst,
                               delta=TOLERANCE)

    @retry_before_failing()
    def test_vmem_wired(self):
        syst = sysctl("vm.stats.vm.v_wire_count") * PAGESIZE
        self.assertAlmostEqual(psutil.virtual_memory().wired, syst,
                               delta=TOLERANCE)

    @retry_before_failing()
    def test_vmem_cached(self):
        syst = sysctl("vm.stats.vm.v_cache_count") * PAGESIZE
        self.assertAlmostEqual(psutil.virtual_memory().cached, syst,
                               delta=TOLERANCE)

    @retry_before_failing()
    def test_vmem_free(self):
        syst = sysctl("vm.stats.vm.v_free_count") * PAGESIZE
        self.assertAlmostEqual(psutil.virtual_memory().free, syst,
                               delta=TOLERANCE)

    @retry_before_failing()
    def test_vmem_buffers(self):
        syst = sysctl("vfs.bufspace")
        self.assertAlmostEqual(psutil.virtual_memory().buffers, syst,
                               delta=TOLERANCE)

    # --- virtual_memory(); tests against muse

    @unittest.skipUnless(MUSE_AVAILABLE, "muse cmdline tool is not available")
    def test_total(self):
        num = muse('Total')
        self.assertEqual(psutil.virtual_memory().total, num)

    @unittest.skipUnless(MUSE_AVAILABLE, "muse cmdline tool is not available")
    @retry_before_failing()
    def test_active(self):
        num = muse('Active')
        self.assertAlmostEqual(psutil.virtual_memory().active, num,
                               delta=TOLERANCE)

    @unittest.skipUnless(MUSE_AVAILABLE, "muse cmdline tool is not available")
    @retry_before_failing()
    def test_inactive(self):
        num = muse('Inactive')
        self.assertAlmostEqual(psutil.virtual_memory().inactive, num,
                               delta=TOLERANCE)

    @unittest.skipUnless(MUSE_AVAILABLE, "muse cmdline tool is not available")
    @retry_before_failing()
    def test_wired(self):
        num = muse('Wired')
        self.assertAlmostEqual(psutil.virtual_memory().wired, num,
                               delta=TOLERANCE)

    @unittest.skipUnless(MUSE_AVAILABLE, "muse cmdline tool is not available")
    @retry_before_failing()
    def test_cached(self):
        num = muse('Cache')
        self.assertAlmostEqual(psutil.virtual_memory().cached, num,
                               delta=TOLERANCE)

    @unittest.skipUnless(MUSE_AVAILABLE, "muse cmdline tool is not available")
    @retry_before_failing()
    def test_free(self):
        num = muse('Free')
        self.assertAlmostEqual(psutil.virtual_memory().free, num,
                               delta=TOLERANCE)

    @unittest.skipUnless(MUSE_AVAILABLE, "muse cmdline tool is not available")
    @retry_before_failing()
    def test_buffers(self):
        num = muse('Buffer')
        self.assertAlmostEqual(psutil.virtual_memory().buffers, num,
                               delta=TOLERANCE)


def test_main():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(BSDSpecificTestCase))
    result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    return result.wasSuccessful()

if __name__ == '__main__':
    if not test_main():
        sys.exit(1)
