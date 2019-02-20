#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A simple micro benchmark script which tests the speedup introduced in:
https://github.com/giampaolo/psutil/pull/1422/
"""

from __future__ import print_function
import sys
import timeit

import psutil


ITERATIONS = 10000
apis = [
    'psutil.boot_time()',
    'psutil.disk_io_counters()',
    'psutil.cpu_count(logical=False)',
    'psutil.cpu_count(logical=True)',
    'psutil.cpu_times(percpu=True)',
    'psutil.users()',
    'psutil.cpu_stats()',
    # 'psutil.net_connections(kind="inet4")',  # slow
    'proc.ionice()',
    'proc.ionice(0)',
    # 'proc.open_files()',  # slow
]
apis = sorted(set(apis))
setup = "import psutil; proc = psutil.Process()"


def main():
    if not psutil.WINDOWS:
        sys.exit("Windows only")
    for api in apis:
        elapsed = timeit.timeit(api, setup=setup, number=ITERATIONS)
        print("%-40s %.3f" % (api, elapsed))


if __name__ == '__main__':
    main()
