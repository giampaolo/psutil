import unittest
import subprocess
import os
import signal

import psutil

from test_psutil import TESTFN, run_hanging_subprocess, kill


class PosixSpecificTestCase(unittest.TestCase):

    def tearDown(self):
        if not os.path.isfile(TESTFN):
            return
        f = open(TESTFN, 'r')
        pid = int(f.read())
        f.close()
        os.remove(TESTFN)
        kill(pid)

    def test_process_rss_memory(self):
        pid = run_hanging_subprocess()
        cmdline = "ps -o rss -p %s" %pid
        p = subprocess.Popen(cmdline, shell=1, stdout=subprocess.PIPE)
        p.wait()
        out = p.stdout.read()
        rss_ps = int(out.split()[1])
        rss_psutil = psutil.Process(pid).get_memory_info()[0] / 1024
        self.assertEqual(rss_ps, rss_psutil)

    def test_process_vsz_memory(self):
        pid = run_hanging_subprocess()
        cmdline = "ps -o vsz -p %s" %pid
        p = subprocess.Popen(cmdline, shell=1, stdout=subprocess.PIPE)
        p.wait()
        out = p.stdout.read()
        vsz_ps = int(out.split()[1])
        vsz_psutil = psutil.Process(pid).get_memory_info()[1] / 1024
        self.assertEqual(vsz_ps, vsz_psutil)

    def test_process_username(self):
        pid = run_hanging_subprocess()
        cmdline = "ps -o user -p %s" %pid
        p = subprocess.Popen(cmdline, shell=1, stdout=subprocess.PIPE)
        p.wait()
        out = p.stdout.read()
        username_ps = out.split()[1]
        username_psutil = psutil.Process(pid).username
        self.assertEqual(username_ps, username_psutil)


