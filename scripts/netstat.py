#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A clone of 'netstat -antp' on Linux.

$ python3 scripts/netstat.py
Proto Local address      Remote address   Status        PID    Program name
tcp   127.0.0.1:48256    127.0.0.1:45884  ESTABLISHED   13646  chrome
tcp   127.0.0.1:47073    127.0.0.1:45884  ESTABLISHED   13646  chrome
tcp   127.0.0.1:47072    127.0.0.1:45884  ESTABLISHED   13646  chrome
tcp   127.0.0.1:45884    -                LISTEN        13651  GoogleTalkPlugi
tcp   127.0.0.1:60948    -                LISTEN        13651  GoogleTalkPlugi
tcp   172.17.42.1:49102  127.0.0.1:19305  CLOSE_WAIT    13651  GoogleTalkPlugi
tcp   172.17.42.1:55797  127.0.0.1:443    CLOSE_WAIT    13651  GoogleTalkPlugi
...
"""

import socket
from socket import AF_INET
from socket import SOCK_DGRAM
from socket import SOCK_STREAM

import psutil


AD = "-"
AF_INET6 = getattr(socket, 'AF_INET6', object())
proto_map = {
    (AF_INET, SOCK_STREAM): 'tcp',
    (AF_INET6, SOCK_STREAM): 'tcp6',
    (AF_INET, SOCK_DGRAM): 'udp',
    (AF_INET6, SOCK_DGRAM): 'udp6',
}


def main():
    templ = "{:<5} {:<30} {:<30} {:<13} {:<6} {}"
    header = templ.format(
        "Proto",
        "Local address",
        "Remote address",
        "Status",
        "PID",
        "Program name",
    )
    print(header)
    proc_names = {}
    for p in psutil.process_iter(['pid', 'name']):
        proc_names[p.info['pid']] = p.info['name']
    for c in psutil.net_connections(kind='inet'):
        laddr = "{}:{}".format(*c.laddr)
        raddr = ""
        if c.raddr:
            raddr = "{}:{}".format(*c.raddr)
        name = proc_names.get(c.pid, '?') or ''
        line = templ.format(
            proto_map[(c.family, c.type)],
            laddr,
            raddr or AD,
            c.status,
            c.pid or AD,
            name[:15],
        )
        print(line)


if __name__ == '__main__':
    main()
