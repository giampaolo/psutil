import unittest
import platform

import psutil


class WindowsSpecificTestCase(unittest.TestCase):

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
        p.groupname
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


