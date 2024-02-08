#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Benchmark all API calls and print them from fastest to slowest.

$ make print_api_speed
SYSTEM APIS                NUM CALLS      SECONDS
-------------------------------------------------
disk_usage                       300      0.00157
cpu_count                        300      0.00255
pid_exists                       300      0.00792
cpu_times                        300      0.01044
boot_time                        300      0.01136
cpu_percent                      300      0.01290
cpu_times_percent                300      0.01515
virtual_memory                   300      0.01594
users                            300      0.01964
net_io_counters                  300      0.02027
cpu_stats                        300      0.02034
net_if_addrs                     300      0.02962
swap_memory                      300      0.03209
sensors_battery                  300      0.05186
pids                             300      0.07954
net_if_stats                     300      0.09321
disk_io_counters                 300      0.09406
cpu_count (cores)                300      0.10293
disk_partitions                  300      0.10345
cpu_freq                         300      0.20817
sensors_fans                     300      0.63476
sensors_temperatures             231      2.00039
process_iter (all)               171      2.01300
net_connections                   97      2.00206

PROCESS APIS               NUM CALLS      SECONDS
-------------------------------------------------
create_time                      300      0.00009
exe                              300      0.00015
nice                             300      0.00057
ionice                           300      0.00091
cpu_affinity                     300      0.00091
cwd                              300      0.00151
num_fds                          300      0.00391
memory_info                      300      0.00597
memory_percent                   300      0.00648
io_counters                      300      0.00707
name                             300      0.00894
status                           300      0.00900
ppid                             300      0.00906
num_threads                      300      0.00932
cpu_num                          300      0.00933
num_ctx_switches                 300      0.00943
uids                             300      0.00979
gids                             300      0.01002
cpu_times                        300      0.01008
cmdline                          300      0.01009
terminal                         300      0.01059
is_running                       300      0.01063
threads                          300      0.01209
connections                      300      0.01276
cpu_percent                      300      0.01463
open_files                       300      0.01630
username                         300      0.01655
environ                          300      0.02250
memory_full_info                 300      0.07066
memory_maps                      300      0.74281
"""

from __future__ import division
from __future__ import print_function

import argparse
import inspect
import os
import sys
from timeit import default_timer as timer

import psutil
from psutil._common import print_color


TIMES = 300
timings = []
templ = "%-25s %10s   %10s"


def print_header(what):
    s = templ % (what, "NUM CALLS", "SECONDS")
    print_color(s, color=None, bold=True)
    print("-" * len(s))


def print_timings():
    timings.sort(key=lambda x: (x[1], -x[2]), reverse=True)
    i = 0
    while timings[:]:
        title, times, elapsed = timings.pop(0)
        s = templ % (title, str(times), "%.5f" % elapsed)
        if i > len(timings) - 5:
            print_color(s, color="red")
        else:
            print(s)


def timecall(title, fun, *args, **kw):
    print("%-50s" % title, end="")
    sys.stdout.flush()
    t = timer()
    for n in range(TIMES):
        fun(*args, **kw)
        elapsed = timer() - t
        if elapsed > 2:
            break
    print("\r", end="")
    sys.stdout.flush()
    timings.append((title, n + 1, elapsed))


def set_highest_priority():
    """Set highest CPU and I/O priority (requires root)."""
    p = psutil.Process()
    if psutil.WINDOWS:
        p.nice(psutil.HIGH_PRIORITY_CLASS)
    else:
        p.nice(-20)

    if psutil.LINUX:
        p.ionice(psutil.IOPRIO_CLASS_RT, value=7)
    elif psutil.WINDOWS:
        p.ionice(psutil.IOPRIO_HIGH)


def main():
    global TIMES

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('-t', '--times', type=int, default=TIMES)
    args = parser.parse_args()
    TIMES = args.times
    assert TIMES > 1, TIMES

    try:
        set_highest_priority()
    except psutil.AccessDenied:
        prio_set = False
    else:
        prio_set = True

    # --- system

    public_apis = []
    ignore = [
        'wait_procs',
        'process_iter',
        'win_service_get',
        'win_service_iter',
    ]
    if psutil.MACOS:
        ignore.append('net_connections')  # raises AD
    for name in psutil.__all__:
        obj = getattr(psutil, name, None)
        if inspect.isfunction(obj):
            if name not in ignore:
                public_apis.append(name)

    print_header("SYSTEM APIS")
    for name in public_apis:
        fun = getattr(psutil, name)
        args = ()
        if name == 'pid_exists':
            args = (os.getpid(),)
        elif name == 'disk_usage':
            args = (os.getcwd(),)
        timecall(name, fun, *args)
    timecall('cpu_count (cores)', psutil.cpu_count, logical=False)
    timecall('process_iter (all)', lambda: list(psutil.process_iter()))
    print_timings()

    # --- process
    print()
    print_header("PROCESS APIS")
    ignore = [
        'send_signal',
        'suspend',
        'resume',
        'terminate',
        'kill',
        'wait',
        'as_dict',
        'parent',
        'parents',
        'memory_info_ex',
        'oneshot',
        'pid',
        'rlimit',
        'children',
    ]
    if psutil.MACOS:
        ignore.append('memory_maps')  # XXX
    p = psutil.Process()
    for name in sorted(dir(p)):
        if not name.startswith('_') and name not in ignore:
            fun = getattr(p, name)
            timecall(name, fun)
    print_timings()

    if not prio_set:
        msg = "\nWARN: couldn't set highest process priority "
        msg += "(requires root)"
        print_color(msg, "red")


if __name__ == '__main__':
    main()
