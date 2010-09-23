#!/usr/bin/env python
#
# $Id$
#

import unittest
import subprocess

import psutil


class LinuxSpecificTestCase(unittest.TestCase):

    def test_cached_phymem(self):
        # test psutil.cached_phymem against "cached" column of free
        # command line utility
        p = subprocess.Popen("free", shell=1, stdout=subprocess.PIPE)
        output = p.communicate()[0].strip()
        free_cmem = int(output.split('\n')[1].split()[6])
        psutil_cmem = psutil.cached_phymem() / 1024
        self.assertEqual(free_cmem, psutil_cmem)

    def test_phymem_buffers(self):
        # test psutil.phymem_buffers against "buffers" column of free
        # command line utility
        p = subprocess.Popen("free", shell=1, stdout=subprocess.PIPE)
        output = p.communicate()[0].strip()
        free_cmem = int(output.split('\n')[1].split()[5])
        psutil_cmem = psutil.phymem_buffers() / 1024
        self.assertEqual(free_cmem, psutil_cmem)


if __name__ == '__main__':
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(LinuxSpecificTestCase))
    unittest.TextTestRunner(verbosity=2).run(test_suite)




