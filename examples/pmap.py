#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of 'pmap' utility on Linux, 'vmmap' on OSX and 'procstat -v' on BSD.
Report memory map of a process.

$ python examples/pmap.py 32402
pid=32402, name=hg
Address                 RSS  Mode    Mapping
0000000000400000      1200K  r-xp    /usr/bin/python2.7
0000000000838000         4K  r--p    /usr/bin/python2.7
0000000000839000       304K  rw-p    /usr/bin/python2.7
00000000008ae000        68K  rw-p    [anon]
000000000275e000      5396K  rw-p    [heap]
00002b29bb1e0000       124K  r-xp    /lib/x86_64-linux-gnu/ld-2.17.so
00002b29bb203000         8K  rw-p    [anon]
00002b29bb220000       528K  rw-p    [anon]
00002b29bb2d8000       768K  rw-p    [anon]
00002b29bb402000         4K  r--p    /lib/x86_64-linux-gnu/ld-2.17.so
00002b29bb403000         8K  rw-p    /lib/x86_64-linux-gnu/ld-2.17.so
00002b29bb405000        60K  r-xp    /lib/x86_64-linux-gnu/libpthread-2.17.so
00002b29bb41d000         0K  ---p    /lib/x86_64-linux-gnu/libpthread-2.17.so
00007fff94be6000        48K  rw-p    [stack]
00007fff94dd1000         4K  r-xp    [vdso]
ffffffffff600000         0K  r-xp    [vsyscall]
...
"""

import sys

import psutil


def main():
    if len(sys.argv) != 2:
        sys.exit('usage: pmap <pid>')
    p = psutil.Process(int(sys.argv[1]))
    print("pid=%s, name=%s" % (p.pid, p.name()))
    templ = "%-16s %10s  %-7s %s"
    print(templ % ("Address", "RSS", "Mode", "Mapping"))
    total_rss = 0
    for m in p.memory_maps(grouped=False):
        total_rss += m.rss
        print(templ % (
            m.addr.split('-')[0].zfill(16),
            str(m.rss / 1024) + 'K',
            m.perms,
            m.path))
    print("-" * 33)
    print(templ % ("Total", str(total_rss / 1024) + 'K', '', ''))

if __name__ == '__main__':
    main()
