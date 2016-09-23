#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of 'ifconfig' on UNIX.

$ python scripts/ifconfig.py
lo (speed=0MB, duplex=?, mtu=65536, up=yes):
    IPv4     address   : 127.0.0.1
             broadcast : 127.0.0.1
             netmask   : 255.0.0.0
    IPv6     address   : ::1
             netmask   : ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff
    MAC      address   : 00:00:00:00:00:00
             broadcast : 00:00:00:00:00:00

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
    io_counters = psutil.net_io_counters(pernic=True)
    for nic, addrs in psutil.net_if_addrs().items():
        print("%s:" % (nic))
        if nic in stats:
            st = stats[nic]
            print("    stats           : ", end='')
            print("speed=%sMB, duplex=%s, mtu=%s, up=%s" % (
                st.speed, duplex_map[st.duplex], st.mtu,
                "yes" if st.isup else "no"))
        if nic in io_counters:
            io = io_counters[nic]
            print("    incoming        : ", end='')
            print("bytes=%s, pkts=%s, errs=%s, drops=%s" % (
                io.bytes_recv, io.packets_recv, io.errin, io.dropin))
            print("    outgoing        : ", end='')
            print("bytes=%s, pkts=%s, errs=%s, drops=%s" % (
                io.bytes_sent, io.packets_sent, io.errout, io.dropout))
        for addr in addrs:
            print("    %-5s" % af_map.get(addr.family, addr.family), end="")
            print(" address   : %s" % addr.address)
            if addr.broadcast:
                print("          broadcast : %s" % addr.broadcast)
            if addr.netmask:
                print("          netmask   : %s" % addr.netmask)
            if addr.ptp:
                print("       p2p       : %s" % addr.ptp)
        print("")


if __name__ == '__main__':
    main()
