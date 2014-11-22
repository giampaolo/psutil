#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Similar to 'ps aux --forest' on Linux, prints the process list
as a tree structure.

$ python examples/pstree.py
0 ?
├─ 1 init
│ ├─ 289 cgmanager
│ ├─ 616 upstart-socket-bridge
│ ├─ 628 rpcbind
│ ├─ 892 upstart-file-bridge
│ ├─ 907 dbus-daemon
│ ├─ 978 avahi-daemon
│ │ └─ 979 avahi-daemon
│ ├─ 987 NetworkManager
│ │ ├─ 2242 dnsmasq
│ │ ├─ 20794 dhclient
│ │ └─ 20796 dhclient
...
"""

from __future__ import print_function
import collections
import psutil
import sys


def print_tree(parent, tree, indent=''):
    sys.stdout.flush()
    try:
        name = psutil.Process(parent).name()
    except psutil.Error:
        name = "?"
    print(parent, name)
    if parent not in tree:
        return
    children = tree[parent][:-1]
    for child in children:
        sys.stdout.write(indent + "├─ ")
        print_tree(child, tree, indent + "│ ")
    child = tree[parent][-1]
    sys.stdout.write(indent + "└─ ")
    print_tree(child, tree, indent + "  ")


def main():
    # construct a dict where 'values' are all the processes
    # having 'key' as their parent
    tree = collections.defaultdict(list)
    for p in psutil.process_iter():
        try:
            tree[p.ppid()].append(p.pid)
        except psutil.NoSuchProcess:
            pass
    print_tree(min(tree), tree)


if __name__ == '__main__':
    main()
