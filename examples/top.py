#!/usr/bin/env python
#
# $Id$
#
# Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of top / htop.

Author: Giampaolo Rodola' <g.rodola@gmail.com>
"""

import os
import sys
if os.name != 'posix':
    sys.exit('platform not supported')
import time
import curses
import atexit
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
        prefix[s] = 1 << (i+1)*10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = int(float(n) / prefix[s])
            return '%s%s' % (value, s)
    return "%sB" % n

procs = [p for p in psutil.process_iter()]  # the current process list

def poll(interval):
    # add new processes to procs list; processes which have gone
    # in meantime will be removed from the list later
    cpids = [p.pid for p in procs]
    for p in psutil.process_iter():
        if p.pid not in cpids:
            procs.append(p)

    # sleep some time
    time.sleep(interval)

    procs_status = {}
    # then retrieve the same info again
    for p in procs[:]:
        try:
            p._username = p.username
            p._nice = p.nice
            p._meminfo = p.get_memory_info()
            p._mempercent = p.get_memory_percent()
            p._cpu_percent = p.get_cpu_percent(interval=0)
            p._cpu_times = p.get_cpu_times()
            p._name = p.name
            try:
                procs_status[str(p.status)] += 1
            except KeyError:
                procs_status[str(p.status)] = 1
        except psutil.NoSuchProcess:
            procs.remove(p)

    # return processes sorted by CPU percent usage
    processes = sorted(procs, key=lambda p: p._cpu_percent, reverse=True)
    return (processes, procs_status)

def print_header(procs_status):
    """Print system-related info, above the process list."""

    def get_dashes(perc):
        dashes =  "|" * int((float(perc) / 10 * 4))
        empty_dashes = " " * (40 - len(dashes))
        return dashes, empty_dashes

    # cpu usage
    for cpu_num, perc in enumerate(psutil.cpu_percent(interval=0, percpu=True)):
        dashes, empty_dashes = get_dashes(perc)
        print_line(" CPU%-2s [%s%s] %5s%%" % (cpu_num, dashes, empty_dashes,
                                              perc))
    # physmem usage (on linux we include buffers and cached values
    # to match htop results)
    phymem = psutil.phymem_usage()
    dashes, empty_dashes = get_dashes(phymem.percent)
    buffers = getattr(psutil, 'phymem_buffers', lambda: 0)()
    cached = getattr(psutil, 'cached_phymem', lambda: 0)()
    used = phymem.total - (phymem.free + buffers + cached)
    line = " Mem   [%s%s] %5s%% %6s/%s" % (
        dashes, empty_dashes,
        phymem.percent,
        str(int(used / 1024 / 1024)) + "M",
        str(int(phymem.total / 1024 / 1024)) + "M"
    )
    print_line(line)

    # swap usage
    vmem = psutil.virtmem_usage()
    dashes, empty_dashes = get_dashes(vmem.percent)
    line = " Swap  [%s%s] %5s%% %6s/%s" % (
        dashes, empty_dashes,
        vmem.percent,
        str(int(vmem.used / 1024 / 1024)) + "M",
        str(int(vmem.total / 1024 / 1024)) + "M"
    )
    print_line(line)

    # processes number and status
    st = []
    for x, y in procs_status.items():
        if y:
            st.append("%s=%s" % (x, y))
    st.sort(key=lambda x: x[:3] in ('run', 'sle'), reverse=1)
    print_line(" Processes: %s (%s)" % (len(procs), ' '.join(st)))
    # load average, uptime
    uptime = datetime.now() - datetime.fromtimestamp(psutil.BOOT_TIME)
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
    print_header(procs_status)
    print_line("")
    print_line(header, highlight=True)
    for p in procs:
        # TIME+ column shows process CPU cumulative time and it
        # is expressed as: "mm:ss.ms"
        ctime = timedelta(seconds=sum(p._cpu_times))
        ctime = "%s:%s.%s" % (ctime.seconds // 60 % 60,
                              str((ctime.seconds % 60)).zfill(2),
                              str(ctime.microseconds)[:2])
        line = templ % (p.pid,
                        p._username[:8],
                        p._nice,
                        bytes2human(p._meminfo.vms),
                        bytes2human(p._meminfo.rss),
                        p._cpu_percent,
                        round(p._mempercent, 1),
                        ctime,
                        p._name,
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
