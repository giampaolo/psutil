#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A simple micro benchmark script which prints the speedup when using
Process.oneshot() ctx manager.
See: https://github.com/giampaolo/psutil/issues/799.
"""

import argparse
import os
import sys
import textwrap
import timeit

import psutil

TIMES = 1000
PID = os.getpid()

# The list of Process methods which gets collected in one shot and
# as such get advantage of the speedup.
NAMES = [
    'cpu_times',
    'cpu_percent',
    'memory_info',
    'memory_percent',
    'ppid',
    'parent',
]

if psutil.POSIX:
    NAMES.extend(('uids', 'username'))

if psutil.LINUX:
    NAMES += [
        # 'memory_footprint',
        # 'memory_maps',
        'cpu_num',
        'cpu_times',
        'gids',
        'memory_info_ex',
        'name',
        'num_ctx_switches',
        'num_threads',
        'num_threads',
        'page_faults',
        'ppid',
        'status',
        'terminal',
        'uids',
    ]
elif psutil.BSD:
    NAMES = [
        'cpu_times',
        'gids',
        'io_counters',
        'memory_footprint',
        'memory_info',
        'name',
        'num_ctx_switches',
        'ppid',
        'status',
        'terminal',
        'uids',
    ]
    if psutil.FREEBSD:
        NAMES.append('cpu_num')
elif psutil.SUNOS:
    NAMES += [
        'cmdline',
        'gids',
        'memory_footprint',
        'memory_info',
        'name',
        'num_threads',
        'ppid',
        'status',
        'terminal',
        'uids',
    ]
elif psutil.MACOS:
    NAMES += [
        'cpu_times',
        'create_time',
        'gids',
        'memory_info',
        'name',
        'num_ctx_switches',
        'num_threads',
        'ppid',
        'terminal',
        'uids',
    ]
elif psutil.WINDOWS:
    NAMES += [
        'num_ctx_switches',
        'num_threads',
        # dual implementation, called in case of AccessDenied
        'num_handles',
        'cpu_times',
        'create_time',
        'num_threads',
        'io_counters',
        'memory_info',
    ]

NAMES = sorted(set(NAMES))

setup_code = textwrap.dedent("""
    from __main__ import NAMES
    import psutil

    def call_normal(funs):
        for fun in funs:
            fun()

    def call_oneshot(funs):
        with p.oneshot():
            for fun in funs:
                fun()

    p = psutil.Process({})
    funs = [getattr(p, n) for n in NAMES]
    """)


def parse_cli():
    global TIMES, PID, NAMES
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("-i", "--times", type=int, default=TIMES)
    parser.add_argument("-p", "--pid", type=int, default=PID)
    parser.add_argument("-n", "--names", default=None, metavar="METHOD,METHOD")
    args = parser.parse_args()
    TIMES = args.times
    PID = args.pid
    if args.names:
        NAMES = sorted(set(args.names.split(",")))


def main():
    parse_cli()
    print(
        f"{len(NAMES)} methods pre-fetched by oneshot() on platform"
        f" {sys.platform!r} ({TIMES:,} times, psutil"
        f" {psutil.__version__}):\n"
    )
    for name in sorted(NAMES):
        print("  " + name)
        attr = getattr(psutil.Process, name, None)
        if attr is None or not callable(attr):
            raise ValueError(f"invalid name {name!r}")

    # "normal" run
    setup = setup_code.format(PID)
    elapsed1 = timeit.timeit("call_normal(funs)", setup=setup, number=TIMES)
    print(f"\nregular:  {elapsed1:.3f} secs")

    # "one shot" run
    elapsed2 = timeit.timeit("call_oneshot(funs)", setup=setup, number=TIMES)
    print(f"oneshot:  {elapsed2:.3f} secs")

    # done
    if elapsed2 < elapsed1:
        print(f"speedup:  +{elapsed1 / elapsed2:.2f}x")
    elif elapsed2 > elapsed1:
        print(f"slowdown:  -{elapsed2 / elapsed1:.2f}x")
    else:
        print("same speed")


if __name__ == '__main__':
    main()
