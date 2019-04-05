#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of 'ifconfig' on UNIX.

$ python scripts/ifconfig.py
lo:
    stats          : speed=0MB, duplex=?, mtu=65536, up=yes
    incoming       : bytes=1.95M, pkts=22158, errs=0, drops=0
    outgoing       : bytes=1.95M, pkts=22158, errs=0, drops=0
    IPv4 address   : 127.0.0.1
         netmask   : 255.0.0.0
    IPv6 address   : ::1
         netmask   : ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff
    MAC  address   : 00:00:00:00:00:00

docker0:
    stats          : speed=0MB, duplex=?, mtu=1500, up=yes
    incoming       : bytes=3.48M, pkts=65470, errs=0, drops=0
    outgoing       : bytes=164.06M, pkts=112993, errs=0, drops=0
    IPv4 address   : 172.17.0.1
         broadcast : 172.17.0.1
         netmask   : 255.255.0.0
    IPv6 address   : fe80::42:27ff:fe5e:799e%docker0
         netmask   : ffff:ffff:ffff:ffff::
    MAC  address   : 02:42:27:5e:79:9e
         broadcast : ff:ff:ff:ff:ff:ff

wlp3s0:
    stats          : speed=0MB, duplex=?, mtu=1500, up=yes
    incoming       : bytes=7.04G, pkts=5637208, errs=0, drops=0
    outgoing       : bytes=372.01M, pkts=3200026, errs=0, drops=0
    IPv4 address   : 10.0.0.2
         broadcast : 10.255.255.255
         netmask   : 255.0.0.0
    IPv6 address   : fe80::ecb3:1584:5d17:937%wlp3s0
         netmask   : ffff:ffff:ffff:ffff::
    MAC  address   : 48:45:20:59:a4:0c
         broadcast : ff:ff:ff:ff:ff:ff
"""

from __future__ import print_function
import socket

import psutil
from psutil._common import bytes2human


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
                bytes2human(io.bytes_recv), io.packets_recv, io.errin,
                io.dropin))
            print("    outgoing       : ", end='')
            print("bytes=%s, pkts=%s, errs=%s, drops=%s" % (
                bytes2human(io.bytes_sent), io.packets_sent, io.errout,
                io.dropout))
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
