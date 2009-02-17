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

    def test_get_tcp_connections(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        time.sleep(0.1)  # XXX: provisional, fix needed
        self.assertEqual(psutil.Process(self.proc.pid).get_tcp_connections(), [])
        psutil.Process(self.proc.pid).kill()

        ip = "127.0.0.1"
        port = find_unused_port()
        arg = "import socket;" \
              "s = socket.socket();" \
              "s.bind(('%s', %s));" %(ip, port) + \
              "s.listen(1);" \
              "s.accept()"
        self.proc = subprocess.Popen([PYTHON, "-c", arg], stdout=DEVNULL, stderr=DEVNULL)
        time.sleep(0.1)  # XXX: provisional, fix needed
        cons = psutil.Process(self.proc.pid).get_tcp_connections()
        self.assertEqual(len(cons), 1)
        self.assertEqual(cons[0][0], "%s:%s" %(ip, port))
        self.assertEqual(cons[0][2], "LISTEN")

    def test_get_udp_connections(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        time.sleep(0.1)  # XXX: provisional, fix needed
        self.assertEqual(psutil.Process(self.proc.pid).get_udp_connections(), [])
        psutil.Process(self.proc.pid).kill()

        ip = "127.0.0.1"
        port = find_unused_port(socktype=socket.SOCK_DGRAM)
        arg = "import socket;" \
              "s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM);" \
              "s.bind(('%s', %s));" %(ip, port) + \
              "s.recvfrom(1024)"
        self.proc = subprocess.Popen([PYTHON, "-c", arg], stdout=DEVNULL, stderr=DEVNULL)
        time.sleep(0.1)  # XXX: provisional, fix needed
        cons = psutil.Process(self.proc.pid).get_udp_connections()
        self.assertEqual(len(cons), 1)
        self.assertEqual(cons[0][0], "%s:%s" %(ip, port))

    def test_fetch_all(self):
        for p in psutil.get_process_list():
            p.pid
            p.name
            p.path
            p.cmdline
            p.uid
            p.gid
            p.get_tcp_connections()
            p.get_udp_connections()
            str(p)  # test __str__


def test_main():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(TestCase))
    unittest.TextTestRunner(verbosity=2).run(test_suite)
    if hasattr(test_support, "reap_children"):  # python 2.5 and >
        test_support.reap_children()
    DEVNULL.close()

if __name__ == '__main__':
    test_main()

