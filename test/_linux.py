#!/usr/bin/env python
#
# $Id$
#

import unittest
import subprocess
import sys

from test_psutil import sh
import psutil


class LinuxSpecificTestCase(unittest.TestCase):

    def test_cached_phymem(self):
        # test psutil.cached_phymem against "cached" column of free
        # command line utility
        p = subprocess.Popen("free", shell=1, stdout=subprocess.PIPE)
        output = p.communicate()[0].strip()
        if sys.version_info >= (3,):
            output = str(output, sys.stdout.encoding)
        free_cmem = int(output.split('\n')[1].split()[6])
        psutil_cmem = psutil.cached_phymem() / 1024
        self.assertEqual(free_cmem, psutil_cmem)

    def test_phymem_buffers(self):
        # test psutil.phymem_buffers against "buffers" column of free
        # command line utility
        p = subprocess.Popen("free", shell=1, stdout=subprocess.PIPE)
        output = p.communicate()[0].strip()
        if sys.version_info >= (3,):
            output = str(output, sys.stdout.encoding)
        free_cmem = int(output.split('\n')[1].split()[5])
        psutil_cmem = psutil.phymem_buffers() / 1024
        self.assertEqual(free_cmem, psutil_cmem)

    def test_disks(self):
        # test psutil.disk_usage() and psutil.disk_partitions()
        # against "df -a"
        def df(path):
            out = sh('df -B 1 "%s"' % path).strip()
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
                self.fail("psutil=%s, df=%s" % usage.free, free)
            if abs(usage.used - used) > 10 * 1024 * 1024:
                self.fail("psutil=%s, df=%s" % usage.used, used)


if __name__ == '__main__':
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(LinuxSpecificTestCase))
    unittest.TextTestRunner(verbosity=2).run(test_suite)
