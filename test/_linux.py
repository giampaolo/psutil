#!/usr/bin/env python

import unittest
import subprocess
import time

import psutil

from test_psutil import PYTHON, DEVNULL, kill
from _posix import ps


class LinuxSpecificTestCase(unittest.TestCase):

    def setUp(self):
        self.pid = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL).pid

    def tearDown(self):
        kill(self.pid)

    def test_process_groupname(self):
        groupname_ps = ps("ps --no-headers -o rgroup -p %s" %self.pid)
        groupname_psutil = psutil.Process(self.pid).groupname
        self.assertEqual(groupname_ps, groupname_psutil)


