#!/usr/bin/env python
#
# $Id$
#


import os
import unittest
import platform
import subprocess
import signal
import time
import warnings

import psutil
from test_psutil import reap_children, PYTHON, DEVNULL
try:
    from psutil import wmi
except ImportError:
    warnings.warn("Can't import WMI module; Windows specific tests disabled",
                  RuntimeWarning)
    wmi = None


class WindowsSpecificTestCase(unittest.TestCase):

    def setUp(self):
        self.pid = subprocess.Popen([PYTHON, "-E", "-O"], stdout=DEVNULL, stderr=DEVNULL).pid

    def tearDown(self):
        reap_children()

    def test_issue_24(self):
        p = psutil.Process(0)
        self.assertRaises(psutil.AccessDenied, p.kill)

    def test_pid_4(self):
        p = psutil.Process(4)
        self.assertEqual(p.name, 'System')
        # use __str__ to access all common Process properties to check
        # that nothing strange happens
        str(p)
        p.username
        self.assertTrue(p.create_time >= 0.0)
        try:
            rss, vms = p.get_memory_info()
        except psutil.AccessDenied:
            # expected on Windows Vista and Windows 7
            if not platform.uname()[1] in ('vista', 'win-7'):
                raise
        else:
            self.assertTrue(rss > 0)
            self.assertEqual(vms, 0)

    def test_signal(self):
        p = psutil.Process(self.pid)
        self.assertRaises(ValueError, p.send_signal, signal.SIGINT)

    if wmi is not None:

        # --- Process class tests

        def test_process_name(self):
            w = wmi.WMI().Win32_Process(ProcessId=self.pid)[0]
            p = psutil.Process(self.pid)
            self.assertEqual(p.name, w.Caption)

        def test_process_path(self):
            w = wmi.WMI().Win32_Process(ProcessId=self.pid)[0]
            p = psutil.Process(self.pid)
            self.assertEqual(os.path.join(p.path, p.name), w.ExecutablePath)

        def test_process_cmdline(self):
            w = wmi.WMI().Win32_Process(ProcessId=self.pid)[0]
            p = psutil.Process(self.pid)
            self.assertEqual(' '.join(p.cmdline), w.CommandLine)

        def test_process_username(self):
            w = wmi.WMI().Win32_Process(ProcessId=self.pid)[0]
            p = psutil.Process(self.pid)
            domain, _, username = w.GetOwner()
            username = "%s\\%s" %(domain, username)
            self.assertEqual(p.username, username)

        def test_process_rss_memory(self):
            w = wmi.WMI().Win32_Process(ProcessId=self.pid)[0]
            p = psutil.Process(self.pid)
            rss = p.get_memory_info()[0]
            self.assertEqual(rss, int(w.WorkingSetSize))

        def test_process_vsz_memory(self):
            w = wmi.WMI().Win32_Process(ProcessId=self.pid)[0]
            p = psutil.Process(self.pid)
            vsz = p.get_memory_info()[1]
            self.assertEqual(vsz, int(w.PageFileUsage) * 1024)

        def test_process_create_time(self):
            w = wmi.WMI().Win32_Process(ProcessId=self.pid)[0]
            p = psutil.Process(self.pid)
            wmic_create = str(w.CreationDate.split('.')[0])
            psutil_create = time.strftime("%Y%m%d%H%M%S",
                                          time.localtime(p.create_time))
            self.assertEqual(wmic_create, psutil_create)


        # --- psutil namespace functions and constants tests

        def test_NUM_CPUS(self):
            num_cpus = int(os.environ['NUMBER_OF_PROCESSORS'])
            self.assertEqual(num_cpus, psutil.NUM_CPUS)

        def test_TOTAL_PHYMEM(self):
            w = wmi.WMI().Win32_ComputerSystem()[0]
            self.assertEqual(int(w.TotalPhysicalMemory), psutil.TOTAL_PHYMEM)

        def test__UPTIME(self):
            # _UPTIME constant is not public but it is used internally
            # as value to return for pid 0 creation time.
            # WMI behaves the same.
            w = wmi.WMI().Win32_Process(ProcessId=self.pid)[0]
            p = psutil.Process(0)
            wmic_create = str(w.CreationDate.split('.')[0])
            psutil_create = time.strftime("%Y%m%d%H%M%S",
                                          time.localtime(p.create_time))

        def test_get_pids(self):
            # Note: this test might fail if the OS is starting/killing
            # other processes in the meantime
            w = wmi.WMI().Win32_Process()
            wmi_pids = [x.ProcessId for x in w]
            wmi_pids.sort()
            psutil_pids = psutil.get_pid_list()
            psutil_pids.sort()
            if wmi_pids != psutil_pids:
                difference = filter(lambda x:x not in wmi_pids, psutil_pids) + \
                             filter(lambda x:x not in psutil_pids, wmi_pids)
                self.fail("difference: " + str(difference))


if __name__ == '__main__':
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(WindowsSpecificTestCase))
    unittest.TextTestRunner(verbosity=2).run(test_suite)

