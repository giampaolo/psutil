#!/usr/bin/env python

"""
A clone of 'pidof' cmdline utility.
$ pidof  /usr/bin/python
1140 1138 1136 1134 1133 1129 1127 1125 1121 1120 1119
"""

import psutil
import sys


def pidsof(pgm):
    pids = []
    for proc in psutil.process_iter():
        process = proc.as_dict()
        if len(process['cmdline']) > 0 and process['cmdline'][0] == pgm:
            pids.append(str(process['pid']))
    return pids


def main():
    if len(sys.argv) != 2:
        sys.exit('usage: %s pgm_name' % __file__)
    else:
        pgmname = sys.argv[1]
    pids = pidsof(pgmname)
    print " ".join(pids)

if __name__ == '__main__':
    main()
