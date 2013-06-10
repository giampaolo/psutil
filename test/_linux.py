#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Linux specific tests.  These are implicitly run by test_psutil.py."""

from __future__ import division
import unittest
import subprocess
import sys
import time
import os
import re

from test_psutil import *
from psutil._compat import PY3
import psutil


class LinuxSpecificTestCase(unittest.TestCase):

    @unittest.skipIf(POSIX and not hasattr(os, 'statvfs'),
            reason="os.statvfs() function not available on this platform")
    @skip_on_not_implemented()
    def test_disks(self):
        # test psutil.disk_usage() and psutil.disk_partitions()
        # against "df -a"
        def df(path):
            out = sh('df -P -B 1 "%s"' % path).strip()
            lines = out.split('\n')
            lines.pop(0)
            line = lines.pop(0)
            dev, total, used, free = line.split()[:4]
            if dev == 'none':
                dev = ''
            total, used, free = int(total), int(used), int(free)
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
        sproc = get_test_subprocess()
        time.sleep(1)
        p = psutil.Process(sproc.pid)
        maps = p.get_memory_maps(grouped=False)
        pmap = sh('pmap -x %s' % p.pid).split('\n')
        del pmap[0]; del pmap[0]  # get rid of header
        while maps and pmap:
            this = maps.pop(0)
            other = pmap.pop(0)
            addr, _, rss, dirty, mode, path = other.split(None, 5)
            if not path.startswith('[') and not path.endswith(']'):
                self.assertEqual(path, os.path.basename(this.path))
            self.assertEqual(int(rss) * 1024, this.rss)
            # test only rwx chars, ignore 's' and 'p'
            self.assertEqual(mode[:3], this.perms[:3])

    def test_vmem_total(self):
        lines = sh('free').split('\n')[1:]
        total = int(lines[0].split()[1]) * 1024
        self.assertEqual(total, psutil.virtual_memory().total)

    @retry_before_failing()
    def test_vmem_used(self):
        lines = sh('free').split('\n')[1:]
        used = int(lines[0].split()[2]) * 1024
        self.assertAlmostEqual(used, psutil.virtual_memory().used,
                               delta=TOLERANCE)

    @retry_before_failing()
    def test_vmem_free(self):
        lines = sh('free').split('\n')[1:]
        free = int(lines[0].split()[3]) * 1024
        self.assertAlmostEqual(free, psutil.virtual_memory().free,
                               delta=TOLERANCE)

    @retry_before_failing()
    def test_vmem_buffers(self):
        lines = sh('free').split('\n')[1:]
        buffers = int(lines[0].split()[5]) * 1024
        self.assertAlmostEqual(buffers, psutil.virtual_memory().buffers,
                               delta=TOLERANCE)

    @retry_before_failing()
    def test_vmem_cached(self):
        lines = sh('free').split('\n')[1:]
        cached = int(lines[0].split()[6]) * 1024
        self.assertAlmostEqual(cached, psutil.virtual_memory().cached,
                               delta=TOLERANCE)

    def test_swapmem_total(self):
        lines = sh('free').split('\n')[1:]
        total = int(lines[2].split()[1]) * 1024
        self.assertEqual(total, psutil.swap_memory().total)

    @retry_before_failing()
    def test_swapmem_used(self):
        lines = sh('free').split('\n')[1:]
        used = int(lines[2].split()[2]) * 1024
        self.assertAlmostEqual(used, psutil.swap_memory().used,
                               delta=TOLERANCE)

    @retry_before_failing()
    def test_swapmem_free(self):
        lines = sh('free').split('\n')[1:]
        free = int(lines[2].split()[3]) * 1024
        self.assertAlmostEqual(free, psutil.swap_memory().free,
                               delta=TOLERANCE)

    def test_cpu_times(self):
        fields = psutil.cpu_times()._fields
        kernel_ver = re.findall('\d.\d.\d', os.uname()[2])[0]
        kernel_ver_info = tuple(map(int, kernel_ver.split('.')))
        # steal >= 2.6.11
        # guest >= 2.6.24
        # guest_nice >= 3.2.0
        if kernel_ver_info >= (2, 6, 11):
            self.assertIn('steal', fields)
        else:
            self.assertNotIn('steal', fields)
        if kernel_ver_info >= (2, 6, 24):
            self.assertIn('guest', fields)
        else:
            self.assertNotIn('guest', fields)
        if kernel_ver_info >= (3, 2, 0):
            self.assertIn('guest_nice', fields)
        else:
            self.assertNotIn('guest_nice', fields)


def test_main():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(LinuxSpecificTestCase))
    result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    return result.wasSuccessful()

if __name__ == '__main__':
    if not test_main():
        sys.exit(1)
