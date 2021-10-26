#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of iotop (http://guichaz.free.fr/iotop/) showing real time
disk I/O statistics.

It works on Linux only (FreeBSD and macOS are missing support for IO
counters).
It doesn't work on Windows as curses module is required.

Example output:

$ python3 scripts/iotop.py
Total DISK READ: 0.00 B/s | Total DISK WRITE: 472.00 K/s
PID   USER      DISK READ  DISK WRITE  COMMAND
13155 giampao    0.00 B/s  428.00 K/s  /usr/bin/google-chrome-beta
3260  giampao    0.00 B/s    0.00 B/s  bash
3779  giampao    0.00 B/s    0.00 B/s  gnome-session --session=ubuntu
3830  giampao    0.00 B/s    0.00 B/s  /usr/bin/dbus-launch
3831  giampao    0.00 B/s    0.00 B/s  //bin/dbus-daemon --fork --print-pid 5
3841  giampao    0.00 B/s    0.00 B/s  /usr/lib/at-spi-bus-launcher
3845  giampao    0.00 B/s    0.00 B/s  /bin/dbus-daemon
3848  giampao    0.00 B/s    0.00 B/s  /usr/lib/at-spi2-core/at-spi2-registryd
3862  giampao    0.00 B/s    0.00 B/s  /usr/lib/gnome-settings-daemon

Author: Giampaolo Rodola' <g.rodola@gmail.com>
"""

import time
import sys
try:
    import curses
except ImportError:
    sys.exit('platform not supported')

import psutil
from psutil._common import bytes2human


win = curses.initscr()
lineno = 0


def printl(line, highlight=False):
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
            p._before = p.io_counters()
        except psutil.Error:
            procs.remove(p)
            continue
    disks_before = psutil.disk_io_counters()

    # sleep some time
    time.sleep(interval)

    # then retrieve the same info again
    for p in procs[:]:
        with p.oneshot():
            try:
                p._after = p.io_counters()
                p._cmdline = ' '.join(p.cmdline())
                if not p._cmdline:
                    p._cmdline = p.name()
                p._username = p.username()
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
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
    printl(disks_tot)

    header = templ % ("PID", "USER", "DISK READ", "DISK WRITE", "COMMAND")
    printl(header, highlight=True)

    for p in procs:
        line = templ % (
            p.pid,
            p._username[:7],
            bytes2human(p._read_per_sec),
            bytes2human(p._write_per_sec),
            p._cmdline)
        try:
            printl(line)
        except curses.error:
            break
    win.refresh()


def setup():
    curses.start_color()
    curses.use_default_colors()
    for i in range(0, curses.COLORS):
        curses.init_pair(i + 1, i, -1)
    curses.endwin()
    win.nodelay(1)


def tear_down():
    win.keypad(0)
    curses.nocbreak()
    curses.echo()
    curses.endwin()


def main():
    global lineno
    setup()
    try:
        interval = 0
        while True:
            if win.getch() == ord('q'):
                break
            args = poll(interval)
            refresh_window(*args)
            lineno = 0
            interval = 0.5
            time.sleep(interval)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        tear_down()


if __name__ == '__main__':
    main()
