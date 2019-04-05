#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of 'ps aux'.

$ python scripts/ps.py
...
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
            user[:10],
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
