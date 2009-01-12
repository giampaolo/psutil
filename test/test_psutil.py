#!/usr/bin/env python
# test_psutil.py

import unittest
import os
import sys
import subprocess
import time
from test import test_support

import psutil


class TestCase(unittest.TestCase):
    
    def setUp(self):
        self.proc = None
        
    def tearDown(self):
        if self.proc is not None:
            try:
                psutil.Process(self.proc.pid).kill()
            finally:
                self.proc = None        
    
    def test_get_process_list(self):           
        pids = [x.pid for x in psutil.get_process_list()]
        if hasattr(os, 'getpid'):
            self.assertTrue(os.getpid() in pids)
        
    def test_kill(self):
        devnull = open(os.devnull, 'r+')
        proc = subprocess.Popen(sys.executable, stdout=devnull, stderr=devnull)
        psutil.Process(proc.pid).kill()
        
    def test_pid(self):
        devnull = open(os.devnull, 'r+') 
        self.proc = subprocess.Popen(sys.executable, stdout=devnull, 
                                     stderr=devnull)
        self.assertEqual(psutil.Process(self.proc.pid).pid, self.proc.pid)

    def test_path(self):
        devnull = open(os.devnull, 'r+') 
        self.proc = subprocess.Popen(sys.executable, stdout=devnull, 
                                     stderr=devnull)
        time.sleep(0.1)  # XXX: provisional, fix needed
        self.assertEqual(psutil.Process(self.proc.pid).path, sys.executable)
        
    def test_args(self):
        devnull = open(os.devnull, 'r+') 
        self.proc = subprocess.Popen(sys.executable, stdout=devnull, 
                                     stderr=devnull)
        time.sleep(0.1)  # XXX: provisional, fix needed
        self.assertEqual(psutil.Process(self.proc.pid).args, [sys.executable])

    def test_name(self):
        devnull = open(os.devnull, 'r+') 
        self.proc = subprocess.Popen(sys.executable, stdout=devnull, 
                                     stderr=devnull)
        time.sleep(0.1)  # XXX: provisional, fix needed
        self.assertEqual(psutil.Process(self.proc.pid).name, 
                         os.path.basename(sys.executable))        


def test_main():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(TestCase))
    unittest.TextTestRunner(verbosity=2).run(test_suite)
    try:
        from test.test_support import reap_children
    except ImportError:
        pass
    else:
        reap_children()

if __name__ == '__main__':
    test_main()
    
