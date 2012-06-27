#!/usr/bin/env python
#
# $Id$
#
# Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""BSD specific tests.  These are implicitly run by test_psutil.py."""

import unittest
import subprocess
import time
import re
import sys

import psutil

from psutil._compat import PY3
from test_psutil import reap_children, get_test_subprocess, sh

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

def parse_sysctl_vmtotal(output):
    """Parse sysctl vm.vmtotal output returning total and free memory
    values.
    """
    line = output.split('\n')[4]  # our line of interest
    mobj = re.match(r'Virtual\s+Memory.*Total:\s+(\d+)K,\s+Active\s+(\d+)K.*', line)
    total, active = mobj.groups()
    # values are represented in kilo bytes
    total = int(total) * 1024
    active = int(active) * 1024
    free = total - active
    return total, free


class BSDSpecificTestCase(unittest.TestCase):

    def setUp(self):
        self.pid = get_test_subprocess().pid

    def tearDown(self):
        reap_children()

    def test_TOTAL_PHYMEM(self):
        sysctl_hwphymem = sysctl('sysctl hw.physmem')
        self.assertEqual(sysctl_hwphymem, psutil.TOTAL_PHYMEM)

    def test_BOOT_TIME(self):
        s = sysctl('sysctl kern.boottime')
        s = s[s.find(" sec = ") + 7:]
        s = s[:s.find(',')]
        btime = int(s)
        self.assertEqual(btime, psutil.BOOT_TIME)

    def test_avail_phymem(self):
        # This test is not particularly accurate and may fail if the OS is
        # consuming memory for other applications.
        # We just want to test that the difference between psutil result
        # and sysctl's is not too high.
        _sum = sum((sysctl("sysctl vm.stats.vm.v_inactive_count"),
                    sysctl("sysctl vm.stats.vm.v_cache_count"),
                    sysctl("sysctl vm.stats.vm.v_free_count")
                   ))
        _pagesize = sysctl("sysctl hw.pagesize")
        sysctl_avail_phymem = _sum * _pagesize
        psutil_avail_phymem =  psutil.phymem_usage().free
        difference = abs(psutil_avail_phymem - sysctl_avail_phymem)
        # On my system both sysctl and psutil report the same values.
        # Let's use a tollerance of 0.5 MB and consider the test as failed
        # if we go over it.
        if difference > (0.5 * 2**20):
            self.fail("sysctl=%s; psutil=%s; difference=%s;" %(
                      sysctl_avail_phymem, psutil_avail_phymem, difference))

    def test_total_virtmem(self):
        # This test is not particularly accurate and may fail if the OS is
        # consuming memory for other applications.
        # We just want to test that the difference between psutil result
        # and sysctl's is not too high.
        p = subprocess.Popen("sysctl vm.vmtotal", shell=1, stdout=subprocess.PIPE)
        result = p.communicate()[0].strip()
        if PY3:
            result = str(result, sys.stdout.encoding)
        sysctl_total_virtmem, _ = parse_sysctl_vmtotal(result)
        psutil_total_virtmem = psutil.virtmem_usage().total
        difference = abs(sysctl_total_virtmem - psutil_total_virtmem)

        # On my system I get a difference of 4657152 bytes, probably because
        # the system is consuming memory for this same test.
        # Assuming psutil is right, let's use a tollerance of 10 MB and consider
        # the test as failed if we go over it.
        if difference > (10 * 2**20):
            self.fail("sysctl=%s; psutil=%s; difference=%s;" %(
                       sysctl_total_virtmem, psutil_total_virtmem, difference))

    def test_avail_virtmem(self):
        # This test is not particularly accurate and may fail if the OS is
        # consuming memory for other applications.
        # We just want to test that the difference between psutil result
        # and sysctl's is not too high.
        p = subprocess.Popen("sysctl vm.vmtotal", shell=1, stdout=subprocess.PIPE)
        result = p.communicate()[0].strip()
        if PY3:
            result = str(result, sys.stdout.encoding)
        _, sysctl_avail_virtmem = parse_sysctl_vmtotal(result)
        psutil_avail_virtmem = psutil.virtmem_usage().free
        difference = abs(sysctl_avail_virtmem - psutil_avail_virtmem)
        # let's assume the test is failed if difference is > 0.5 MB
        if difference > (0.5 * 2**20):
            self.fail(difference)

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

if __name__ == '__main__':
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(BSDSpecificTestCase))
    unittest.TextTestRunner(verbosity=2).run(test_suite)
