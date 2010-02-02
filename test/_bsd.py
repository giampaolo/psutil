#!/usr/bin/env python

import unittest
import subprocess
import time

import psutil

from test_psutil import kill, ps, PYTHON, DEVNULL
from _posix import ps


def sysctl(cmdline):
    """Expects a sysctl command with an argument and parse the result
    returning only the value of interest.
    """
    p = subprocess.Popen(cmdline, shell=1, stdout=subprocess.PIPE) 
    result = p.communicate()[0].strip().split()[1]
    try:
        return int(result)
    except ValueError:
        return result


class BSDSpecificTestCase(unittest.TestCase):

    def setUp(self):
        self.pid = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL).pid

    def tearDown(self):
        kill(self.pid)

    def test_TOTAL_PHYMEM(self):
        sysctl_hwphymem = sysctl('sysctl hw.physmem')
        self.assertEqual(sysctl_hwphymem, psutil.TOTAL_PHYMEM)

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
        psutil_avail_phymem =  psutil.avail_phymem()
        difference = psutil_avail_phymem - sysctl_avail_phymem
        # on my system the difference is of 348160 bytes;
        # let's assume it is a filaure if it's higher than 0.5 mega bytes
        if difference > 512000:
            self.fail("sysctl=%s; psutil=%s; difference=%s;" %(
                      sysctl_avail_phymem, psutil_avail_phymem, difference))

    def test_process_create_time(self):
        cmdline = "ps -o lstart -p %s" %self.pid
        p = subprocess.Popen(cmdline, shell=1, stdout=subprocess.PIPE)
        output = p.communicate()[0]
        start_ps = output.replace('STARTED', '').strip()
        start_psutil = psutil.Process(self.pid).create_time
        start_psutil = time.strftime("%a %b %d %H:%M:%S %Y", 
                                     time.localtime(start_psutil))
        self.assertEqual(start_ps, start_psutil)

    def test_process_groupname(self):
        groupname_ps = ps("ps --no-headers -o rgroup -p %s" %self.pid)
        groupname_psutil = psutil.Process(self.pid).groupname
        self.assertEqual(groupname_ps, groupname_psutil)




