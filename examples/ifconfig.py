#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of 'ifconfig' on UNIX.

$ python examples/ifconfig.py
lo
    inet address:127.0.0.1, broadcast:127.0.0.1, netmask:255.0.0.0
    inet6 address:::1, broadcast:-, netmask:-
    packet address:00:00:00:00:00:00, broadcast:00:00:00:00:00:00, netmask:-

eth0
    inet address:192.168.0.10, broadcast:192.168.0.255, netmask:255.255.255.0
    inet6 address:2a02:8109:83c0:224c::5, broadcast:-, netmask:-
    inet6 address:2a02:8109:83c0:224c:3975, broadcast:-, netmask:-
    inet6 address:2a02:8109:83c0:224c:c685, broadcast:-, netmask:-
    inet6 address:fe80::c685:8ff:fe45:6412, broadcast:-, netmask:-
    packet address:c4:85:08:45:06:41, broadcast:ff:ff:ff:ff:ff:ff, netmask:-

docker0
    inet address:172.17.42.1, broadcast:172.17.42.1, netmask:255.255.0.0
    inet6 address:fe80::64f5:58ff:fef9:779a, broadcast:-, netmask:-
    packet address:66:f5:58:f9:77:9a, broadcast:ff:ff:ff:ff:ff:ff, netmask:-
"""

import socket

import psutil
from psutil._compat import print_


af_map = {
    getattr(socket, "AF_PACKET", 17): 'packet',
    socket.AF_INET: 'inet',
    socket.AF_INET6: 'inet6',
}


def main():
    for nic, addrs in psutil.net_if_addrs().items():
        print_("%s" % (nic))
        for addr in addrs:
            print_("    %s address:%s, broadcast:%s, netmask:%s" % (
                af_map.get(addr.family, addr.family),
                addr.address,
                addr.broadcast or "-",
                addr.netmask or "-",
            ))
        print_("")


if __name__ == '__main__':
    main()
