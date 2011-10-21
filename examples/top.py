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


win = curses.initscr()                      # the curses window
procs = [p for p in psutil.process_iter()]  # the current process list

def bytes2human(n):
    """
    >>> bytes2human(10000)
    '9.8 K/s'
    >>> bytes2human(100001221)
    '95.4 M/s'
    """
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i+1)*10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = int(float(n) / prefix[s])
            return '%s%s' % (value, s)
    return "0B"


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
            if str(p.status) not in procs_status:
                procs_status[str(p.status)] = 0
            procs_status[str(p.status)] += 1
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
    for lineno, perc in enumerate(psutil.cpu_percent(interval=0, percpu=True)):
        dashes, empty_dashes = get_dashes(perc)
        line = " CPU%-2s [%s%s] %5s%%" % (lineno, dashes, empty_dashes, perc)
        win.addstr(lineno, 0, line)

    # physmem usage
    lineno += 1
    phymem = psutil.phymem_usage()
    dashes, empty_dashes = get_dashes(phymem.percent)
    buffers = getattr(psutil, 'phymem_buffers', lambda: 0)()
    cached = getattr(psutil, 'cached_phymem', lambda: 0)()
    used = phymem.total - (phymem.free + buffers + cached)
    line = " Mem   [%s%s] %5s%% %6s/%s" % (dashes, empty_dashes,
                                           phymem.percent,
                                           str(used / 1024 / 1024) + "M",
                                           str(phymem.total / 1024 / 1024) + "M")
    win.addstr(lineno, 0, line)

    # swap usage
    lineno += 1
    vmem = psutil.virtmem_usage()
    dashes, empty_dashes = get_dashes(vmem.percent)
    line = " Swap  [%s%s] %5s%% %6s/%s" % (dashes, empty_dashes,
                                           vmem.percent,
                                           str(vmem.used / 1024 / 1024) + "M",
                                           str(vmem.total / 1024 / 1024) + "M")
    win.addstr(lineno, 0, line)

    # procesess number and status
    lineno += 1
    st = []
    for x, y in procs_status.iteritems():
        if y:
            st.append("%s=%s" % (x, y))
    st.sort(key=lambda x: x[:3] in ('run', 'sle'), reverse=1)
    win.addstr(lineno, 0, " Processes: %s (%s)" % (len(procs), ' '.join(st)))
    # load average, uptime
    lineno += 1
    uptime = datetime.now() - datetime.fromtimestamp(psutil.BOOT_TIME)
    av1, av2, av3 = os.getloadavg()
    line = " Load average: %.2f %.2f %.2f  Uptime: %s" \
            % (av1, av2, av3, str(uptime).split('.')[0])
    win.addstr(lineno, 0, line)
    return lineno + 1

def run(win):
    """Print results on screen by using curses."""
    curses.endwin()
    templ = "%-6s %-8s %4s %5s %5s %6s %4s %9s  %2s"
    interval = 0
    while 1:
        procs, procs_status = poll(interval)
        win.erase()
        header = templ % ("PID", "USER", "NI", "VIRT", "RES", "CPU%", "MEM%",
                          "TIME+", "NAME")
        header += " " * (win.getmaxyx()[1] - len(header))
        lineno = print_header(procs_status) + 1
        win.addstr(lineno, 0, header, curses.A_REVERSE)
        lineno += 1
        for p in procs:
            # TIME+ column shows process CPU cumulative time and
            # is expressed as: mm:ss.ms
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
                win.addstr(lineno, 0, line)
            except curses.error:
                break
            win.refresh()
            lineno += 1
        interval = 1

def main():
    def tear_down():
        win.keypad(0)
        curses.nocbreak()
        curses.echo()
        curses.endwin()

    atexit.register(tear_down)
    try:
        run(win)
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == '__main__':
    main()
