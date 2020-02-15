#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Show detailed memory usage about all (querable) processes.

Processes are sorted by their "USS" (Unique Set Size) memory, which is
probably the most representative metric for determining how much memory
is actually being used by a process.

This is similar to "smem" cmdline utility on Linux:
https://www.selenic.com/smem/

Author: Giampaolo Rodola' <g.rodola@gmail.com>

~/svn/psutil$ ./scripts/procsmem.py
PID     User    Cmdline                            USS     PSS    Swap     RSS
==============================================================================
...
3986    giampao /usr/bin/python3 /usr/bin/indi   15.3M   16.6M      0B   25.6M
3906    giampao /usr/lib/ibus/ibus-ui-gtk3       17.6M   18.1M      0B   26.7M
3991    giampao python /usr/bin/hp-systray -x    19.0M   23.3M      0B   40.7M
3830    giampao /usr/bin/ibus-daemon --daemoni   19.0M   19.0M      0B   21.4M
20529   giampao /opt/sublime_text/plugin_host    19.9M   20.1M      0B   22.0M
3990    giampao nautilus -n                      20.6M   29.9M      0B   50.2M
3898    giampao /usr/lib/unity/unity-panel-ser   27.1M   27.9M      0B   37.7M
4176    giampao /usr/lib/evolution/evolution-c   35.7M   36.2M      0B   41.5M
20712   giampao /usr/bin/python -B /home/giamp   45.6M   45.9M      0B   49.4M
3880    giampao /usr/lib/x86_64-linux-gnu/hud/   51.6M   52.7M      0B   61.3M
20513   giampao /opt/sublime_text/sublime_text   65.8M   73.0M      0B   87.9M
3976    giampao compiz                          115.0M  117.0M      0B  130.9M
32486   giampao skype                           145.1M  147.5M      0B  149.6M
"""

from __future__ import print_function
import sys

import psutil


if not (psutil.LINUX or psutil.MACOS or psutil.WINDOWS):
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
        with p.oneshot():
            try:
                mem = p.memory_full_info()
                info = p.as_dict(["cmdline", "username"])
            except psutil.AccessDenied:
                ad_pids.append(p.pid)
            except psutil.NoSuchProcess:
                pass
            else:
                p._uss = mem.uss
                p._rss = mem.rss
                if not p._uss:
                    continue
                p._pss = getattr(mem, "pss", "")
                p._swap = getattr(mem, "swap", "")
                p._info = info
                procs.append(p)

    procs.sort(key=lambda p: p._uss)
    templ = "%-7s %-7s %-30s %7s %7s %7s %7s"
    print(templ % ("PID", "User", "Cmdline", "USS", "PSS", "Swap", "RSS"))
    print("=" * 78)
    for p in procs[:86]:
        line = templ % (
            p.pid,
            p._info["username"][:7] if p._info["username"] else "",
            " ".join(p._info["cmdline"])[:30],
            convert_bytes(p._uss),
            convert_bytes(p._pss) if p._pss != "" else "",
            convert_bytes(p._swap) if p._swap != "" else "",
            convert_bytes(p._rss),
        )
        print(line)
    if ad_pids:
        print("warning: access denied for %s pids" % (len(ad_pids)),
              file=sys.stderr)


if __name__ == '__main__':
    sys.exit(main())
