#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A simple micro benchmark script which prints the speedup when using
Process.oneshot() ctx manager.
See: https://github.com/giampaolo/psutil/issues/799
"""

from __future__ import print_function
import sys
import time

import psutil


ITERATIONS = 1000

# The list of Process methods which gets collected in one shot and
# as such get advantage of the speedup.
if psutil.LINUX:
    names = (
        'cpu_percent',
        'cpu_times',
        'create_time',
        'gids',
        'name',
        'num_ctx_switches',
        'num_threads',
        'ppid',
        'status',
        'terminal',
        'uids',
    )
elif psutil.BSD:
    names = (
        'cpu_percent',
        'cpu_times',
        'create_time',
        'gids',
        'io_counters',
        'memory_full_info',
        'memory_info',
        'memory_percent',
        'num_ctx_switches',
        'ppid',
        'status',
        'terminal',
        'uids',
    )
elif psutil.SUNOS:
    names = (
        'cmdline',
        'create_time',
        'gids',
        'memory_full_info',
        'memory_info',
        'memory_percent',
        'name',
        'num_threads',
        'ppid',
        'status',
        'terminal',
        'uids',
    )
else:
    raise RuntimeError("platform %r not supported" % sys.platform)


def collect(p):
    return [getattr(p, n) for n in names]


def call(funs):
    for fun in funs:
        fun()


def main():
    p = psutil.Process()
    funs = collect(p)
    print("%s methods involved on platform %r (%s iterations):" % (
        len(names), sys.platform, ITERATIONS))
    for name in sorted(names):
        print("    " + name)

    # first "normal" run
    t = time.time()
    for x in range(ITERATIONS):
        call(funs)
    elapsed1 = time.time() - t
    print("normal:  %.3f secs" % elapsed1)

    # "one shot" run
    t = time.time()
    for x in range(ITERATIONS):
        with p.oneshot():
            call(funs)
    elapsed2 = time.time() - t
    print("oneshot: %.3f secs" % elapsed2)

    # done
    if elapsed2 < elapsed1:
        print("speedup: +%.2fx" % (elapsed1 / elapsed2))
    elif elapsed2 > elapsed1:
        print("slowdown: -%.2fx" % (elapsed1 / elapsed2))
    else:
        print("same speed")


main()
