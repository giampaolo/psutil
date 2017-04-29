#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for net_connections() and Process.connections() APIs."""

import contextlib
import os
import socket
import textwrap
import unittest
from socket import AF_INET
from socket import AF_INET6
from socket import SOCK_DGRAM
from socket import SOCK_STREAM

import psutil
from psutil import FREEBSD
from psutil import OSX
from psutil import SUNOS
from psutil import WINDOWS
from psutil._common import supports_ipv6
from psutil._compat import unicode
from psutil.tests import bind_unix_socket
from psutil.tests import check_connection_ntuple
from psutil.tests import pyrun
from psutil.tests import reap_children
from psutil.tests import run_test_module_by_name
from psutil.tests import safe_rmpath
from psutil.tests import skip_on_access_denied
from psutil.tests import TESTFN
from psutil.tests import unix_socket_path
from psutil.tests import wait_for_file


AF_UNIX = getattr(socket, "AF_UNIX", object())


class TestProcessConnections(unittest.TestCase):
    """Tests for Process.connections()."""

    def tearDown(self):
        safe_rmpath(TESTFN)
        reap_children()

    def compare_proc_sys_cons(self, pid, proc_cons):
        from psutil._common import pconn
        sys_cons = [c[:-1] for c in psutil.net_connections(kind='all')
                    if c.pid == pid]
        if FREEBSD:
            # on FreeBSD all fds are set to -1
            proc_cons = [pconn(*[-1] + list(x[1:])) for x in proc_cons]
        self.assertEqual(sorted(proc_cons), sorted(sys_cons))

    @unittest.skipUnless(hasattr(socket, 'AF_UNIX'), 'AF_UNIX not supported')
    @skip_on_access_denied(only_if=OSX)
    def test_connections_unix(self):
        def check(type):
            with unix_socket_path() as name:
                sock = bind_unix_socket(name, type=type)
                with contextlib.closing(sock):
                    cons = psutil.Process().connections(kind='unix')
                    self.assertEqual(len(cons), 1)
                    conn = cons[0]
                    check_connection_ntuple(conn)
                    if conn.fd != -1:  # != sunos and windows
                        self.assertEqual(conn.fd, sock.fileno())
                    self.assertEqual(conn.family, AF_UNIX)
                    self.assertEqual(conn.type, type)
                    self.assertEqual(conn.laddr, name)
                    if not SUNOS:
                        # XXX Solaris can't retrieve system-wide UNIX
                        # sockets.
                        self.compare_proc_sys_cons(os.getpid(), cons)

        check(SOCK_STREAM)
        check(SOCK_DGRAM)

    @unittest.skipUnless(hasattr(socket, "fromfd"),
                         'socket.fromfd() not supported')
    @unittest.skipIf(WINDOWS or SUNOS,
                     'connection fd not available on this platform')
    def test_connection_fromfd(self):
        with contextlib.closing(socket.socket()) as sock:
            sock.bind(('127.0.0.1', 0))
            sock.listen(1)
            p = psutil.Process()
            for conn in p.connections():
                if conn.fd == sock.fileno():
                    break
            else:
                self.fail("couldn't find socket fd")
            dupsock = socket.fromfd(conn.fd, conn.family, conn.type)
            with contextlib.closing(dupsock):
                self.assertEqual(dupsock.getsockname(), conn.laddr)
                self.assertNotEqual(sock.fileno(), dupsock.fileno())

    def test_connection_constants(self):
        ints = []
        strs = []
        for name in dir(psutil):
            if name.startswith('CONN_'):
                num = getattr(psutil, name)
                str_ = str(num)
                assert str_.isupper(), str_
                assert str_ not in strs, str_
                assert num not in ints, num
                ints.append(num)
                strs.append(str_)
        if SUNOS:
            psutil.CONN_IDLE
            psutil.CONN_BOUND
        if WINDOWS:
            psutil.CONN_DELETE_TCB

    @skip_on_access_denied(only_if=OSX)
    def test_connections(self):
        def check_conn(proc, conn, family, type, laddr, raddr, status, kinds):
            all_kinds = ("all", "inet", "inet4", "inet6", "tcp", "tcp4",
                         "tcp6", "udp", "udp4", "udp6")
            check_connection_ntuple(conn)
            self.assertEqual(conn.family, family)
            self.assertEqual(conn.type, type)
            self.assertEqual(conn.laddr, laddr)
            self.assertEqual(conn.raddr, raddr)
            self.assertEqual(conn.status, status)
            for kind in all_kinds:
                cons = proc.connections(kind=kind)
                if kind in kinds:
                    self.assertNotEqual(cons, [])
                else:
                    self.assertEqual(cons, [])
            # compare against system-wide connections
            # XXX Solaris can't retrieve system-wide UNIX
            # sockets.
            if not SUNOS:
                self.compare_proc_sys_cons(proc.pid, [conn])

        tcp_template = textwrap.dedent("""
            import socket, time
            s = socket.socket($family, socket.SOCK_STREAM)
            s.bind(('$addr', 0))
            s.listen(1)
            with open('$testfn', 'w') as f:
                f.write(str(s.getsockname()[:2]))
            time.sleep(60)
        """)

        udp_template = textwrap.dedent("""
            import socket, time
            s = socket.socket($family, socket.SOCK_DGRAM)
            s.bind(('$addr', 0))
            with open('$testfn', 'w') as f:
                f.write(str(s.getsockname()[:2]))
            time.sleep(60)
        """)

        from string import Template
        testfile = os.path.basename(TESTFN)
        tcp4_template = Template(tcp_template).substitute(
            family=int(AF_INET), addr="127.0.0.1", testfn=testfile)
        udp4_template = Template(udp_template).substitute(
            family=int(AF_INET), addr="127.0.0.1", testfn=testfile)
        tcp6_template = Template(tcp_template).substitute(
            family=int(AF_INET6), addr="::1", testfn=testfile)
        udp6_template = Template(udp_template).substitute(
            family=int(AF_INET6), addr="::1", testfn=testfile)

        # launch various subprocess instantiating a socket of various
        # families and types to enrich psutil results
        tcp4_proc = pyrun(tcp4_template)
        tcp4_addr = eval(wait_for_file(testfile))
        udp4_proc = pyrun(udp4_template)
        udp4_addr = eval(wait_for_file(testfile))
        if supports_ipv6():
            tcp6_proc = pyrun(tcp6_template)
            tcp6_addr = eval(wait_for_file(testfile))
            udp6_proc = pyrun(udp6_template)
            udp6_addr = eval(wait_for_file(testfile))
        else:
            tcp6_proc = None
            udp6_proc = None
            tcp6_addr = None
            udp6_addr = None

        for p in psutil.Process().children():
            cons = p.connections()
            self.assertEqual(len(cons), 1)
            for conn in cons:
                # TCP v4
                if p.pid == tcp4_proc.pid:
                    check_conn(p, conn, AF_INET, SOCK_STREAM, tcp4_addr, (),
                               psutil.CONN_LISTEN,
                               ("all", "inet", "inet4", "tcp", "tcp4"))
                # UDP v4
                elif p.pid == udp4_proc.pid:
                    check_conn(p, conn, AF_INET, SOCK_DGRAM, udp4_addr, (),
                               psutil.CONN_NONE,
                               ("all", "inet", "inet4", "udp", "udp4"))
                # TCP v6
                elif p.pid == getattr(tcp6_proc, "pid", None):
                    check_conn(p, conn, AF_INET6, SOCK_STREAM, tcp6_addr, (),
                               psutil.CONN_LISTEN,
                               ("all", "inet", "inet6", "tcp", "tcp6"))
                # UDP v6
                elif p.pid == getattr(udp6_proc, "pid", None):
                    check_conn(p, conn, AF_INET6, SOCK_DGRAM, udp6_addr, (),
                               psutil.CONN_NONE,
                               ("all", "inet", "inet6", "udp", "udp6"))

        # err
        self.assertRaises(ValueError, p.connections, kind='???')


class TestSystemConnections(unittest.TestCase):
    """Tests for net_connections()."""

    @skip_on_access_denied()
    def test_net_connections(self):
        def check(cons, families, types_):
            AF_UNIX = getattr(socket, 'AF_UNIX', object())
            for conn in cons:
                self.assertIn(conn.family, families, msg=conn)
                if conn.family != AF_UNIX:
                    self.assertIn(conn.type, types_, msg=conn)
                self.assertIsInstance(conn.status, (str, unicode))

        from psutil._common import conn_tmap
        for kind, groups in conn_tmap.items():
            if SUNOS and kind == 'unix':
                continue
            families, types_ = groups
            cons = psutil.net_connections(kind)
            self.assertEqual(len(cons), len(set(cons)))
            check(cons, families, types_)

        self.assertRaises(ValueError, psutil.net_connections, kind='???')


if __name__ == '__main__':
    run_test_module_by_name(__file__)
