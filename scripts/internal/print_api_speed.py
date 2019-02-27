#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Benchmark all API calls.

$ make print_api_speed
SYSTEM APIS               SECONDS
----------------------------------
boot_time                 0.000140
cpu_count                 0.000016
cpu_count (cores)         0.000312
cpu_freq                  0.000811
cpu_percent               0.000138
cpu_stats                 0.000165
cpu_times                 0.000140
...

PROCESS APIS              SECONDS
----------------------------------
children                  0.007246
cmdline                   0.000069
connections               0.000072
cpu_affinity              0.000012
cpu_num                   0.000035
cpu_percent               0.000042
cpu_times                 0.000031
"""

from __future__ import print_function, division
from timeit import default_timer as timer
import argparse
import inspect
import os

import psutil
from scriptutils import hilite


SORT_BY_TIME = False if psutil.POSIX else True
TOP_SLOWEST = 7
timings = []
templ = "%-25s %s"


def print_timings():
    slower = []
    timings.sort(key=lambda x: x[1 if SORT_BY_TIME else 0])
    for x in sorted(timings, key=lambda x: x[1], reverse=1)[:TOP_SLOWEST]:
        slower.append(x[0])
    while timings[:]:
        title, elapsed = timings.pop(0)
        s = templ % (title, "%f" % elapsed)
        if title in slower:
            s = hilite(s, ok=False)
        print(s)


def timecall(title, fun, *args, **kw):
    t = timer()
    fun(*args, **kw)
    elapsed = timer() - t
    timings.append((title, elapsed))


def titlestr(s):
    return hilite(s, ok=None, bold=True)


def run():
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

    print(titlestr(templ % ("SYSTEM APIS", "SECONDS")))
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
    print(titlestr(templ % ("PROCESS APIS", "SECONDS")))
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


def main():
    global SORT_BY_TIME, TOP_SLOWEST
    parser = argparse.ArgumentParser(description='Benchmark all API calls')
    parser.add_argument('-t', '--time', required=False, default=SORT_BY_TIME,
                        action='store_true', help="sort by timings")
    parser.add_argument('-s', '--slowest', required=False, default=TOP_SLOWEST,
                        help="highlight the top N slowest APIs")
    args = parser.parse_args()
    SORT_BY_TIME = bool(args.time)
    TOP_SLOWEST = int(args.slowest)
    run()


if __name__ == '__main__':
    main()
