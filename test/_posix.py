#!/usr/bin/env python

import unittest
import subprocess
import time
import sys

import psutil

from test_psutil import kill, PYTHON, DEVNULL


def ps(cmd):
    """Expects a ps command with a -o argument and parse the result
    returning only the value of interest.
    """
    if not sys.platform.lower().startswith("linux"):
        cmd = cmd.replace(" --no-headers ", " ")
    p = subprocess.Popen(cmd, shell=1, stdout=subprocess.PIPE)
    output = p.communicate()[0].strip()
    if not sys.platform.lower().startswith("linux"):
        output = output.split()[1]
    try:
        return int(output)
    except ValueError:
        return output


class PosixSpecificTestCase(unittest.TestCase):
    """Compare psutil results against 'ps' command line utility."""

    # for ps -o arguments see: http://unixhelp.ed.ac.uk/CGI/man-cgi?ps

    def setUp(self):
        self.pid = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL).pid

    def tearDown(self):
        kill(self.pid)

    def test_process_parent_pid(self):
        ppid_ps = ps("ps --no-headers -o ppid -p %s" %self.pid)
        ppid_psutil = psutil.Process(self.pid).ppid
        self.assertEqual(ppid_ps, ppid_psutil)

    def test_process_uid(self):
        uid_ps = ps("ps --no-headers -o uid -p %s" %self.pid)
        uid_psutil = psutil.Process(self.pid).uid
        self.assertEqual(uid_ps, uid_psutil)

    def test_process_gid(self):
        gid_ps = ps("ps --no-headers -o rgid -p %s" %self.pid)
        gid_psutil = psutil.Process(self.pid).gid
        self.assertEqual(gid_ps, gid_psutil)

    def test_process_username(self):
        username_ps = ps("ps --no-headers -o user -p %s" %self.pid)
        username_psutil = psutil.Process(self.pid).username
        self.assertEqual(username_ps, username_psutil)

    def test_process_rss_memory(self):
        # give python interpreter some time to properly initialize
        # so that the results are the same
        time.sleep(0.1)
        rss_ps = ps("ps --no-headers -o rss -p %s" %self.pid)
        rss_psutil = psutil.Process(self.pid).get_memory_info()[0] / 1024
        self.assertEqual(rss_ps, rss_psutil)

    def test_process_vsz_memory(self):
        # give python interpreter some time to properly initialize
        # so that the results are the same
        time.sleep(0.1)
        vsz_ps = ps("ps --no-headers -o vsz -p %s" %self.pid)
        vsz_psutil = psutil.Process(self.pid).get_memory_info()[1] / 1024
        self.assertEqual(vsz_ps, vsz_psutil)

    def test_get_pids(self):
        # Note: this test might fail if the OS is starting/killing
        # other processes in the meantime
        p = subprocess.Popen(["ps", "ax", "-o", "pid"], stdout=subprocess.PIPE)
        output = p.communicate()[0].strip()
        output = output.replace('PID', '')
        p.wait()
        pids_ps = []
        for pid in output.split('\n'):
            if pid:
                pids_ps.append(int(pid.strip()))
        # remove ps subprocess pid which is supposed to be dead in meantime
        pids_ps.remove(p.pid)
        # not all systems include pid 0 in their list but psutil does so 
        # we force it
        if 0 not in pids_ps:
            pis_ps.append(0)

        pids_psutil = psutil.get_pid_list()
        pids_ps.sort()
        pids_psutil.sort()

        if pids_ps != pids_psutil:
            difference = filter(lambda x:x not in pids_ps, pids_psutil) + \
                         filter(lambda x:x not in pids_psutil, pids_ps)
            self.fail("difference: " + str(difference))


if __name__ == '__main__':
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(PosixSpecificTestCase))
    unittest.TextTestRunner(verbosity=2).run(test_suite)


