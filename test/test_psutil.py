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
        time.sleep(.1) # XXX: provisional, fix needed
        p = psutil.Process(self.proc.pid)
        p.kill()
        self.proc.wait()
        self.assertFalse(psutil.pid_exists(self.proc.pid) and psutil.Process(self.proc.pid).name == PYTHON)
        self.proc = None

    def test_pid(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        self.assertEqual(psutil.Process(self.proc.pid).pid, self.proc.pid)

    def test_eq(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        time.sleep(0.1)  # XXX: provisional, fix needed
        self.assertTrue(psutil.Process(self.proc.pid) == psutil.Process(self.proc.pid))

    def test_is_running(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        time.sleep(0.1)  # XXX: provisional, fix needed
        p = psutil.Process(self.proc.pid)
        self.assertTrue(p.is_running())
        psutil.Process(self.proc.pid).kill()
        self.proc.wait()
        time.sleep(0.1) # FIXME: why is this needed?
        try:
            self.assertFalse(p.is_running())
        finally:
            self.proc = None

    def test_pid_exists(self):
        if hasattr(os, 'getpid'):
            self.assertTrue(psutil.pid_exists(os.getpid()))
        self.assertFalse(psutil.pid_exists(-1))

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

    def test_get_pid_list(self):
        plist = [x.pid for x in psutil.get_process_list()]
        pidlist = psutil.get_pid_list()
        self.assertEqual(plist.sort(), pidlist.sort())

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
        self.assert_(isinstance(p.is_running(), bool))
        self.assert_(isinstance(psutil.get_process_list(), list))
        self.assert_(isinstance(psutil.get_process_list()[0], psutil.Process))
        self.assert_(isinstance(psutil.get_pid_list(), list))
        self.assert_(isinstance(psutil.get_pid_list()[0], int))
        self.assert_(isinstance(psutil.pid_exists(1), bool))

    def test_no_such_process(self):
        # Refers to Issue #12
        self.assertRaises(psutil.NoSuchProcess, psutil.Process, -1)

    def test_zombie_process(self):
        # Test that NoSuchProcess exception gets raised in the event the
        # process dies after we create the Process object.
        # Example:
        #  >>> proc = Process(1234)
        #  >>> time.sleep(5)  # time-consuming task, process dies in meantime
        #  >>> proc.name
        # Refers to Issue #15
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        p = psutil.Process(self.proc.pid)
        p.kill()
        self.proc.wait()
        self.proc = None
        time.sleep(0.1)  # XXX - maybe not necessary; verify

        self.assertRaises(psutil.NoSuchProcess, getattr, p, "ppid")
        self.assertRaises(psutil.NoSuchProcess, getattr, p, "parent")
        self.assertRaises(psutil.NoSuchProcess, getattr, p, "name")
        self.assertRaises(psutil.NoSuchProcess, getattr, p, "path")
        self.assertRaises(psutil.NoSuchProcess, getattr, p, "cmdline")
        self.assertRaises(psutil.NoSuchProcess, getattr, p, "uid")
        self.assertRaises(psutil.NoSuchProcess, getattr, p, "gid")
        self.assertRaises(psutil.NoSuchProcess, p.kill)

    # XXX - provisional
    def test_fetch_all(self):
        for p in psutil.get_process_list():
            str(p)

    def test_pid_0(self):
        # Process(0) is supposed work on all platforms even if with
        # some differences
        p = psutil.Process(0)
        if sys.platform.lower().startswith("win32"):
            self.assertEqual(p.name, 'System Idle Process')
        elif sys.platform.lower().startswith("linux"):
            self.assertEqual(p.name, 'sched')
        # XXX - add test cases for OS X
        # ...

        # use __str__ to access all common Process properties to check
        # that nothing strange happens
        str(p)

        # PID 0 is supposed to be available on all platforms
        self.assertTrue(0 in psutil.get_pid_list())
        self.assertTrue(psutil.pid_exists(0))


    # --- OS specific tests

    # UNIX tests

    if not sys.platform.lower().startswith("win32"):

        if hasattr(os, 'getuid') and os.getuid() > 0:
            def test_access_denied(self):
                p = psutil.Process(1)
                self.assertRaises(psutil.AccessDenied, p.kill)



def test_main():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(TestCase))
    unittest.TextTestRunner(verbosity=2).run(test_suite)
    if hasattr(test_support, "reap_children"):  # python 2.5 and >
        test_support.reap_children()
    DEVNULL.close()

if __name__ == '__main__':
    test_main()

