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
from test_psutil import (MEMORY_TOLERANCE, OSX, sh, get_test_subprocess,
                         reap_children, retry_before_failing, unittest,
                         TRAVIS)


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


# http://code.activestate.com/recipes/578019/
def human2bytes(s):
    SYMBOLS = {
        'customary': ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'),
    }
    init = s
    num = ""
    while s and s[0:1].isdigit() or s[0:1] == '.':
        num += s[0]
        s = s[1:]
    num = float(num)
    letter = s.strip()
    for name, sset in SYMBOLS.items():
        if letter in sset:
            break
    else:
        if letter == 'k':
            sset = SYMBOLS['customary']
            letter = letter.upper()
        else:
            raise ValueError("can't interpret %r" % init)
    prefix = {sset[0]: 1}
    for i, s in enumerate(sset[1:]):
        prefix[s] = 1 << (i+1)*10
    return int(num * prefix[letter])


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

    def test_cpu_count_logical(self):
        num = sysctl("sysctl hw.logicalcpu")
        self.assertEqual(num, psutil.cpu_count(logical=True))

    def test_cpu_count_physical(self):
        num = sysctl("sysctl hw.physicalcpu")
        self.assertEqual(num, psutil.cpu_count(logical=False))

    # --- virtual mem

    def test_vmem_total(self):
        sysctl_hwphymem = sysctl('sysctl hw.memsize')
        self.assertEqual(sysctl_hwphymem, psutil.virtual_memory().total)

    @unittest.skipIf(TRAVIS, "")
    @retry_before_failing()
    def test_vmem_free(self):
        num = vm_stat("free")
        self.assertAlmostEqual(psutil.virtual_memory().free, num,
                               delta=MEMORY_TOLERANCE)

    @retry_before_failing()
    def test_vmem_active(self):
        num = vm_stat("active")
        self.assertAlmostEqual(psutil.virtual_memory().active, num,
                               delta=MEMORY_TOLERANCE)

    @retry_before_failing()
    def test_vmem_inactive(self):
        num = vm_stat("inactive")
        self.assertAlmostEqual(psutil.virtual_memory().inactive, num,
                               delta=MEMORY_TOLERANCE)

    @retry_before_failing()
    def test_vmem_wired(self):
        num = vm_stat("wired")
        self.assertAlmostEqual(psutil.virtual_memory().wired, num,
                               delta=MEMORY_TOLERANCE)

    # --- swap mem

    def test_swapmem_sin(self):
        num = vm_stat("Pageins")
        self.assertEqual(psutil.swap_memory().sin, num)

    def test_swapmem_sout(self):
        num = vm_stat("Pageouts")
        self.assertEqual(psutil.swap_memory().sout, num)

    def test_swapmem_total(self):
        out = sh('sysctl vm.swapusage')
        out = out.replace('vm.swapusage: ', '')
        total, used, free = re.findall('\d+.\d+\w', out)
        psutil_smem = psutil.swap_memory()
        self.assertEqual(psutil_smem.total, human2bytes(total))
        self.assertEqual(psutil_smem.used, human2bytes(used))
        self.assertEqual(psutil_smem.free, human2bytes(free))


def main():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(OSXSpecificTestCase))
    result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    if not main():
        sys.exit(1)
