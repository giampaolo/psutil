#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Same as bench_oneshot.py but uses perf module instead, which is
supposed to be more precise.
"""

import sys

import pyperf  # requires "pip install pyperf"

import psutil

p = psutil.Process()


def call_normal(funs):
    for fun in funs:
        fun()


def call_oneshot(funs):
    with p.oneshot():
        for fun in funs:
            fun()


def main():
    from bench_oneshot import names

    runner = pyperf.Runner()

    args = runner.parse_args()
    if not args.worker:
        print(
            f"{len(names)} methods involved on platform"
            f" {sys.platform!r} (psutil {psutil.__version__}):"
        )
        for name in sorted(names):
            print("    " + name)

    funs = [getattr(p, n) for n in names]
    runner.bench_func("normal", call_normal, funs)
    runner.bench_func("oneshot", call_oneshot, funs)


if __name__ == "__main__":
    main()
