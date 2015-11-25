#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""OpenBSD specific tests.  These are implicitly run by test_psutil.py."""

import datetime
import subprocess
import sys
import time

import psutil
from psutil._compat import PY3
from test_psutil import get_test_subprocess
from test_psutil import OPENBSD
from test_psutil import reap_children
from test_psutil import sh
from test_psutil import unittest


def sysctl(cmdline):
    """Expects a sysctl command with an argument and parse the result
    returning only the value of interest.
    """
    result = sh("sysctl " + cmdline)
    result = result[result.find("=") + 1:]
    try:
        return int(result)
    except ValueError:
        return result


@unittest.skipUnless(OPENBSD, "not an OpenBSD system")
class OpenBSDSpecificTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.pid = get_test_subprocess().pid

    @classmethod
    def tearDownClass(cls):
        reap_children()

    def test_boot_time(self):
        s = sysctl('kern.boottime')
        sys_bt = datetime.datetime.strptime(s, "%a %b %d %H:%M:%S %Y")
        psutil_bt = datetime.datetime.fromtimestamp(psutil.boot_time())
        self.assertEqual(sys_bt, psutil_bt)

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
                self.fail("psutil=%s, df=%s" % (usage.free, free))
            if abs(usage.used - used) > 10 * 1024 * 1024:
                self.fail("psutil=%s, df=%s" % (usage.used, used))

    def test_cpu_count_logical(self):
        syst = sysctl("hw.ncpu")
        self.assertEqual(psutil.cpu_count(logical=True), syst)

    def test_swap_memory(self):
        out = sh("pstat -s")
        _, total, used, free, _, _ = out.split('\n')[1].split()
        smem = psutil.swap_memory()
        self.assertEqual(smem.total, int(total) * 512)
        self.assertEqual(smem.used, int(used) * 512)
        self.assertEqual(smem.free, int(free) * 512)

    def test_virtual_memory_total(self):
        num = sysctl('hw.physmem')
        self.assertEqual(num, psutil.virtual_memory().total)


def main():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(OpenBSDSpecificTestCase))
    result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    if not main():
        sys.exit(1)
