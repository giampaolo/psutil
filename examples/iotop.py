#!/usr/bin/env python
#
# $Id$
#
# Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of iotop (http://guichaz.free.fr/iotop/) showing real time
disk I/O statistics.

It works on UNIX only as curses module is not available on Windows.

Author: Giampaolo Rodola' <g.rodola@gmail.com>
"""

import time
import curses
import atexit

import psutil

win = curses.initscr()

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
    return "0.00 B/s"

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

def run(win):
    """Print results on screen by using curses."""
    curses.endwin()
    templ = "%-5s %-7s %11s %11s  %s"
    interval = 0
    while 1:
        procs, disks_read, disks_write = poll(interval)
        win.erase()

        disks_tot = "Total DISK READ: %s | Total DISK WRITE: %s" \
                    % (bytes2human(disks_read), bytes2human(disks_write))
        win.addstr(0, 0, disks_tot)

        header = templ % ("PID", "USER", "DISK READ", "DISK WRITE", "COMMAND")
        header += " " * (win.getmaxyx()[1] - len(header))
        win.addstr(1, 0, header, curses.A_REVERSE)

        lineno = 2
        for p in procs:
            line = templ % (p.pid,
                            p._username[:7],
                            bytes2human(p._read_per_sec),
                            bytes2human(p._write_per_sec),
                            p._cmdline)
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
