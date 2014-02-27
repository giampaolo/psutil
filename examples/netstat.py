#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of 'netstat'.

$ python examples/netstat.py
Proto Local addr         Remote addr      Status        PID    Program name
tcp   127.0.0.1:48256    127.0.0.1:45884  ESTABLISHED   13646  chrome
tcp   127.0.0.1:47073    127.0.0.1:45884  ESTABLISHED   13646  chrome
tcp   127.0.0.1:47072    127.0.0.1:45884  ESTABLISHED   13646  chrome
tcp   127.0.0.1:45884                     LISTEN        13651  GoogleTalkPlugi
tcp   127.0.0.1:60948                     LISTEN        13651  GoogleTalkPlugi
tcp   172.17.42.1:49102  127.0.0.1:19305  CLOSE_WAIT    13651  GoogleTalkPlugi
tcp   172.17.42.1:55797  127.0.0.1:443    CLOSE_WAIT    13651  GoogleTalkPlugi
...
"""

import socket
from socket import AF_INET, SOCK_STREAM, SOCK_DGRAM

import psutil
from psutil._compat import print_


AD = "-"
AF_INET6 = getattr(socket, 'AF_INET6', object())
proto_map = {
    (AF_INET, SOCK_STREAM): 'tcp',
    (AF_INET6, SOCK_STREAM): 'tcp6',
    (AF_INET, SOCK_DGRAM): 'udp',
    (AF_INET6, SOCK_DGRAM): 'udp6',
}


def main():
    templ = "%-5s %-22s %-22s %-13s %-6s %s"
    print_(templ % (
        "Proto", "Local addr", "Remote addr", "Status", "PID", "Program name"))
    for p in psutil.process_iter():
        name = '?'
        try:
            name = p.name()
            cons = p.connections(kind='inet')
        except psutil.AccessDenied:
            print_(templ % (AD, AD, AD, AD, p.pid, name))
        except psutil.NoSuchProcess:
            continue
        else:
            for c in cons:
                raddr = ""
                laddr = "%s:%s" % (c.laddr)
                if c.raddr:
                    raddr = "%s:%s" % (c.raddr)
                print_(templ % (
                    proto_map[(c.family, c.type)],
                    laddr,
                    raddr,
                    c.status,
                    p.pid,
                    name[:15]))

if __name__ == '__main__':
    main()
