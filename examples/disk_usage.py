#!/usr/bin/env python

"""
List all mounted disk partitions a-la "df" command.
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
    print "Device       Total     Used     Free  Use %     Type  Mount"
    for part in psutil.disk_partitions(0):
        usage = psutil.disk_usage(part.mountpoint)
        print "%-9s %8s %8s %8s %5s%% %8s  %s" % (part.device,
                                                  convert_bytes(usage.total),
                                                  convert_bytes(usage.used),
                                                  convert_bytes(usage.free),
                                                  int(usage.percent),
                                                  part.fstype,
                                                  part.mountpoint)

if __name__ == '__main__':
    sys.exit(main())
