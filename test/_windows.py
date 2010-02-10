import os
import unittest
import platform
import subprocess

import psutil
from test_psutil import kill, PYTHON, DEVNULL
try:
    import wmi
except ImportError:
    wmi = None


class WindowsSpecificTestCase(unittest.TestCase):

    def setUp(self):
        self.pid = subprocess.Popen([PYTHON, "-E", "-O"], stdout=DEVNULL, stderr=DEVNULL).pid

    def tearDown(self):
        kill(self.pid)

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
        #p.groupname
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

    if wmi is not None:
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


if __name__ == '__main__':
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(WindowsSpecificTestCase))
    unittest.TextTestRunner(verbosity=2).run(test_suite)

