#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of top / htop.

Author: Giampaolo Rodola' <g.rodola@gmail.com>

$ python examples/top.py
 CPU0  [|                                       ]   4.9%
 CPU1  [|||                                     ]   7.8%
 CPU2  [                                        ]   2.0%
 CPU3  [|||||                                   ]  13.9%
 Mem   [|||||||||||||||||||                     ]  49.8%  4920M/9888M
 Swap  [                                        ]   0.0%     0M/0M
 Processes: 287 (running=1 sleeping=286)
 Load average: 0.34 0.54 0.46  Uptime: 3 days, 10:16:37

PID    USER       NI  VIRT   RES   CPU% MEM%     TIME+  NAME
------------------------------------------------------------
989    giampaol    0   66M   12M    7.4  0.1   0:00.61  python
2083   root        0  506M  159M    6.5  1.6   0:29.26  Xorg
4503   giampaol    0  599M   25M    6.5  0.3   3:32.60  gnome-terminal
3868   giampaol    0  358M    8M    2.8  0.1  23:12.60  pulseaudio
3936   giampaol    0    1G  111M    2.8  1.1  33:41.67  compiz
4401   giampaol    0  536M  141M    2.8  1.4  35:42.73  skype
4047   giampaol    0  743M   76M    1.8  0.8  42:03.33  unity-panel-service
13155  giampaol    0    1G  280M    1.8  2.8  41:57.34  chrome
10     root        0    0B    0B    0.9  0.0   4:01.81  rcu_sched
339    giampaol    0    1G  113M    0.9  1.1   8:15.73  chrome
...
"""

import os
import sys
if os.name != 'posix':
    sys.exit('platform not supported')
import atexit
import curses
import time
from datetime import datetime, timedelta

import psutil


# --- curses stuff
def tear_down():
    win.keypad(0)
    curses.nocbreak()
    curses.echo()
    curses.endwin()

win = curses.initscr()
atexit.register(tear_down)
curses.endwin()
lineno = 0


def print_line(line, highlight=False):
    """A thin wrapper around curses's addstr()."""
    global lineno
    try:
        if highlight:
            line += " " * (win.getmaxyx()[1] - len(line))
            win.addstr(lineno, 0, line, curses.A_REVERSE)
        else:
            win.addstr(lineno, 0, line, 0)
    except curses.error:
        lineno = 0
        win.refresh()
        raise
    else:
        lineno += 1
# --- /curses stuff


def bytes2human(n):
    """
    >>> bytes2human(10000)
    '9K'
    >>> bytes2human(100001221)
    '95M'
    """
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i + 1) * 10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = int(float(n) / prefix[s])
            return '%s%s' % (value, s)
    return "%sB" % n


def poll(interval):
    # sleep some time
    time.sleep(interval)
    procs = []
    procs_status = {}
    for p in psutil.process_iter():
        try:
            p.dict = p.as_dict(['username', 'nice', 'memory_info',
                                'memory_percent', 'cpu_percent',
                                'cpu_times', 'name', 'status'])
            try:
                procs_status[p.dict['status']] += 1
            except KeyError:
                procs_status[p.dict['status']] = 1
        except psutil.NoSuchProcess:
            pass
        else:
            procs.append(p)

    # return processes sorted by CPU percent usage
    processes = sorted(procs, key=lambda p: p.dict['cpu_percent'],
                       reverse=True)
    return (processes, procs_status)


def print_header(procs_status, num_procs):
    """Print system-related info, above the process list."""

    def get_dashes(perc):
        dashes = "|" * int((float(perc) / 10 * 4))
        empty_dashes = " " * (40 - len(dashes))
        return dashes, empty_dashes

    # cpu usage
    percs = psutil.cpu_percent(interval=0, percpu=True)
    for cpu_num, perc in enumerate(percs):
        dashes, empty_dashes = get_dashes(perc)
        print_line(" CPU%-2s [%s%s] %5s%%" % (cpu_num, dashes, empty_dashes,
                                              perc))
    mem = psutil.virtual_memory()
    dashes, empty_dashes = get_dashes(mem.percent)
    used = mem.total - mem.available
    line = " Mem   [%s%s] %5s%% %6s/%s" % (
        dashes, empty_dashes,
        mem.percent,
        str(int(used / 1024 / 1024)) + "M",
        str(int(mem.total / 1024 / 1024)) + "M"
    )
    print_line(line)

    # swap usage
    swap = psutil.swap_memory()
    dashes, empty_dashes = get_dashes(swap.percent)
    line = " Swap  [%s%s] %5s%% %6s/%s" % (
        dashes, empty_dashes,
        swap.percent,
        str(int(swap.used / 1024 / 1024)) + "M",
        str(int(swap.total / 1024 / 1024)) + "M"
    )
    print_line(line)

    # processes number and status
    st = []
    for x, y in procs_status.items():
        if y:
            st.append("%s=%s" % (x, y))
    st.sort(key=lambda x: x[:3] in ('run', 'sle'), reverse=1)
    print_line(" Processes: %s (%s)" % (num_procs, ' '.join(st)))
    # load average, uptime
    uptime = datetime.now() - datetime.fromtimestamp(psutil.boot_time())
    av1, av2, av3 = os.getloadavg()
    line = " Load average: %.2f %.2f %.2f  Uptime: %s" \
        % (av1, av2, av3, str(uptime).split('.')[0])
    print_line(line)


def refresh_window(procs, procs_status):
    """Print results on screen by using curses."""
    curses.endwin()
    templ = "%-6s %-8s %4s %5s %5s %6s %4s %9s  %2s"
    win.erase()
    header = templ % ("PID", "USER", "NI", "VIRT", "RES", "CPU%", "MEM%",
                      "TIME+", "NAME")
    print_header(procs_status, len(procs))
    print_line("")
    print_line(header, highlight=True)
    for p in procs:
        # TIME+ column shows process CPU cumulative time and it
        # is expressed as: "mm:ss.ms"
        if p.dict['cpu_times'] is not None:
            ctime = timedelta(seconds=sum(p.dict['cpu_times']))
            ctime = "%s:%s.%s" % (ctime.seconds // 60 % 60,
                                  str((ctime.seconds % 60)).zfill(2),
                                  str(ctime.microseconds)[:2])
        else:
            ctime = ''
        if p.dict['memory_percent'] is not None:
            p.dict['memory_percent'] = round(p.dict['memory_percent'], 1)
        else:
            p.dict['memory_percent'] = ''
        if p.dict['cpu_percent'] is None:
            p.dict['cpu_percent'] = ''
        if p.dict['username']:
            username = p.dict['username'][:8]
        else:
            username = ""
        line = templ % (p.pid,
                        username,
                        p.dict['nice'],
                        bytes2human(getattr(p.dict['memory_info'], 'vms', 0)),
                        bytes2human(getattr(p.dict['memory_info'], 'rss', 0)),
                        p.dict['cpu_percent'],
                        p.dict['memory_percent'],
                        ctime,
                        p.dict['name'] or '',
                        )
        try:
            print_line(line)
        except curses.error:
            break
        win.refresh()


def main():
    try:
        interval = 0
        while 1:
            args = poll(interval)
            refresh_window(*args)
            interval = 1
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == '__main__':
    main()
