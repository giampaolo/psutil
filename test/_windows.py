#!/usr/bin/env python
#
# $Id$
#
# Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Windows specific tests.  These are implicitly run by test_psutil.py."""

import os
import unittest
import platform
import signal
import time
import warnings
import atexit
import sys
import subprocess
import errno

import psutil
import _psutil_mswindows
from psutil._compat import PY3, callable
from test_psutil import reap_children, get_test_subprocess, wait_for_pid
try:
    import wmi
except ImportError:
    err = sys.exc_info()[1]
    atexit.register(warnings.warn, "Couldn't run wmi tests: %s" % str(err),
                    RuntimeWarning)
    wmi = None
try:
    import win32api
    import win32con
except ImportError:
    err = sys.exc_info()[1]
    atexit.register(warnings.warn, "Couldn't run pywin32 tests: %s" % str(err),
                    RuntimeWarning)
    win32api = None



class WindowsSpecificTestCase(unittest.TestCase):

    def setUp(self):
        sproc = get_test_subprocess()
        wait_for_pid(sproc.pid)
        self.pid = sproc.pid

    def tearDown(self):
        reap_children()

    def test_issue_24(self):
        p = psutil.Process(0)
        self.assertRaises(psutil.AccessDenied, p.kill)

    def test_special_pid(self):
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
            if not platform.uname()[1] in ('vista', 'win-7', 'win7'):
                raise
        else:
            self.assertTrue(rss > 0)

    def test_signal(self):
        p = psutil.Process(self.pid)
        self.assertRaises(ValueError, p.send_signal, signal.SIGINT)

    def test_nic_names(self):
        p = subprocess.Popen(['ipconfig', '/all'], stdout=subprocess.PIPE)
        out = p.communicate()[0]
        if PY3:
            out = str(out, sys.stdout.encoding)
        nics = psutil.network_io_counters(pernic=True).keys()
        for nic in nics:
            if "pseudo-interface" in nic.replace(' ', '-').lower():
                continue
            if nic not in out:
                self.fail("%r nic wasn't found in 'ipconfig /all' output" % nic)

    if wmi is not None:

        # --- Process class tests

        def test_process_name(self):
            w = wmi.WMI().Win32_Process(ProcessId=self.pid)[0]
            p = psutil.Process(self.pid)
            self.assertEqual(p.name, w.Caption)

        def test_process_exe(self):
            w = wmi.WMI().Win32_Process(ProcessId=self.pid)[0]
            p = psutil.Process(self.pid)
            self.assertEqual(p.exe, w.ExecutablePath)

        def test_process_cmdline(self):
            w = wmi.WMI().Win32_Process(ProcessId=self.pid)[0]
            p = psutil.Process(self.pid)
            self.assertEqual(' '.join(p.cmdline), w.CommandLine.replace('"', ''))

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
            # ...claims that PageFileUsage is represented in Kilo
            # bytes but funnily enough on certain platforms bytes are
            # returned instead.
            wmi_usage = int(w.PageFileUsage)
            if (vms != wmi_usage) and (vms != wmi_usage * 1024):
                self.fail("wmi=%s, psutil=%s" % (wmi_usage, vms))

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
            # XXX - ? no actual test here

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

        def test_disks(self):
            ps_parts = psutil.disk_partitions(all=True)
            wmi_parts = wmi.WMI().Win32_LogicalDisk()
            for ps_part in ps_parts:
                for wmi_part in wmi_parts:
                    if ps_part.device.replace('\\', '') == wmi_part.DeviceID:
                        if not ps_part.mountpoint:
                            # this is usually a CD-ROM with no disk inserted
                            break
                        try:
                            usage = psutil.disk_usage(ps_part.mountpoint)
                        except OSError:
                            err = sys.exc_info()[1]
                            if err.errno == errno.ENOENT:
                                # usually this is the floppy
                                break
                            else:
                                raise
                        self.assertEqual(usage.total, int(wmi_part.Size))
                        wmi_free = int(wmi_part.FreeSpace)
                        self.assertEqual(usage.free, wmi_free)
                        # 10 MB tollerance
                        if abs(usage.free - wmi_free) > 10 * 1024 * 1024:
                            self.fail("psutil=%s, wmi=%s" % usage.free, wmi_free)
                        break
                else:
                    self.fail("can't find partition %s" % repr(ps_part))

    if win32api is not None:

        def test_get_num_handles(self):
            p = psutil.Process(os.getpid())
            before = p.get_num_handles()
            handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION,
                                          win32con.FALSE, os.getpid())
            after = p.get_num_handles()
            self.assertEqual(after, before+1)
            win32api.CloseHandle(handle)
            self.assertEqual(p.get_num_handles(), before)

        def test_get_num_handles_2(self):
            # Note: this fails from time to time; I'm keen on thinking
            # it doesn't mean something is broken
            def call(p, attr):
                attr = getattr(p, name, None)
                if attr is not None and callable(attr):
                    ret = attr()
                else:
                    ret = attr

            p = psutil.Process(self.pid)
            attrs = []
            failures = []
            for name in dir(psutil.Process):
                if name.startswith('_') \
                or name.startswith('set_') \
                or name in ('terminate', 'kill', 'suspend', 'resume', 'nice',
                            'send_signal', 'wait', 'get_children'):
                    continue
                else:
                    try:
                        call(p, name)
                        num1 = p.get_num_handles()
                        call(p, name)
                        num2 = p.get_num_handles()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    else:
                        if num2 > num1:
                            fail = "failure while processing Process.%s method " \
                                   "(before=%s, after=%s)" % (name, num1, num2)
                            failures.append(fail)
            if failures:
                self.fail('\n' + '\n'.join(failures))


if __name__ == '__main__':
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(WindowsSpecificTestCase))
    unittest.TextTestRunner(verbosity=2).run(test_suite)
