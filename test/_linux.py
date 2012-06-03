#!/usr/bin/env python
#
# $Id$
#
# Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Linux specific tests.  These are implicitly run by test_psutil.py."""

from __future__ import division
import unittest
import subprocess
import sys
import time
import os

from test_psutil import sh, get_test_subprocess
from psutil._compat import PY3
import psutil


class LinuxSpecificTestCase(unittest.TestCase):

    def test_cached_phymem(self):
        # test psutil.cached_phymem against "cached" column of free
        # command line utility
        p = subprocess.Popen("free", shell=1, stdout=subprocess.PIPE)
        output = p.communicate()[0].strip()
        if PY3:
            output = str(output, sys.stdout.encoding)
        free_cmem = int(output.split('\n')[1].split()[6])
        psutil_cmem = psutil.cached_phymem() / 1024
        self.assertEqual(free_cmem, psutil_cmem)

    def test_phymem_buffers(self):
        # test psutil.phymem_buffers against "buffers" column of free
        # command line utility
        p = subprocess.Popen("free", shell=1, stdout=subprocess.PIPE)
        output = p.communicate()[0].strip()
        if PY3:
            output = str(output, sys.stdout.encoding)
        free_cmem = int(output.split('\n')[1].split()[5])
        psutil_cmem = psutil.phymem_buffers() / 1024
        self.assertEqual(free_cmem, psutil_cmem)

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

if __name__ == '__main__':
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(LinuxSpecificTestCase))
    unittest.TextTestRunner(verbosity=2).run(test_suite)
