#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of 'ifconfig' on UNIX.

$ python examples/ifconfig.py
lo:
    IPv4     address   : 127.0.0.1
             broadcast : 127.0.0.1
             netmask   : 255.0.0.0
    IPv6     address   : ::1
             netmask   : ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff
    HWADDR   address   : 00:00:00:00:00:00
             broadcast : 00:00:00:00:00:00

wlan0:
    IPv4     address   : 192.168.1.3
             broadcast : 192.168.1.255
             netmask   : 255.255.255.0
    IPv6     address   : fe80::c685:8ff:fe45:641%wlan0
             netmask   : ffff:ffff:ffff:ffff::
    HWADDR   address   : c4:85:08:45:06:41
             broadcast : ff:ff:ff:ff:ff:ff

docker0:
    IPv4     address   : 172.17.42.1
             broadcast : 172.17.42.1
             netmask   : 255.255.0.0
    IPv6     address   : fe80::ac6d:3aff:fe0d:a19c%docker0
             netmask   : ffff:ffff:ffff:ffff::
    HWADDR   address   : ae:6d:3a:0d:a1:9c
             broadcast : ff:ff:ff:ff:ff:ff
"""

from __future__ import print_function
import socket

import psutil


af_map = {
    socket.AF_INET: 'IPv4',
    socket.AF_INET6: 'IPv6',
    psutil.AF_LINK: 'HWADDR',
}


def main():
    for nic, addrs in psutil.net_if_addrs().items():
        print("%s:" % (nic))
        for addr in addrs:
            print("    %-8s" % af_map.get(addr.family, addr.family), end="")
            print(" address   : %s" % addr.address)
            if addr.broadcast:
                print("             broadcast : %s" % addr.broadcast)
            if addr.netmask:
                print("             netmask   : %s" % addr.netmask)
        print("")


if __name__ == '__main__':
    main()
