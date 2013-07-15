#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of 'netstat -antup', shows all TCP and UDP connections opened
by the system.
"""

import socket
from socket import AF_INET, SOCK_STREAM, SOCK_DGRAM

import psutil
from psutil._compat import print_


AF_INET6 = getattr(socket, 'AF_INET6', object())
proto_map = {(AF_INET, SOCK_STREAM)  : 'tcp',
             (AF_INET6, SOCK_STREAM) : 'tcp6',
             (AF_INET, SOCK_DGRAM)   : 'udp',
             (AF_INET6, SOCK_DGRAM)  : 'udp6'}

def main():
    templ = "%-5s %-22s %-22s %-13s %-6s %s"
    print_(templ % ("Proto", "Local addr", "Remote addr", "Status", "PID",
                    "Program name"))
    for conn in psutil.net_connections():
        pid = name = '-'
        if conn.pid is not None:
            try:
                pid = conn.pid
                p = psutil.Process(conn.pid)
                name = p.name
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass
        raddr = ""
        laddr = "%s:%s" % (conn.laddr)
        if conn.raddr:
            raddr = "%s:%s" % (conn.raddr)
        print_(templ % (proto_map[(conn.family, conn.type)],
                        laddr,
                        raddr,
                        str(conn.status),
                        pid,
                        name[:15]))

if __name__ == '__main__':
    main()
