#!/usr/bin/env python

import unittest
import subprocess
import time

import psutil

from test_psutil import kill, PYTHON, DEVNULL


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

    def test_process_create_time(self):
        cmdline = "ps -o lstart -p %s" %self.pid
        p = subprocess.Popen(cmdline, shell=1, stdout=subprocess.PIPE)
        output = p.communicate()[0]
        start_ps = output.replace('STARTED', '').strip()
        start_psutil = psutil.Process(self.pid).create_time
        start_psutil = time.strftime("%a %b %d %H:%M:%S %Y", 
                                     time.localtime(start_psutil))
        self.assertEqual(start_ps, start_psutil)



