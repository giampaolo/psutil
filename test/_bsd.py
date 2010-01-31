#!/usr/bin/env python

import unittest
import subprocess
import time

import psutil

from test_psutil import kill, PYTHON, DEVNULL


def sh(cmd):
    p = subprocess.Popen(cmd, shell=1, stdout=subprocess.PIPE) 
    return p.communicate()[0].strip()


class BSDSpecificTestCase(unittest.TestCase):

    def setUp(self):
        self.pid = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL).pid

    def tearDown(self):
        kill(self.pid)

    def test_TOTAL_PHYMEM(self):
        p = subprocess.Popen('sysctl -a | grep hw.physmem', shell=1, stdout=subprocess.PIPE)
        out = p.stdout.read()
        value = int(out.split()[1])
        self.assertEqual(value, psutil.TOTAL_PHYMEM)

    def test_avail_phymem(self):
        # This test is not particularly precise and may fail if the OS is
        # consuming memory for other applications. 
        # We just want to test that the difference between psutil result
        # and sysctl's is not too high.
        _sum = sum((
            int(sh("sysctl vm.stats.vm.v_inactive_count").split()[1]),
            int(sh("sysctl vm.stats.vm.v_cache_count").split()[1]),
            int(sh("sysctl vm.stats.vm.v_free_count").split()[1])
            ))
        _pagesize = int(sh("sysctl hw.pagesize").split()[1])
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



