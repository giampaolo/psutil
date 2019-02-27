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
import os

import psutil


SORT_BY_NAME = 0  # <- toggle this
timings = []


def print_timings():
    timings.sort(key=lambda x: x[0 if SORT_BY_NAME else 1])
    while timings[:]:
        title, elapsed = timings.pop(0)
        print("    %-30s %f secs" % (title, elapsed))


def timecall(title, fun, *args, **kw):
    t = timer()
    fun(*args, **kw)
    elapsed = timer() - t
    timings.append((title, elapsed))


def main():
    print("SYSTEM APIS")
    timecall('cpu_count', psutil.cpu_count)
    timecall('cpu_count (cores)', psutil.cpu_count, logical=False)
    timecall('cpu_times', psutil.cpu_times)
    timecall('cpu_percent', psutil.cpu_percent, interval=0)
    timecall('cpu_times_percent', psutil.cpu_times_percent, interval=0)
    timecall('cpu_stats', psutil.cpu_stats)
    timecall('cpu_freq', psutil.cpu_freq)
    timecall('virtual_memory', psutil.virtual_memory)
    timecall('swap_memory', psutil.swap_memory)
    timecall('disk_partitions', psutil.disk_partitions)
    timecall('disk_usage', psutil.disk_usage, os.getcwd())
    timecall('disk_io_counters', psutil.disk_io_counters)
    timecall('net_io_counters', psutil.net_io_counters)
    timecall('net_connections', psutil.net_connections)
    timecall('net_if_addrs', psutil.net_if_addrs)
    timecall('net_if_stats', psutil.net_if_stats)
    timecall('sensors_temperatures', psutil.sensors_temperatures)
    timecall('sensors_fans', psutil.sensors_fans)
    timecall('sensors_battery', psutil.sensors_battery)
    timecall('boot_time', psutil.boot_time)
    timecall('users', psutil.users)
    timecall('pids', psutil.pids)
    timecall('pid_exists', psutil.pid_exists, os.getpid())
    timecall('process_iter (all)', lambda: list(psutil.process_iter()))
    print_timings()

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
