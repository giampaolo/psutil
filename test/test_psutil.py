#!/usr/bin/env python
# test_psutil.py

import unittest
import os
import sys
import subprocess
import time
import signal
from test import test_support

import psutil


PYTHON = os.path.realpath(sys.executable)
DEVNULL = open(os.devnull, 'r+') 


class TestCase(unittest.TestCase):
    
    def setUp(self):
        self.proc = None
        
    def tearDown(self):
        if self.proc is not None:
            try:
                if hasattr(os, 'kill'):
                    os.kill(self.proc.pid, signal.SIGKILL)
                else:
                    psutil.Process(self.proc.pid).kill()
            finally:
                self.proc = None        
    
    def test_get_process_list(self):           
        pids = [x.pid for x in psutil.get_process_list()]
        if hasattr(os, 'getpid'):
            self.assertTrue(os.getpid() in pids)
        
    def test_kill(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        psutil.Process(self.proc.pid).kill()
        self.proc = None
        
    def test_pid(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        self.assertEqual(psutil.Process(self.proc.pid).pid, self.proc.pid)

    def test_path(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        time.sleep(0.1)  # XXX: provisional, fix needed
        self.assertEqual(psutil.Process(self.proc.pid).path, os.path.dirname(PYTHON))
        
    def test_cmdline(self):
        self.proc = subprocess.Popen([PYTHON, "-E"], stdout=DEVNULL, stderr=DEVNULL)
        time.sleep(0.1)  # XXX: provisional, fix needed
        self.assertEqual(psutil.Process(self.proc.pid).cmdline, [PYTHON, "-E"])

    def test_name(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL,  stderr=DEVNULL)
        time.sleep(0.1)  # XXX: provisional, fix needed
        self.assertEqual(psutil.Process(self.proc.pid).name, os.path.basename(PYTHON))        


def test_main():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(TestCase))
    unittest.TextTestRunner(verbosity=2).run(test_suite)
    test_support.reap_children()
    DEVNULL.close()

if __name__ == '__main__':
    test_main()
    
