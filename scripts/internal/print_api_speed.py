#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Benchmark all API calls.

$ make print_api_speed
SYSTEM APIS               SECONDS
----------------------------------
cpu_count                 0.000014
disk_usage                0.000027
cpu_times                 0.000037
cpu_percent               0.000045
...

PROCESS APIS              SECONDS
----------------------------------
create_time               0.000001
nice                      0.000005
cwd                       0.000011
cpu_affinity              0.000011
ionice                    0.000013
...
"""

from __future__ import print_function, division
from timeit import default_timer as timer
import inspect
import os

import psutil
from psutil._common import print_color


timings = []
templ = "%-25s %s"


def print_timings():
    timings.sort(key=lambda x: x[1])
    i = 0
    while timings[:]:
        title, elapsed = timings.pop(0)
        s = templ % (title, "%f" % elapsed)
        if i > len(timings) - 5:
            print_color(s, color="red")
        else:
            print(s)


def timecall(title, fun, *args, **kw):
    t = timer()
    fun(*args, **kw)
    elapsed = timer() - t
    timings.append((title, elapsed))


def main():
    # --- system

    public_apis = []
    ignore = ['wait_procs', 'process_iter', 'win_service_get',
              'win_service_iter']
    if psutil.MACOS:
        ignore.append('net_connections')  # raises AD
    for name in psutil.__all__:
        obj = getattr(psutil, name, None)
        if inspect.isfunction(obj):
            if name not in ignore:
                public_apis.append(name)

    print_color(templ % ("SYSTEM APIS", "SECONDS"), color=None, bold=True)
    print("-" * 34)
    for name in public_apis:
        fun = getattr(psutil, name)
        args = ()
        if name == 'pid_exists':
            args = (os.getpid(), )
        elif name == 'disk_usage':
            args = (os.getcwd(), )
        timecall(name, fun, *args)
    timecall('cpu_count (cores)', psutil.cpu_count, logical=False)
    timecall('process_iter (all)', lambda: list(psutil.process_iter()))
    print_timings()

    # --- process
    print("")
    print_color(templ % ("PROCESS APIS", "SECONDS"), color=None, bold=True)
    print("-" * 34)
    ignore = ['send_signal', 'suspend', 'resume', 'terminate', 'kill', 'wait',
              'as_dict', 'parent', 'parents', 'memory_info_ex', 'oneshot',
              'pid', 'rlimit']
    if psutil.MACOS:
        ignore.append('memory_maps')  # XXX
    p = psutil.Process()
    for name in sorted(dir(p)):
        if not name.startswith('_') and name not in ignore:
            fun = getattr(p, name)
            timecall(name, fun)
    print_timings()


if __name__ == '__main__':
    main()
