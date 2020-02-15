#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of 'ps aux'.

$ python scripts/ps.py
USER         PID  %MEM     VSZ     RSS  NICE STATUS  START   TIME  CMDLINE
root           1   0.0  220.9M    6.5M        sleep  Mar27  09:10  /lib/systemd
root           2   0.0    0.0B    0.0B        sleep  Mar27  00:00  kthreadd
root           4   0.0    0.0B    0.0B   -20   idle  Mar27  00:00  kworker/0:0H
root           6   0.0    0.0B    0.0B   -20   idle  Mar27  00:00  mm_percpu_wq
root           7   0.0    0.0B    0.0B        sleep  Mar27  00:06  ksoftirqd/0
root           8   0.0    0.0B    0.0B         idle  Mar27  03:32  rcu_sched
root           9   0.0    0.0B    0.0B         idle  Mar27  00:00  rcu_bh
root          10   0.0    0.0B    0.0B        sleep  Mar27  00:00  migration/0
root          11   0.0    0.0B    0.0B        sleep  Mar27  00:00  watchdog/0
root          12   0.0    0.0B    0.0B        sleep  Mar27  00:00  cpuhp/0
root          13   0.0    0.0B    0.0B        sleep  Mar27  00:00  cpuhp/1
root          14   0.0    0.0B    0.0B        sleep  Mar27  00:01  watchdog/1
root          15   0.0    0.0B    0.0B        sleep  Mar27  00:00  migration/1
[...]
giampaolo  19704   1.5    1.9G  235.6M        sleep  17:39  01:11  firefox
root       20414   0.0    0.0B    0.0B         idle  Apr04  00:00  kworker/4:2
giampaolo  20952   0.0   10.7M  100.0K        sleep  Mar28  00:00  sh -c /usr
giampaolo  20953   0.0  269.0M  528.0K        sleep  Mar28  00:00  /usr/lib/
giampaolo  22150   3.3    2.4G  525.5M        sleep  Apr02  49:09  /usr/lib/
root       22338   0.0    0.0B    0.0B         idle  02:04  00:00  kworker/1:2
giampaolo  24123   0.0   35.0M    7.0M        sleep  02:12  00:02  bash
"""

import datetime
import time

import psutil
from psutil._common import bytes2human
from psutil._compat import get_terminal_size


def main():
    today_day = datetime.date.today()
    templ = "%-10s %5s %5s %7s %7s %5s %6s %6s %6s  %s"
    attrs = ['pid', 'memory_percent', 'name', 'cmdline', 'cpu_times',
             'create_time', 'memory_info', 'status', 'nice', 'username']
    print(templ % ("USER", "PID", "%MEM", "VSZ", "RSS", "NICE",
                   "STATUS", "START", "TIME", "CMDLINE"))
    for p in psutil.process_iter(attrs, ad_value=None):
        if p.info['create_time']:
            ctime = datetime.datetime.fromtimestamp(p.info['create_time'])
            if ctime.date() == today_day:
                ctime = ctime.strftime("%H:%M")
            else:
                ctime = ctime.strftime("%b%d")
        else:
            ctime = ''
        if p.info['cpu_times']:
            cputime = time.strftime("%M:%S",
                                    time.localtime(sum(p.info['cpu_times'])))
        else:
            cputime = ''

        user = p.info['username']
        if not user and psutil.POSIX:
            try:
                user = p.uids()[0]
            except psutil.Error:
                pass
        if user and psutil.WINDOWS and '\\' in user:
            user = user.split('\\')[1]
        if not user:
            user = ''
        user = user[:9]
        vms = bytes2human(p.info['memory_info'].vms) if \
            p.info['memory_info'] is not None else ''
        rss = bytes2human(p.info['memory_info'].rss) if \
            p.info['memory_info'] is not None else ''
        memp = round(p.info['memory_percent'], 1) if \
            p.info['memory_percent'] is not None else ''
        nice = int(p.info['nice']) if p.info['nice'] else ''
        if p.info['cmdline']:
            cmdline = ' '.join(p.info['cmdline'])
        else:
            cmdline = p.info['name']
        status = p.info['status'][:5] if p.info['status'] else ''

        line = templ % (
            user,
            p.info['pid'],
            memp,
            vms,
            rss,
            nice,
            status,
            ctime,
            cputime,
            cmdline)
        print(line[:get_terminal_size()[0]])


if __name__ == '__main__':
    main()
