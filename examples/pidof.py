#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola', karthikrev. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""
A clone of 'pidof' cmdline utility.
$ pidof  /usr/bin/python
1140 1138 1136 1134 1133 1129 1127 1125 1121 1120 1119
"""

from __future__ import print_function
import psutil
import sys


def pidsof(pgm):
    pids = []
    # Iterate on all proccesses and find matching cmdline and get list of
    # corresponding PIDs
    for proc in psutil.process_iter():
        try:
            cmdline = proc.cmdline()
            pid = proc.pid
        except psutil.Error:
            continue
        if len(cmdline) > 0 and cmdline[0] == pgm:
            pids.append(str(pid))
    return pids


def main():
    if len(sys.argv) != 2:
        sys.exit('usage: %s pgm_name' % __file__)
    else:
        pgmname = sys.argv[1]
    pids = pidsof(pgmname)
    print(" ".join(pids))

if __name__ == '__main__':
    main()
