#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola', karthikrev. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""
A clone of 'pidof' cmdline utility.
$ pidof python
1140 1138 1136 1134 1133 1129 1127 1125 1121 1120 1119
"""

from __future__ import print_function
import psutil
import sys


def pidof(pgname):
    pids = []
    for proc in psutil.process_iter():
        # search for matches in the process name and cmdline
        try:
            name = proc.name()
        except psutil.Error:
            pass
        else:
            if name == pgname:
                pids.append(str(proc.pid))
                continue

        try:
            cmdline = proc.cmdline()
        except psutil.Error:
            pass
        else:
            if cmdline and cmdline[0] == pgname:
                pids.append(str(proc.pid))

    return pids


def main():
    if len(sys.argv) != 2:
        sys.exit('usage: %s pgname' % __file__)
    else:
        pgname = sys.argv[1]
    pids = pidof(pgname)
    if pids:
        print(" ".join(pids))

if __name__ == '__main__':
    main()
