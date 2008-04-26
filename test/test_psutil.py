#!/usr/bin/env python
# test_psutil.py

import psutil
import subprocess
import sys
import os
import unittest
from test import test_support


# TODO
# - avoid created processes to print on stdout


class TestCase(unittest.TestCase):
    
    def test_list_processes(self):
        psutil.list_processes()
        
    def test_kill_process(self):
        proc = subprocess.Popen(sys.executable)
        psutil.kill_process(proc.pid)
       
    def test_kill_process_by_name(self):
        # TODO - can't use sys.executable since it would kill our 
        # test suite.  What to do here?
        pass
    
    def test_process_name(self):
        proc = subprocess.Popen(sys.executable)
        # TODO - find a workaround for this
        import time
        time.sleep(0.5)
        try:
            self.assert_(os.path.basename(sys.executable),
                         psutil.get_process_name(proc.pid))
        finally:
            psutil.kill_process(proc.pid)
            
    def test_process_path(self):
        proc = subprocess.Popen(sys.executable)
        # TODO - find a workaround for this
        import time
        time.sleep(0.5)
        try:
            self.assertEqual(sys.executable, psutil.get_process_path(proc.pid))
        finally:
            psutil.kill_process(proc.pid)
       
        
if __name__ == '__main__':
    test_support.run_unittest(TestCase)
    
