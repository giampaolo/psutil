#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
List all mounted disk partitions a-la "df -h" command.
"""

import sys
import os
import psutil
from psutil._compat import print_

def bytes2human(n):
    # http://code.activestate.com/recipes/578019
    # >>> bytes2human(10000)
    # '9.8K'
    # >>> bytes2human(100001221)
    # '95.4M'
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i+1)*10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.1f%s' % (value, s)
    return "%sB" % n


def main():
    templ = "%-17s %8s %8s %8s %5s%% %9s  %s"
    print_(templ % ("Device", "Total", "Used", "Free", "Use ", "Type", "Mount"))
    for part in psutil.disk_partitions(all=False):
        if os.name == 'nt' and 'cdrom' in part.opts:
            # may raise ENOENT if there's no cd-rom in the drive
            continue
        usage = psutil.disk_usage(part.mountpoint)
        print_(templ % (part.device,
                        bytes2human(usage.total),
                        bytes2human(usage.used),
                        bytes2human(usage.free),
                        int(usage.percent),
                        part.fstype,
                        part.mountpoint))

if __name__ == '__main__':
    sys.exit(main())
