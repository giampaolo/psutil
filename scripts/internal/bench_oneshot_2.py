#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Same as bench_oneshot.py but uses perf module instead, which is
supposed to be more precise.
"""

import sys

import pyperf  # requires "pip install pyperf"

import psutil
from bench_oneshot import names


p = psutil.Process()
funs = [getattr(p, n) for n in names]


def call_normal():
    for fun in funs:
        fun()


def call_oneshot():
    with p.oneshot():
        for fun in funs:
            fun()


def add_cmdline_args(cmd, args):
    cmd.append(args.benchmark)


def main():
    runner = pyperf.Runner()

    args = runner.parse_args()
    if not args.worker:
        print("%s methods involved on platform %r (psutil %s):" % (
            len(names), sys.platform, psutil.__version__))
        for name in sorted(names):
            print("    " + name)

    runner.bench_func("normal", call_normal)
    runner.bench_func("oneshot", call_oneshot)


main()
