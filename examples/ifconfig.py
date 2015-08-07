#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of 'ifconfig' on UNIX.

$ python examples/ifconfig.py
lo (speed=0MB, duplex=?, mtu=65536, up=yes):
    IPv4     address   : 127.0.0.1
             broadcast : 127.0.0.1
             netmask   : 255.0.0.0
    IPv6     address   : ::1
             netmask   : ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff
    MAC      address   : 00:00:00:00:00:00
             broadcast : 00:00:00:00:00:00

wlan0 (speed=0MB, duplex=?, mtu=1500, up=yes):
    IPv4     address   : 10.0.3.1
             broadcast : 10.0.3.255
             netmask   : 255.255.255.0
    IPv6     address   : fe80::3005:adff:fe31:8698
             netmask   : ffff:ffff:ffff:ffff::
    MAC      address   : 32:05:ad:31:86:98
             broadcast : ff:ff:ff:ff:ff:ff

eth0 (speed=100MB, duplex=full, mtu=1500, up=yes):
    IPv4     address   : 192.168.1.2
             broadcast : 192.168.1.255
             netmask   : 255.255.255.0
    IPv6     address   : fe80::c685:8ff:fe45:641
             netmask   : ffff:ffff:ffff:ffff::
    MAC      address   : c4:85:08:45:06:41
             broadcast : ff:ff:ff:ff:ff:ff
"""

from __future__ import print_function
import socket

import psutil


af_map = {
    socket.AF_INET: 'IPv4',
    socket.AF_INET6: 'IPv6',
    psutil.AF_LINK: 'MAC',
}

duplex_map = {
    psutil.NIC_DUPLEX_FULL: "full",
    psutil.NIC_DUPLEX_HALF: "half",
    psutil.NIC_DUPLEX_UNKNOWN: "?",
}


def main():
    stats = psutil.net_if_stats()
    for nic, addrs in psutil.net_if_addrs().items():
        if nic in stats:
            print("%s (speed=%sMB, duplex=%s, mtu=%s, up=%s):" % (
                nic, stats[nic].speed, duplex_map[stats[nic].duplex],
                stats[nic].mtu, "yes" if stats[nic].isup else "no"))
        else:
            print("%s:" % (nic))
        for addr in addrs:
            print("    %-8s" % af_map.get(addr.family, addr.family), end="")
            print(" address   : %s" % addr.address)
            if addr.broadcast:
                print("             broadcast : %s" % addr.broadcast)
            if addr.netmask:
                print("             netmask   : %s" % addr.netmask)
            if addr.ptp:
                print("             p2p       : %s" % addr.ptp)
        print("")


if __name__ == '__main__':
    main()
