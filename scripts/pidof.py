#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola', karthikrev. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""A clone of 'pidof' cmdline utility.

$ pidof python
1140 1138 1136 1134 1133 1129 1127 1125 1121 1120 1119
"""

import sys

import psutil


def pidof(pgname):
    # search for matches in the process name and cmdline
    return [
        str(proc.pid)
        for proc in psutil.process_iter(['name', 'cmdline'])
        if proc.info["name"] == pgname
        or (proc.info["cmdline"] and proc.info["cmdline"][0] == pgname)
    ]


def main():
    if len(sys.argv) != 2:
        sys.exit(f"usage: {__file__} pgname")
    else:
        pgname = sys.argv[1]
    pids = pidof(pgname)
    if pids:
        print(" ".join(pids))


if __name__ == '__main__':
    main()
