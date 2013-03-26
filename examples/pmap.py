#!/usr/bin/env python

# Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of 'pmap' utility on Linux, 'vmmap' on OSX and 'procstat -v' on BSD.
Report memory map of a process.
"""

import sys

import psutil
from psutil._compat import print_

def main():
    if len(sys.argv) != 2:
        sys.exit('usage: pmap pid')
    p = psutil.Process(int(sys.argv[1]))
    print_("pid=%s, name=%s" % (p.pid, p.name))
    templ = "%-16s %10s  %-7s %s"
    print_(templ % ("Address", "RSS", "Mode", "Mapping"))
    total_rss = 0
    for m in p.get_memory_maps(grouped=False):
        total_rss += m.rss
        print_(templ % (m.addr.split('-')[0].zfill(16),
                        str(m.rss / 1024) + 'K' ,
                        m.perms,
                        m.path))
    print_("-" * 33)
    print_(templ % ("Total", str(total_rss / 1024) + 'K', '', ''))

if __name__ == '__main__':
    main()
