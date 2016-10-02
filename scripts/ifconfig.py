#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of 'ifconfig' on UNIX.

$ python scripts/ifconfig.py
lo:
    stats          : speed=0MB, duplex=?, mtu=65536, up=yes
    incoming       : bytes=6889336, pkts=84032, errs=0, drops=0
    outgoing       : bytes=6889336, pkts=84032, errs=0, drops=0
    IPv4 address   : 127.0.0.1
         netmask   : 255.0.0.0
    IPv6 address   : ::1
         netmask   : ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff
    MAC  address   : 00:00:00:00:00:00

vboxnet0:
    stats          : speed=10MB, duplex=full, mtu=1500, up=yes
    incoming       : bytes=0, pkts=0, errs=0, drops=0
    outgoing       : bytes=1622766, pkts=9102, errs=0, drops=0
    IPv4 address   : 192.168.33.1
         broadcast : 192.168.33.255
         netmask   : 255.255.255.0
    IPv6 address   : fe80::800:27ff:fe00:0%vboxnet0
         netmask   : ffff:ffff:ffff:ffff::
    MAC  address   : 0a:00:27:00:00:00
         broadcast : ff:ff:ff:ff:ff:ff

eth0:
    stats          : speed=0MB, duplex=?, mtu=1500, up=yes
    incoming       : bytes=18905596301, pkts=15178374, errs=0, drops=21
    outgoing       : bytes=1913720087, pkts=9543981, errs=0, drops=0
    IPv4 address   : 10.0.0.3
         broadcast : 10.255.255.255
         netmask   : 255.0.0.0
    IPv6 address   : fe80::7592:1dcf:bcb7:98d6%wlp3s0
         netmask   : ffff:ffff:ffff:ffff::
    MAC  address   : 48:45:20:59:a4:0c
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
            print("    stats          : ", end='')
            print("speed=%sMB, duplex=%s, mtu=%s, up=%s" % (
                st.speed, duplex_map[st.duplex], st.mtu,
                "yes" if st.isup else "no"))
        if nic in io_counters:
            io = io_counters[nic]
            print("    incoming       : ", end='')
            print("bytes=%s, pkts=%s, errs=%s, drops=%s" % (
                io.bytes_recv, io.packets_recv, io.errin, io.dropin))
            print("    outgoing       : ", end='')
            print("bytes=%s, pkts=%s, errs=%s, drops=%s" % (
                io.bytes_sent, io.packets_sent, io.errout, io.dropout))
        for addr in addrs:
            print("    %-4s" % af_map.get(addr.family, addr.family), end="")
            print(" address   : %s" % addr.address)
            if addr.broadcast:
                print("         broadcast : %s" % addr.broadcast)
            if addr.netmask:
                print("         netmask   : %s" % addr.netmask)
            if addr.ptp:
                print("      p2p       : %s" % addr.ptp)
        print("")


if __name__ == '__main__':
    main()
