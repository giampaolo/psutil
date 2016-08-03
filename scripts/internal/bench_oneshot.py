#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A simple micro benchmark script which prints the speedup when using
Process.oneshot() ctx manager.
See: https://github.com/giampaolo/psutil/issues/799
"""

import sys
import time

import psutil


# The list of Process methods which gets collected in one shot and
# as such get advantage of the speedup.
if psutil.LINUX:
    names = ["name", "terminal", "cpu_times", "cpu_percent", "create_time",
             "status", "ppid", "num_ctx_switches", "num_threads", "uids",
             "gids"]
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

    print("%s methods involved on platform %r" % (len(names), sys.platform))

    t = time.time()
    for x in range(1000):
        call(funs)
    elapsed1 = time.time() - t
    print("normal:  %.3f" % elapsed1)

    t = time.time()
    for x in range(1000):
        with p.oneshot():
            call(funs)
    elapsed2 = time.time() - t
    print("oneshot: %.3f" % elapsed2)

    print("speedup: +%.2fx" % (elapsed1 / elapsed2))


main()
