#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
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
from test_psutil import *


def ps(cmd):
    """Expects a ps command with a -o argument and parse the result
    returning only the value of interest.
    """
    if not LINUX:
        cmd = cmd.replace(" --no-headers ", " ")
    if SUNOS:
        cmd = cmd.replace("-o command", "-o comm")
        cmd = cmd.replace("-o start", "-o stime")
    p = subprocess.Popen(cmd, shell=1, stdout=subprocess.PIPE)
    output = p.communicate()[0].strip()
    if PY3:
        output = str(output, sys.stdout.encoding)
    if not LINUX:
        output = output.split('\n')[1].strip()
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

    @unittest.skipIf(OSX or BSD,
                    'ps -o start not available')
    def test_process_create_time(self):
        time_ps = ps("ps --no-headers -o start -p %s" %self.pid).split(' ')[0]
        time_psutil = psutil.Process(self.pid).create_time
        if SUNOS:
            time_psutil = round(time_psutil)
        time_psutil_tstamp = datetime.datetime.fromtimestamp(
                        time_psutil).strftime("%H:%M:%S")
        self.assertEqual(time_ps, time_psutil_tstamp)

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
        if SUNOS:
            # ps on Solaris only shows the first part of the cmdline
            psutil_cmdline = psutil_cmdline.split(" ")[0]
        self.assertEqual(ps_cmdline, psutil_cmdline)

    @retry_before_failing()
    def test_get_pids(self):
        # Note: this test might fail if the OS is starting/killing
        # other processes in the meantime
        if SUNOS:
            cmd = ["ps", "ax"]
        else:
            cmd = ["ps", "ax", "-o", "pid"]
        p = get_test_subprocess(cmd, stdout=subprocess.PIPE)
        output = p.communicate()[0].strip()
        if PY3:
            output = str(output, sys.stdout.encoding)
        pids_ps = []
        for line in output.split('\n')[1:]:
            if line:
                pid = int(line.split()[0].strip())
                pids_ps.append(pid)
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

    # for some reason ifconfig -a does not report differente interfaces
    # psutil does
    @unittest.skipIf(SUNOS, "test not reliable on SUNOS")
    def test_nic_names(self):
        p = subprocess.Popen("ifconfig -a", shell=1, stdout=subprocess.PIPE)
        output = p.communicate()[0].strip()
        if PY3:
            output = str(output, sys.stdout.encoding)
        for nic in psutil.net_io_counters(pernic=True).keys():
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

    def test_fds_open(self):
        # Note: this fails from time to time; I'm keen on thinking
        # it doesn't mean something is broken
        def call(p, attr):
            attr = getattr(p, name, None)
            if attr is not None and callable(attr):
                ret = attr()
            else:
                ret = attr

        p = psutil.Process(os.getpid())
        attrs = []
        failures = []
        for name in dir(psutil.Process):
            if name.startswith('_') \
            or name.startswith('set_') \
            or name in ('terminate', 'kill', 'suspend', 'resume', 'nice',
                        'send_signal', 'wait', 'get_children', 'as_dict'):
                continue
            else:
                try:
                    num1 = p.get_num_fds()
                    for x in range(2):
                        call(p, name)
                    num2 = p.get_num_fds()
                except psutil.AccessDenied:
                    pass
                else:
                    if abs(num2 - num1) > 1:
                        fail = "failure while processing Process.%s method " \
                               "(before=%s, after=%s)" % (name, num1, num2)
                        failures.append(fail)
        if failures:
            self.fail('\n' + '\n'.join(failures))




def test_main():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(PosixSpecificTestCase))
    result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    return result.wasSuccessful()

if __name__ == '__main__':
    if not test_main():
        sys.exit(1)
