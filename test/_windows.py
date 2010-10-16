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
import atexit

import psutil
from test_psutil import reap_children, get_test_subprocess
try:
    import wmi
except ImportError:
    atexit.register(warnings.warn, "Couldn't import wmi module; some Windows "
                                 "specific tests were disabled", RuntimeWarning)
    wmi = None

WIN2000 = platform.win32_ver()[0] == '2000'


class WindowsSpecificTestCase(unittest.TestCase):

    def setUp(self):
        sproc = get_test_subprocess()
        self.pid = sproc.pid

    def tearDown(self):
        reap_children()

    def test_issue_24(self):
        p = psutil.Process(0)
        self.assertRaises(psutil.AccessDenied, p.kill)

    def test_special_pid(self):
        if not WIN2000:
            p = psutil.Process(4)
        else:
            p = psutil.Process(8)
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
            if not platform.uname()[1] in ('vista', 'win-7', 'win7'):
                raise
        else:
            self.assertTrue(rss > 0)
            if not WIN2000:
                self.assertEqual(vms, 0)

    def test_signal(self):
        p = psutil.Process(self.pid)
        self.assertRaises(ValueError, p.send_signal, signal.SIGINT)

    def test_process_names(self):
        special_pids = [0, 4]
        if WIN2000:
            special_pids.append(8)
        for p in psutil.process_iter():
            name = p.name.lower()
            if p.pid in special_pids:
                continue
            self.assertTrue(name.endswith(".exe") or name.endswith(".bin"))

    if wmi is not None:

        # --- Process class tests

        def test_process_name(self):
            w = wmi.WMI().Win32_Process(ProcessId=self.pid)[0]
            p = psutil.Process(self.pid)
            self.assertEqual(p.name, w.Caption)

        def test_process_path(self):
            w = wmi.WMI().Win32_Process(ProcessId=self.pid)[0]
            p = psutil.Process(self.pid)
            self.assertEqual(p.exe, w.ExecutablePath)

        if not WIN2000:
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
            time.sleep(0.1)
            w = wmi.WMI().Win32_Process(ProcessId=self.pid)[0]
            p = psutil.Process(self.pid)
            rss = p.get_memory_info().rss
            self.assertEqual(rss, int(w.WorkingSetSize))

        def test_process_vms_memory(self):
            time.sleep(0.1)
            w = wmi.WMI().Win32_Process(ProcessId=self.pid)[0]
            p = psutil.Process(self.pid)
            vms = p.get_memory_info().vms
            # http://msdn.microsoft.com/en-us/library/aa394372(VS.85).aspx
            # claims that PageFileUsage is represented in Kilo bytes.
            # This appear to be true on Windows 7 but not on Windows XP.
            if platform.uname()[1] in ('vista', 'win-7', 'win7'):
                self.assertEqual(vms, int(w.PageFileUsage * 1024))
            else:
                self.assertEqual(vms, w.PageFileUsage)

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

