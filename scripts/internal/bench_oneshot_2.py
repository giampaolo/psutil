#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Same as bench_oneshot.py but uses perf module instead, which is
supposed to be more precise.
"""

import sys

import perf.text_runner

import psutil
from bench_oneshot import names


p = psutil.Process()
funs = [getattr(p, n) for n in names]


def call_normal(funs):
    for fun in funs:
        fun()


def call_oneshot(funs):
    with p.oneshot():
        for fun in funs:
            fun()


def prepare_cmd(runner, cmd):
    cmd.append(runner.args.benchmark)


def main():
    runner = perf.text_runner.TextRunner(name='psutil')
    runner.argparser.add_argument('benchmark', choices=('normal', 'oneshot'))
    runner.prepare_subprocess_args = prepare_cmd

    args = runner.parse_args()
    if not args.worker:
        print("%s methods involved on platform %r:" % (
            len(names), sys.platform))
        for name in sorted(names):
            print("    " + name)

    if args.benchmark == 'normal':
        runner.bench_func(call_normal, funs)
    else:
        runner.bench_func(call_oneshot, funs)

main()
