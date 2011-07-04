#!/usr/bin/env python
# $Id

"""
List all mounted disk partitions a-la "df -h" command.
"""

import sys
import psutil

def convert_bytes(n):
    if n == 0:
        return "0B"
    symbols = ('k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i+1)*10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.1f%s' % (value, s)


def main():
    templ = "%-17s %8s %8s %8s %5s%% %9s  %s"
    print templ % ("Device", "Total", "Used", "Free", "Use ", "Type", "Mount")
    for part in psutil.disk_partitions(all=False):
        usage = psutil.disk_usage(part.mountpoint)
        print templ % (part.device,
                       convert_bytes(usage.total),
                       convert_bytes(usage.used),
                       convert_bytes(usage.free),
                       int(usage.percent),
                       part.fstype,
                       part.mountpoint)

if __name__ == '__main__':
    sys.exit(main())
