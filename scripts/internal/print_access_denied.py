#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Helper script iterates over all processes and .
It prints how many AccessDenied exceptions are raised in total and
for what Process method.

$ make print-access-denied
API                  AD    Percent   Outcome
memory_info          0        0.0%   SUCCESS
uids                 0        0.0%   SUCCESS
cmdline              0        0.0%   SUCCESS
create_time          0        0.0%   SUCCESS
status               0        0.0%   SUCCESS
num_ctx_switches     0        0.0%   SUCCESS
username             0        0.0%   SUCCESS
ionice               0        0.0%   SUCCESS
memory_percent       0        0.0%   SUCCESS
gids                 0        0.0%   SUCCESS
cpu_times            0        0.0%   SUCCESS
nice                 0        0.0%   SUCCESS
pid                  0        0.0%   SUCCESS
cpu_percent          0        0.0%   SUCCESS
num_threads          0        0.0%   SUCCESS
cpu_num              0        0.0%   SUCCESS
ppid                 0        0.0%   SUCCESS
terminal             0        0.0%   SUCCESS
name                 0        0.0%   SUCCESS
threads              0        0.0%   SUCCESS
cpu_affinity         0        0.0%   SUCCESS
memory_maps          71      21.3%   ACCESS DENIED
memory_full_info     71      21.3%   ACCESS DENIED
exe                  174     52.1%   ACCESS DENIED
environ              238     71.3%   ACCESS DENIED
num_fds              238     71.3%   ACCESS DENIED
io_counters          238     71.3%   ACCESS DENIED
cwd                  238     71.3%   ACCESS DENIED
connections          238     71.3%   ACCESS DENIED
open_files           238     71.3%   ACCESS DENIED
--------------------------------------------------
Totals: access-denied=1744, calls=10020, processes=334
"""

from __future__ import print_function, division
from collections import defaultdict
import time

import psutil
from psutil._common import print_color


def main():
    # collect
    tot_procs = 0
    tot_ads = 0
    tot_calls = 0
    signaler = object()
    d = defaultdict(int)
    start = time.time()
    for p in psutil.process_iter(attrs=[], ad_value=signaler):
        tot_procs += 1
        for methname, value in p.info.items():
            tot_calls += 1
            if value is signaler:
                tot_ads += 1
                d[methname] += 1
            else:
                d[methname] += 0
    elapsed = time.time() - start

    # print
    templ = "%-20s %-5s %-9s %s"
    s = templ % ("API", "AD", "Percent", "Outcome")
    print_color(s, color=None, bold=True)
    for methname, ads in sorted(d.items(), key=lambda x: (x[1], x[0])):
        perc = (ads / tot_procs) * 100
        outcome = "SUCCESS" if not ads else "ACCESS DENIED"
        s = templ % (methname, ads, "%6.1f%%" % perc, outcome)
        print_color(s, "red" if ads else None)
    tot_perc = round((tot_ads / tot_calls) * 100, 1)
    print("-" * 50)
    print("Totals: access-denied=%s (%s%%), calls=%s, processes=%s, "
          "elapsed=%ss" % (tot_ads, tot_perc, tot_calls, tot_procs,
                           round(elapsed, 2)))


if __name__ == '__main__':
    main()
