#!/usr/bin/env python

# Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of 'netstat'.
"""

import socket
from socket import AF_INET, SOCK_STREAM, SOCK_DGRAM

import psutil
from psutil._compat import print_


AD = "-"
AF_INET6 = getattr(socket, 'AF_INET6', object())
proto_map = {(AF_INET, SOCK_STREAM)  : 'tcp',
             (AF_INET6, SOCK_STREAM) : 'tcp6',
             (AF_INET, SOCK_DGRAM)   : 'udp',
             (AF_INET6, SOCK_DGRAM)  : 'udp6'}

def main():
    templ = "%-5s %-22s %-22s %-13s %-6s %s"
    print_(templ % ("Proto", "Local addr", "Remote addr", "Status", "PID",
                    "Program name"))
    for p in psutil.process_iter():
        name = '?'
        try:
            name = p.name
            cons = p.get_connections(kind='inet')
        except psutil.AccessDenied:
            print_(templ % (AD, AD, AD, AD, p.pid, name))
        else:
            for c in cons:
                raddr = ""
                laddr = "%s:%s" % (c.local_address)
                if c.remote_address:
                    raddr = "%s:%s" % (c.remote_address)
                print_(templ % (proto_map[(c.family, c.type)],
                                laddr,
                                raddr,
                                str(c.status),
                                p.pid,
                                name[:15]))

if __name__ == '__main__':
    main()
