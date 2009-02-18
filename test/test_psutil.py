#!/usr/bin/env python
# test_psutil.py

import unittest
import os
import sys
import subprocess
import time
import signal
import socket
from test import test_support

import psutil


PYTHON = os.path.realpath(sys.executable)
DEVNULL = open(os.devnull, 'r+')


def find_unused_port(family=socket.AF_INET, socktype=socket.SOCK_STREAM):
    "Bind the socket to a free port and return the port number."
    tempsock = socket.socket(family, socktype)
    port = test_support.bind_port(tempsock)
    tempsock.close()
    del tempsock
    return port


class TestCase(unittest.TestCase):

    def setUp(self):
        self.proc = None

    def tearDown(self):
        if self.proc is not None:
            try:
                if hasattr(os, 'kill'):
                    os.kill(self.proc.pid, signal.SIGKILL)
                else:
                    psutil.Process(self.proc.pid).kill()
            finally:
                self.proc = None

    def test_get_process_list(self):
        pids = [x.pid for x in psutil.get_process_list()]
        if hasattr(os, 'getpid'):
            self.assertTrue(os.getpid() in pids)

    def test_kill(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        psutil.Process(self.proc.pid).kill()
        self.proc.wait()
        self.assertFalse(psutil.pid_exists(self.proc.pid) and psutil.Process(self.proc.pid).name == PYTHON)
        self.proc = None

    def test_pid(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        self.assertEqual(psutil.Process(self.proc.pid).pid, self.proc.pid)

    def test_path(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        time.sleep(0.1)  # XXX: provisional, fix needed
        self.assertEqual(psutil.Process(self.proc.pid).path, os.path.dirname(PYTHON))

    def test_cmdline(self):
        self.proc = subprocess.Popen([PYTHON, "-E"], stdout=DEVNULL, stderr=DEVNULL)
        time.sleep(0.1)  # XXX: provisional, fix needed
        self.assertEqual(psutil.Process(self.proc.pid).cmdline, [PYTHON, "-E"])

    def test_name(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL,  stderr=DEVNULL)
        time.sleep(0.1)  # XXX: provisional, fix needed
        self.assertEqual(psutil.Process(self.proc.pid).name, os.path.basename(PYTHON))

    def test_uid(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        time.sleep(0.1)  # XXX: provisional, fix needed
        uid = psutil.Process(self.proc.pid).uid
        if hasattr(os, 'getuid'):
            self.assertEqual(uid, os.getuid())
        else:
            # On those platforms where UID doesn't make sense (Windows)
            # we expect it to be -1
            self.assertEqual(uid, -1)

    def test_gid(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        time.sleep(0.1)  # XXX: provisional, fix needed
        gid = psutil.Process(self.proc.pid).gid
        if hasattr(os, 'getgid'):
            self.assertEqual(gid, os.getgid())
        else:
            # On those platforms where GID doesn't make sense (Windows)
            # we expect it to be -1
            self.assertEqual(gid, -1)

    def test_parent_ppid(self):
        this_parent = os.getpid()
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        p = psutil.Process(self.proc.pid)
        self.assertEqual(p.ppid, this_parent)
        self.assertEqual(p.parent.pid, this_parent)

    def test_fetch_all(self):
        for p in psutil.get_process_list():
            p.pid
            p.ppid
            p.parent
            p.name
            p.path
            p.cmdline
            p.uid
            p.gid
            str(p)  # test __str__

    def test_get_pid_list(self):
        self.assertEqual([x.pid for x in psutil.get_process_list()], psutil.get_pid_list())

    def test_types(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        p = psutil.Process(self.proc.pid)
        self.assert_(isinstance(p.pid, int))
        self.assert_(isinstance(p.ppid, int))
        self.assert_(isinstance(p.parent, psutil.Process))
        self.assert_(isinstance(p.name, str))
        self.assert_(isinstance(p.path, str))
        self.assert_(isinstance(p.cmdline, list))
        self.assert_(isinstance(p.uid, int))
        self.assert_(isinstance(p.gid, int))
        self.assert_(isinstance(psutil.get_process_list(), list))
        self.assert_(isinstance(psutil.get_process_list()[0], psutil.Process))


def test_main():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(TestCase))
    unittest.TextTestRunner(verbosity=2).run(test_suite)
    if hasattr(test_support, "reap_children"):  # python 2.5 and >
        test_support.reap_children()
    DEVNULL.close()

if __name__ == '__main__':
    test_main()

