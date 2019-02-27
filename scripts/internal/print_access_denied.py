#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Helper script iterates over all processes and .
It prints how many AccessDenied exceptions are raised in total and
for what Process method.

$ make print-access-denied
username             0     0.0%   SUCCESS
cpu_num              0     0.0%   SUCCESS
num_ctx_switches     0     0.0%   SUCCESS
pid                  0     0.0%   SUCCESS
cmdline              0     0.0%   SUCCESS
create_time          0     0.0%   SUCCESS
ionice               0     0.0%   SUCCESS
cpu_percent          0     0.0%   SUCCESS
terminal             0     0.0%   SUCCESS
ppid                 0     0.0%   SUCCESS
nice                 0     0.0%   SUCCESS
status               0     0.0%   SUCCESS
cpu_times            0     0.0%   SUCCESS
memory_info          0     0.0%   SUCCESS
threads              0     0.0%   SUCCESS
uids                 0     0.0%   SUCCESS
num_threads          0     0.0%   SUCCESS
name                 0     0.0%   SUCCESS
gids                 0     0.0%   SUCCESS
cpu_affinity         0     0.0%   SUCCESS
memory_percent       0     0.0%   SUCCESS
memory_full_info     70   20.8%   ACCESS DENIED
memory_maps          70   20.8%   ACCESS DENIED
exe                  174  51.8%   ACCESS DENIED
connections          237  70.5%   ACCESS DENIED
num_fds              237  70.5%   ACCESS DENIED
cwd                  237  70.5%   ACCESS DENIED
io_counters          237  70.5%   ACCESS DENIED
open_files           237  70.5%   ACCESS DENIED
environ              237  70.5%   ACCESS DENIED
-----------------------------------------------
total:                1736 (336 total processes)
"""

from __future__ import print_function, division
from collections import defaultdict

import psutil
from scriptutils import hilite


def main():
    tot_procs = 0
    tot_ads = 0
    signaler = object()
    d = defaultdict(int)
    for p in psutil.process_iter(attrs=[], ad_value=signaler):
        tot_procs += 1
        for methname, value in p.info.items():
            if value is signaler:
                tot_ads += 1
                d[methname] += 1
            else:
                d[methname] += 0

    for methname, ads in sorted(d.items(), key=lambda x: x[1]):
        perc = (ads / tot_procs) * 100
        s = "%-20s %-3s %5.1f%%   " % (methname, ads, perc)
        if not ads:
            s += "SUCCESS"
            s = hilite(s, ok=True)
        else:
            s += "ACCESS DENIED"
            s = hilite(s, ok=False)
        print(s)
    print("-----------------------------------------------")
    print("total: %19s (%s total processes)" % (tot_ads, tot_procs))


if __name__ == '__main__':
    main()
