import unittest
import subprocess

import psutil

from test_psutil import run_hanging_subprocess
from test_psutil import TestCase as BaseTestCase


class PosixSpecificTestCase(unittest.TestCase):

    def setUp(self):
        BaseTestCase.setUp()

    def tearDown(self):
        BaseTestCase.tearDown()

    def test_process_rss_memory(self):
        self.proc = run_hanging_subprocess()
        cmdline = "ps -o rss -p %s" %self.proc.pid
        p = subprocess.Popen(cmdline, shell=1, stdout=subprocess.PIPE)
        p.wait()
        out = p.stdout.read()
        rss_ps = int(out.split()[1])
        rss_psutil = psutil.Process(self.proc.pid).get_memory_info()[0] / 1024
        self.assertEqual(rss_ps, rss_psutil)

    def test_process_vsz_memory(self):
        self.proc = run_hanging_subprocess()
        cmdline = "ps -o vsz -p %s" %self.proc.pid
        p = subprocess.Popen(cmdline, shell=1, stdout=subprocess.PIPE)
        p.wait()
        out = p.stdout.read()
        vsz_ps = int(out.split()[1])
        vsz_psutil = psutil.Process(self.proc.pid).get_memory_info()[1] / 1024
        self.assertEqual(vsz_ps, vsz_psutil)

    def test_process_username(self):
        self.proc = run_hanging_subprocess()
        cmdline = "ps -o user -p %s" %self.proc.pid
        p = subprocess.Popen(cmdline, shell=1, stdout=subprocess.PIPE)
        p.wait()
        out = p.stdout.read()
        username_ps = out.split()[1]
        username_psutil = psutil.Process(self.proc.pid).username
        self.assertEqual(username_ps, username_psutil)


