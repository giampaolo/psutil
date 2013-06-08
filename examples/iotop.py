#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of iotop (http://guichaz.free.fr/iotop/) showing real time
disk I/O statistics.

It works on Linux only (FreeBSD and OSX are missing support for IO
counters).
It doesn't work on Windows as curses module is required.

Author: Giampaolo Rodola' <g.rodola@gmail.com>
"""

import os
import sys
import psutil
if not hasattr(psutil.Process, 'get_io_counters') or os.name != 'posix':
    sys.exit('platform not supported')
import time
import curses
import atexit


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
            value = float(n) / prefix[s]
            return '%.2f %s/s' % (value, s)
    return '%.2f B/s' % (n)

def poll(interval):
    """Calculate IO usage by comparing IO statics before and
    after the interval.
    Return a tuple including all currently running processes
    sorted by IO activity and total disks I/O activity.
    """
    # first get a list of all processes and disk io counters
    procs = [p for p in psutil.process_iter()]
    for p in procs[:]:
        try:
            p._before = p.get_io_counters()
        except psutil.Error:
            procs.remove(p)
            continue
    disks_before = psutil.disk_io_counters()

    # sleep some time
    time.sleep(interval)

    # then retrieve the same info again
    for p in procs[:]:
        try:
            p._after = p.get_io_counters()
            p._cmdline = ' '.join(p.cmdline)
            if not p._cmdline:
                p._cmdline = p.name
            p._username = p.username
        except psutil.NoSuchProcess:
            procs.remove(p)
    disks_after = psutil.disk_io_counters()

    # finally calculate results by comparing data before and
    # after the interval
    for p in procs:
        p._read_per_sec = p._after.read_bytes - p._before.read_bytes
        p._write_per_sec = p._after.write_bytes - p._before.write_bytes
        p._total = p._read_per_sec + p._write_per_sec

    disks_read_per_sec = disks_after.read_bytes - disks_before.read_bytes
    disks_write_per_sec = disks_after.write_bytes - disks_before.write_bytes

    # sort processes by total disk IO so that the more intensive
    # ones get listed first
    processes = sorted(procs, key=lambda p: p._total, reverse=True)

    return (processes, disks_read_per_sec, disks_write_per_sec)


def refresh_window(procs, disks_read, disks_write):
    """Print results on screen by using curses."""
    curses.endwin()
    templ = "%-5s %-7s %11s %11s  %s"
    win.erase()

    disks_tot = "Total DISK READ: %s | Total DISK WRITE: %s" \
                % (bytes2human(disks_read), bytes2human(disks_write))
    print_line(disks_tot)

    header = templ % ("PID", "USER", "DISK READ", "DISK WRITE", "COMMAND")
    print_line(header, highlight=True)

    for p in procs:
        line = templ % (p.pid,
                        p._username[:7],
                        bytes2human(p._read_per_sec),
                        bytes2human(p._write_per_sec),
                        p._cmdline)
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
