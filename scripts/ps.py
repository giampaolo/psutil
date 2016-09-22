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
import os
import time

import psutil


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
    templ = "%-10s %5s %4s %4s %7s %7s %-13s %-5s %5s %7s  %s"
    attrs = ['pid', 'cpu_percent', 'memory_percent', 'name', 'cpu_times',
             'create_time', 'memory_info', 'status']
    if os.name == 'posix':
        attrs.append('uids')
        attrs.append('terminal')
    print(templ % ("USER", "PID", "%CPU", "%MEM", "VSZ", "RSS", "TTY",
                   "STAT", "START", "TIME", "COMMAND"))
    for p in psutil.process_iter():
        try:
            pinfo = p.as_dict(attrs, ad_value='')
        except psutil.NoSuchProcess:
            pass
        else:
            if pinfo['create_time']:
                ctime = datetime.datetime.fromtimestamp(pinfo['create_time'])
                if ctime.date() == today_day:
                    ctime = ctime.strftime("%H:%M")
                else:
                    ctime = ctime.strftime("%b%d")
            else:
                ctime = ''
            cputime = time.strftime("%M:%S",
                                    time.localtime(sum(pinfo['cpu_times'])))
            try:
                user = p.username()
            except KeyError:
                if os.name == 'posix':
                    if pinfo['uids']:
                        user = str(pinfo['uids'].real)
                    else:
                        user = ''
                else:
                    raise
            except psutil.Error:
                user = ''
            if os.name == 'nt' and '\\' in user:
                user = user.split('\\')[1]
            vms = pinfo['memory_info'] and \
                int(pinfo['memory_info'].vms / 1024) or '?'
            rss = pinfo['memory_info'] and \
                int(pinfo['memory_info'].rss / 1024) or '?'
            memp = pinfo['memory_percent'] and \
                round(pinfo['memory_percent'], 1) or '?'
            status = PROC_STATUSES_RAW.get(pinfo['status'], pinfo['status'])
            print(templ % (
                user[:10],
                pinfo['pid'],
                pinfo['cpu_percent'],
                memp,
                vms,
                rss,
                pinfo.get('terminal', '') or '?',
                status,
                ctime,
                cputime,
                pinfo['name'].strip() or '?'))


if __name__ == '__main__':
    main()
