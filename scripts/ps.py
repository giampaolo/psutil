#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of 'ps -aux' on UNIX.

$ python scripts/ps.py
...
"""

import datetime
import time

import psutil
from psutil._common import bytes2human


PROC_STATUSES_RAW = {
    psutil.STATUS_RUNNING: "R",
    psutil.STATUS_SLEEPING: "S",
    psutil.STATUS_DISK_SLEEP: "D",
    psutil.STATUS_STOPPED: "T",
    psutil.STATUS_TRACING_STOP: "t",
    psutil.STATUS_ZOMBIE: "Z",
    psutil.STATUS_DEAD: "X",
    psutil.STATUS_WAKING: "WA",
    psutil.STATUS_IDLE: "I",
    psutil.STATUS_LOCKED: "L",
    psutil.STATUS_WAITING: "W",
}
if hasattr(psutil, 'STATUS_WAKE_KILL'):
    PROC_STATUSES_RAW[psutil.STATUS_WAKE_KILL] = "WK"
if hasattr(psutil, 'STATUS_SUSPENDED'):
    PROC_STATUSES_RAW[psutil.STATUS_SUSPENDED] = "V"


def main():
    today_day = datetime.date.today()
    templ = "%-10s %5s %5s %5s %7s %7s %5s %-5s %5s %7s  %s"
    attrs = ['pid', 'cpu_percent', 'memory_percent', 'name', 'cpu_times',
             'create_time', 'memory_info', 'status', 'nice', 'username']
    print(templ % ("USER", "PID", "%CPU", "%MEM", "VSZ", "RSS", "NICE",
                   "STAT", "START", "TIME", "COMMAND"))
    for p in psutil.process_iter(attrs, ad_value=None):
        pinfo = p.info
        if pinfo['create_time']:
            ctime = datetime.datetime.fromtimestamp(pinfo['create_time'])
            if ctime.date() == today_day:
                ctime = ctime.strftime("%H:%M")
            else:
                ctime = ctime.strftime("%b%d")
        else:
            ctime = ''
        if pinfo['cpu_times']:
            cputime = time.strftime("%M:%S",
                                    time.localtime(sum(pinfo['cpu_times'])))
        else:
            cputime = ''

        user = pinfo['username']
        if not user and psutil.POSIX:
            try:
                user = p.uids()[0]
            except psutil.Error:
                pass
        if user and psutil.WINDOWS and '\\' in user:
            user = user.split('\\')[1]
        user = user[:9]

        vms = bytes2human(pinfo['memory_info'].vms) if \
            pinfo['memory_info'] is not None else ''
        rss = bytes2human(pinfo['memory_info'].rss) if \
            pinfo['memory_info'] is not None else ''
        memp = round(pinfo['memory_percent'], 1) if \
            pinfo['memory_percent'] is not None else ''
        nice = int(pinfo['nice']) if pinfo['nice'] else ''
        name = pinfo['name'] if pinfo['name'] else ''

        status = PROC_STATUSES_RAW.get(pinfo['status'], pinfo['status'])
        print(templ % (
            user[:10],
            pinfo['pid'],
            pinfo['cpu_percent'],
            memp,
            vms,
            rss,
            nice,
            status,
            ctime,
            cputime,
            name
        ))


if __name__ == '__main__':
    main()
