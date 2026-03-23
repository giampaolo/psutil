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

ITERATIONS = 1000
PID = os.getpid()

# The list of Process methods which gets collected in one shot and
# as such get advantage of the speedup.
names = [
    'cpu_times',
    'cpu_percent',
    'memory_info',
    'memory_percent',
    'ppid',
    'parent',
]

if psutil.POSIX:
    names.extend(('uids', 'username'))

if psutil.LINUX:
    names += [
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
    names = [
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
        names.append('cpu_num')
elif psutil.SUNOS:
    names += [
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
    names += [
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
    names += [
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

names = sorted(set(names))

setup_code = textwrap.dedent("""
    from __main__ import names
    import psutil

    def call_normal(funs):
        for fun in funs:
            fun()

    def call_oneshot(funs):
        with p.oneshot():
            for fun in funs:
                fun()

    p = psutil.Process({})
    funs = [getattr(p, n) for n in names]
    """)


def parse_cli():
    global ITERATIONS, PID
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("-i", "--iterations", type=int, default=ITERATIONS)
    parser.add_argument("-p", "--pid", type=int, default=PID)
    args = parser.parse_args()
    ITERATIONS = args.iterations
    PID = args.pid


def main():
    parse_cli()
    print(
        f"{len(names)} methods involved on platform"
        f" {sys.platform!r} ({ITERATIONS} iterations, psutil"
        f" {psutil.__version__}):"
    )
    for name in sorted(names):
        print("    " + name)

    # "normal" run
    setup = setup_code.format(PID)
    elapsed1 = timeit.timeit(
        "call_normal(funs)", setup=setup, number=ITERATIONS
    )
    print(f"normal:  {elapsed1:.3f} secs")

    # "one shot" run
    elapsed2 = timeit.timeit(
        "call_oneshot(funs)", setup=setup, number=ITERATIONS
    )
    print(f"onshot:  {elapsed2:.3f} secs")

    # done
    if elapsed2 < elapsed1:
        print(f"speedup: +{elapsed1 / elapsed2:.2f}x")
    elif elapsed2 > elapsed1:
        print(f"slowdown: -{elapsed2 / elapsed1:.2f}x")
    else:
        print("same speed")


if __name__ == '__main__':
    main()
