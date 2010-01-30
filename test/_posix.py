#!/usr/bin/env python

import unittest
import subprocess
import time
import sys

import psutil

from test_psutil import kill, PYTHON, DEVNULL


def sh(cmd):
    """Execute a shell command and return its output."""
    if not sys.platform.lower().startswith("linux"):
        cmd = cmd.replace(" --no-headers ", " ")
    p = subprocess.Popen(cmd, shell=1, stdout=subprocess.PIPE)
    output = p.communicate()[0].strip()
    if not sys.platform.lower().startswith("linux"):
        output = output.split()[1]
    return output



class PosixSpecificTestCase(unittest.TestCase):
    """Compare psutil results against 'ps' command line utility."""

    # for ps -o arguments see: http://unixhelp.ed.ac.uk/CGI/man-cgi?ps

    def setUp(self):
        self.pid = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL).pid

    def tearDown(self):
        kill(self.pid)

    def test_process_parent_pid(self):
        ppid_ps = sh("ps --no-headers -o ppid -p %s" %self.pid)
        ppid_psutil = psutil.Process(self.pid).ppid
        self.assertEqual(ppid_ps, str(ppid_psutil))

    def test_process_uid(self):
        uid_ps = sh("ps --no-headers -o euid -p %s" %self.pid)
        uid_psutil = psutil.Process(self.pid).uid
        self.assertEqual(uid_ps, str(uid_psutil))

    def test_process_gid(self):
        gid_ps = sh("ps --no-headers -o egid -p %s" %self.pid)
        gid_psutil = psutil.Process(self.pid).uid
        self.assertEqual(gid_ps, str(gid_psutil))

    def test_process_username(self):
        username_ps = sh("ps --no-headers -o user -p %s" %self.pid)
        username_psutil = psutil.Process(self.pid).username
        self.assertEqual(username_ps, username_psutil)

    def test_process_groupname(self):
        groupname_ps = sh("ps --no-headers -o egroup -p %s" %self.pid)
        groupname_psutil = psutil.Process(self.pid).groupname
        self.assertEqual(groupname_ps, groupname_psutil)

    def test_process_rss_memory(self):
        # give python interpreter some time to properly initialize
        # so that the results are the same
        time.sleep(0.1)
        rss_ps = sh("ps --no-headers -o rss -p %s" %self.pid)
        rss_psutil = psutil.Process(self.pid).get_memory_info()[0] / 1024
        self.assertEqual(rss_ps, str(rss_psutil))

    def test_process_vsz_memory(self):
        # give python interpreter some time to properly initialize
        # so that the results are the same
        time.sleep(0.1)
        vsz_ps = sh("ps --no-headers -o vsz -p %s" %self.pid)
        vsz_psutil = psutil.Process(self.pid).get_memory_info()[1] / 1024
        self.assertEqual(vsz_ps, str(vsz_psutil))

    def test_process_create_time(self):
        start_ps = sh("ps --no-headers -o start -p %s" %self.pid)
        start_psutil = psutil.Process(self.pid).create_time
        start_psutil = time.strftime("%H:%M:%S", time.localtime(start_psutil))
        self.assertEqual(start_ps, start_psutil)
