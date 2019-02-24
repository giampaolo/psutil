#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Helper script which tries to access all info of all running processes.
It prints how many AccessDenied exceptions are raised in total and
for each Process method.
"""

from __future__ import print_function, division
from collections import defaultdict
import sys

import psutil


def term_supports_colors(file=sys.stdout):
    try:
        import curses
        assert file.isatty()
        curses.setupterm()
        assert curses.tigetnum("colors") > 0
    except Exception:
        return False
    else:
        return True


COLORS = term_supports_colors()


def hilite(s, ok=True, bold=False):
    """Return an highlighted version of 'string'."""
    if not COLORS:
        return s
    attr = []
    if ok is None:  # no color
        pass
    elif ok:   # green
        attr.append('32')
    else:   # red
        attr.append('31')
    if bold:
        attr.append('1')
    return '\x1b[%sm%s\x1b[0m' % (';'.join(attr), s)


def main():
    tot_procs = 0
    tot_ads = 0
    signaler = object()
    d = defaultdict(int)
    for p in psutil.process_iter(attrs=[], ad_value=signaler):
        tot_procs += 1
        for methname, value in p.info.items():
            if value is signaler:
                tot_ads += 1
                d[methname] += 1
            else:
                d[methname] += 0

    for methname, ads in sorted(d.items(), key=lambda x: x[1]):
        perc = (ads / tot_procs) * 100
        s = "%-20s %-3s %5.1f%%   " % (methname, ads, perc)
        if not ads:
            s += "SUCCESS"
            s = hilite(s, ok=True)
        else:
            s += "ACCESS DENIED"
            s = hilite(s, ok=False)
        print(s)
    print("--------------------------")
    print("total: %19s (%s total processes)" % (tot_ads, tot_procs))


if __name__ == '__main__':
    main()
