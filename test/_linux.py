#!/usr/bin/env python
# $Id

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


