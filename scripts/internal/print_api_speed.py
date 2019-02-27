#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Benchmark all API calls.

$ python scripts/internal/print_api_speed.py
SYSTEM APIS
    boot_time                      0.000127 secs
    cpu_count                      0.000034 secs
    cpu_count (cores)              0.000279 secs
    cpu_freq                       0.000438 secs
    ...

PROCESS APIS
    cmdline                        0.000027 secs
    connections                    0.000056 secs
    cpu_affinity                   0.000014 secs
    cpu_num                        0.000054 secs
    cpu_percent                    0.000077 secs
    ...
"""

from __future__ import print_function, division
from timeit import default_timer as timer
import inspect
import os

import psutil


SORT_BY_NAME = 0  # <- toggle this
timings = []


def print_timings():
    timings.sort(key=lambda x: x[0 if SORT_BY_NAME else 1])
    while timings[:]:
        title, elapsed = timings.pop(0)
        print("%-30s %f secs" % (title, elapsed))


def timecall(title, fun, *args, **kw):
    t = timer()
    fun(*args, **kw)
    elapsed = timer() - t
    timings.append((title, elapsed))


def main():
    # --- system

    public_apis = []
    for name in psutil.__all__:
        obj = getattr(psutil, name, None)
        if inspect.isfunction(obj):
            if name not in ('wait_procs', 'process_iter'):
                public_apis.append(name)

    print("SYSTEM APIS")
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

    print("\nPROCESS APIS")
    ignore = ['send_signal', 'suspend', 'resume', 'terminate', 'kill', 'wait',
              'as_dict', 'parent', 'parents', 'memory_info_ex', 'oneshot',
              'pid', 'rlimit']
    p = psutil.Process()
    for name in sorted(dir(p)):
        if not name.startswith('_') and name not in ignore:
            fun = getattr(p, name)
            timecall(name, fun)
    print_timings()


if __name__ == '__main__':
    main()
