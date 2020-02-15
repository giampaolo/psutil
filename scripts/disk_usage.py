#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
List all mounted disk partitions a-la "df -h" command.

$ python scripts/disk_usage.py
Device               Total     Used     Free  Use %      Type  Mount
/dev/sdb3            18.9G    14.7G     3.3G    77%      ext4  /
/dev/sda6           345.9G    83.8G   244.5G    24%      ext4  /home
/dev/sda1           296.0M    43.1M   252.9M    14%      vfat  /boot/efi
/dev/sda2           600.0M   312.4M   287.6M    52%   fuseblk  /media/Recovery
"""

import sys
import os
import psutil
from psutil._common import bytes2human


def main():
    templ = "%-17s %8s %8s %8s %5s%% %9s  %s"
    print(templ % ("Device", "Total", "Used", "Free", "Use ", "Type",
                   "Mount"))
    for part in psutil.disk_partitions(all=False):
        if os.name == 'nt':
            if 'cdrom' in part.opts or part.fstype == '':
                # skip cd-rom drives with no disk in it; they may raise
                # ENOENT, pop-up a Windows GUI error for a non-ready
                # partition or just hang.
                continue
        usage = psutil.disk_usage(part.mountpoint)
        print(templ % (
            part.device,
            bytes2human(usage.total),
            bytes2human(usage.used),
            bytes2human(usage.free),
            int(usage.percent),
            part.fstype,
            part.mountpoint))


if __name__ == '__main__':
    sys.exit(main())
