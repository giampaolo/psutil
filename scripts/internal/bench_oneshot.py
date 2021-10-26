#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A simple micro benchmark script which prints the speedup when using
Process.oneshot() ctx manager.
See: https://github.com/giampaolo/psutil/issues/799
"""

from __future__ import print_function, division
import sys
import timeit
import textwrap

import psutil


ITERATIONS = 1000

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
    names.append('uids')
    names.append('username')

if psutil.LINUX:
    names += [
        # 'memory_full_info',
        # 'memory_maps',
        'cpu_num',
        'cpu_times',
        'gids',
        'name',
        'num_ctx_switches',
        'num_threads',
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
        'memory_full_info',
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
        'memory_full_info',
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

setup = textwrap.dedent("""
    from __main__ import names
    import psutil

    def call_normal(funs):
        for fun in funs:
            fun()

    def call_oneshot(funs):
        with p.oneshot():
            for fun in funs:
                fun()

    p = psutil.Process()
    funs = [getattr(p, n) for n in names]
    """)


def main():
    print("%s methods involved on platform %r (%s iterations, psutil %s):" % (
        len(names), sys.platform, ITERATIONS, psutil.__version__))
    for name in sorted(names):
        print("    " + name)

    # "normal" run
    elapsed1 = timeit.timeit(
        "call_normal(funs)", setup=setup, number=ITERATIONS)
    print("normal:  %.3f secs" % elapsed1)

    # "one shot" run
    elapsed2 = timeit.timeit(
        "call_oneshot(funs)", setup=setup, number=ITERATIONS)
    print("onshot:  %.3f secs" % elapsed2)

    # done
    if elapsed2 < elapsed1:
        print("speedup: +%.2fx" % (elapsed1 / elapsed2))
    elif elapsed2 > elapsed1:
        print("slowdown: -%.2fx" % (elapsed2 / elapsed1))
    else:
        print("same speed")


if __name__ == '__main__':
    main()
