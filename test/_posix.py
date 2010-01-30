#!/usr/bin/env python

import unittest
import subprocess
import os
import signal

import psutil

from test_psutil import run_hanging_subprocess, kill


def sh(cmd):
    """Execute a shell command and return its output."""
    p = subprocess.Popen(cmd, shell=1, stdout=subprocess.PIPE)
    return p.communicate()[0]


class PosixSpecificTestCase(unittest.TestCase):
    """Compare psutil results against 'ps' command line utility."""

    def setUp(self):
        self.pid = run_hanging_subprocess()

    def tearDown(self):
        kill(self.pid)

    def test_process_rss_memory(self):
        rss_ps = sh("ps -o rss -p %s" %self.pid).split()[1]
        rss_psutil = psutil.Process(self.pid).get_memory_info()[0] / 1024
        self.assertEqual(rss_ps, str(rss_psutil))

    def test_process_vsz_memory(self):
        vsz_ps = sh("ps -o vsz -p %s" %self.pid).split()[1]
        vsz_psutil = psutil.Process(self.pid).get_memory_info()[1] / 1024
        self.assertEqual(vsz_ps, str(vsz_psutil))

    def test_process_username(self):
        username_ps = sh("ps -o user -p %s" %self.pid).split()[1]
        username_psutil = psutil.Process(self.pid).username
        self.assertEqual(username_ps, username_psutil)
