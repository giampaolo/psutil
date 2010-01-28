import unittest
import subprocess

import psutil


class BSDSpecificTestCase(unittest.TestCase):

    def test_TOTAL_PHYMEM(self):
        p = subprocess.Popen('sysctl -a | grep hw.physmem', shell=1, stdout=subprocess.PIPE)
        out = p.stdout.read()
        value = int(out.split()[1])
        self.assertEqual(value, psutil.TOTAL_PHYMEM)


