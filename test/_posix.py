#!/usr/bin/env python

# Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""POSIX specific tests.  These are implicitly run by test_psutil.py."""

import unittest
import subprocess
import time
import sys
import os
import datetime

import psutil

from psutil._compat import PY3
from test_psutil import (get_test_subprocess, reap_children, PYTHON, LINUX, OSX,
                         BSD, skip_on_access_denied, sh, skipIf)


def ps(cmd):
    """Expects a ps command with a -o argument and parse the result
    returning only the value of interest.
    """
    if not LINUX:
        cmd = cmd.replace(" --no-headers ", " ")
    p = subprocess.Popen(cmd, shell=1, stdout=subprocess.PIPE)
    output = p.communicate()[0].strip()
    if PY3:
        output = str(output, sys.stdout.encoding)
    if not LINUX:
        output = output.split('\n')[1]
    try:
        return int(output)
    except ValueError:
        return output


class PosixSpecificTestCase(unittest.TestCase):
    """Compare psutil results against 'ps' command line utility."""

    # for ps -o arguments see: http://unixhelp.ed.ac.uk/CGI/man-cgi?ps

    def setUp(self):
        self.pid = get_test_subprocess([PYTHON, "-E", "-O"],
                                       stdin=subprocess.PIPE).pid

    def tearDown(self):
        reap_children()

    def test_process_parent_pid(self):
        ppid_ps = ps("ps --no-headers -o ppid -p %s" %self.pid)
        ppid_psutil = psutil.Process(self.pid).ppid
        self.assertEqual(ppid_ps, ppid_psutil)

    def test_process_uid(self):
        uid_ps = ps("ps --no-headers -o uid -p %s" %self.pid)
        uid_psutil = psutil.Process(self.pid).uids.real
        self.assertEqual(uid_ps, uid_psutil)

    def test_process_gid(self):
        gid_ps = ps("ps --no-headers -o rgid -p %s" %self.pid)
        gid_psutil = psutil.Process(self.pid).gids.real
        self.assertEqual(gid_ps, gid_psutil)

    def test_process_username(self):
        username_ps = ps("ps --no-headers -o user -p %s" %self.pid)
        username_psutil = psutil.Process(self.pid).username
        self.assertEqual(username_ps, username_psutil)

    @skip_on_access_denied()
    def test_process_rss_memory(self):
        # give python interpreter some time to properly initialize
        # so that the results are the same
        time.sleep(0.1)
        rss_ps = ps("ps --no-headers -o rss -p %s" %self.pid)
        rss_psutil = psutil.Process(self.pid).get_memory_info()[0] / 1024
        self.assertEqual(rss_ps, rss_psutil)

    @skip_on_access_denied()
    def test_process_vsz_memory(self):
        # give python interpreter some time to properly initialize
        # so that the results are the same
        time.sleep(0.1)
        vsz_ps = ps("ps --no-headers -o vsz -p %s" %self.pid)
        vsz_psutil = psutil.Process(self.pid).get_memory_info()[1] / 1024
        self.assertEqual(vsz_ps, vsz_psutil)

    def test_process_name(self):
        # use command + arg since "comm" keyword not supported on all platforms
        name_ps = ps("ps --no-headers -o command -p %s" %self.pid).split(' ')[0]
        # remove path if there is any, from the command
        name_ps = os.path.basename(name_ps).lower()
        name_psutil = psutil.Process(self.pid).name.lower()
        self.assertEqual(name_ps, name_psutil)

    @skipIf(OSX or BSD)
    def test_process_create_time(self):
        time_ps = ps("ps --no-headers -o start -p %s" %self.pid).split(' ')[0]
        time_psutil = psutil.Process(self.pid).create_time
        time_psutil = datetime.datetime.fromtimestamp(
                        time_psutil).strftime("%H:%M:%S")
        self.assertEqual(time_ps, time_psutil)

    def test_process_exe(self):
        ps_pathname = ps("ps --no-headers -o command -p %s" %self.pid).split(' ')[0]
        psutil_pathname = psutil.Process(self.pid).exe
        try:
            self.assertEqual(ps_pathname, psutil_pathname)
        except AssertionError:
            # certain platforms such as BSD are more accurate returning:
            # "/usr/local/bin/python2.7"
            # ...instead of:
            # "/usr/local/bin/python"
            # We do not want to consider this difference in accuracy
            # an error.
            adjusted_ps_pathname = ps_pathname[:len(ps_pathname)]
            self.assertEqual(ps_pathname, adjusted_ps_pathname)

    def test_process_cmdline(self):
        ps_cmdline = ps("ps --no-headers -o command -p %s" %self.pid)
        psutil_cmdline = " ".join(psutil.Process(self.pid).cmdline)
        self.assertEqual(ps_cmdline, psutil_cmdline)

    def test_get_pids(self):
        # Note: this test might fail if the OS is starting/killing
        # other processes in the meantime
        p = get_test_subprocess(["ps", "ax", "-o", "pid"], stdout=subprocess.PIPE)
        output = p.communicate()[0].strip()
        if PY3:
            output = str(output, sys.stdout.encoding)
        output = output.replace('PID', '')
        p.wait()
        pids_ps = []
        for pid in output.split('\n'):
            if pid:
                pids_ps.append(int(pid.strip()))
        # remove ps subprocess pid which is supposed to be dead in meantime
        pids_ps.remove(p.pid)
        pids_psutil = psutil.get_pid_list()
        pids_ps.sort()
        pids_psutil.sort()

        # on OSX ps doesn't show pid 0
        if OSX and 0 not in pids_ps:
            pids_ps.insert(0, 0)

        if pids_ps != pids_psutil:
            difference = [x for x in pids_psutil if x not in pids_ps] + \
                         [x for x in pids_ps if x not in pids_psutil]
            self.fail("difference: " + str(difference))

    def test_nic_names(self):
        p = subprocess.Popen("ifconfig -a", shell=1, stdout=subprocess.PIPE)
        output = p.communicate()[0].strip()
        if PY3:
            output = str(output, sys.stdout.encoding)
        for nic in psutil.network_io_counters(pernic=True).keys():
            for line in output.split():
                if line.startswith(nic):
                    break
            else:
                self.fail("couldn't find %s nic in 'ifconfig -a' output" % nic)

    def test_get_users(self):
        out = sh("who")
        lines = out.split('\n')
        users = [x.split()[0] for x in lines]
        self.assertEqual(len(users), len(psutil.get_users()))
        terminals = [x.split()[1] for x in lines]
        for u in psutil.get_users():
            self.assertTrue(u.name in users, u.name)
            self.assertTrue(u.terminal in terminals, u.terminal)


if __name__ == '__main__':
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(PosixSpecificTestCase))
    unittest.TextTestRunner(verbosity=2).run(test_suite)
