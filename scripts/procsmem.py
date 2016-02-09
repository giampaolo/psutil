#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Show detailed memory usage about all (querable) processes.

Processes are sorted by their "USS" (Unique Set Size) memory, which is
probably the most representative metric for determining how much memory
is being used by a process.

This is similar to "smem" cmdline utility on Linux:
https://www.selenic.com/smem/
"""

from __future__ import print_function
import sys

import psutil


if not hasattr(psutil.Process, "memory_addrspace_info"):
    sys.exit("platform not supported")


def convert_bytes(n):
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i + 1) * 10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.1f%s' % (value, s)
    return "%sB" % n


def main():
    ad_pids = []
    procs = []
    for p in psutil.process_iter():
        try:
            mem_addrspace = p.memory_addrspace_info()
            info = p.as_dict(attrs=["cmdline", "username", "memory_info"])
        except psutil.AccessDenied:
            ad_pids.append(p.pid)
        except psutil.NoSuchProcess:
            pass
        else:
            p._uss = mem_addrspace.uss
            if not p._uss:
                continue
            p._pss = getattr(mem_addrspace, "pss", "")
            p._swap = getattr(mem_addrspace, "swap", "")
            p._info = info
            procs.append(p)

    procs.sort(key=lambda p: p._uss)
    templ = "%-7s %-7s %-30s %7s %7s %7s %7s"
    print(templ % ("PID", "User", "Cmdline", "USS", "PSS", "Swap", "RSS"))
    print("=" * 78)
    for p in procs:
        line = templ % (
            p.pid,
            p._info["username"][:7],
            " ".join(p._info["cmdline"])[:30],
            convert_bytes(p._uss),
            convert_bytes(p._pss),
            convert_bytes(p._swap),
            convert_bytes(p._info['memory_info'].rss),
        )
        print(line)
    if ad_pids:
        print("warning: access denied for %s pids" % (len(ad_pids)),
              file=sys.stderr)

if __name__ == '__main__':
    sys.exit(main())
