#!/usr/bin/env python3
#
# $Id: iotop.py 1160 2011-10-14 18:50:36Z g.rodola@gmail.com $
#
# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Shows real-time network statistics.

Author: Giampaolo Rodola' <g.rodola@gmail.com>

$ python3 scripts/nettop.py
-----------------------------------------------------------
total bytes:           sent: 1.49 G       received: 4.82 G
total packets:         sent: 7338724      received: 8082712

wlan0                     TOTAL         PER-SEC
-----------------------------------------------------------
bytes-sent               1.29 G        0.00 B/s
bytes-recv               3.48 G        0.00 B/s
pkts-sent               7221782               0
pkts-recv               6753724               0

eth1                      TOTAL         PER-SEC
-----------------------------------------------------------
bytes-sent             131.77 M        0.00 B/s
bytes-recv               1.28 G        0.00 B/s
pkts-sent                     0               0
pkts-recv               1214470               0
"""

import sys
import time


try:
    import curses
except ImportError:
    sys.exit('platform not supported')

import psutil
from psutil._common import bytes2human


lineno = 0
win = curses.initscr()


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
    """Retrieve raw stats within an interval window."""
    tot_before = psutil.net_io_counters()
    pnic_before = psutil.net_io_counters(pernic=True)
    # sleep some time
    time.sleep(interval)
    tot_after = psutil.net_io_counters()
    pnic_after = psutil.net_io_counters(pernic=True)
    return (tot_before, tot_after, pnic_before, pnic_after)


def refresh_window(tot_before, tot_after, pnic_before, pnic_after):
    """Print stats on screen."""
    global lineno

    # totals
    printl(
        "total bytes:           sent: {:<10}   received: {}".format(
            bytes2human(tot_after.bytes_sent),
            bytes2human(tot_after.bytes_recv),
        )
    )

    # per-network interface details: let's sort network interfaces so
    # that the ones which generated more traffic are shown first
    printl("")
    nic_names = list(pnic_after.keys())
    nic_names.sort(key=lambda x: sum(pnic_after[x]), reverse=True)
    for name in nic_names:
        stats_before = pnic_before[name]
        stats_after = pnic_after[name]
        templ = "{:<15s} {:>15} {:>15}"
        # fmt: off
        printl(templ.format(name, "TOTAL", "PER-SEC"), highlight=True)
        printl(templ.format(
            "bytes-sent",
            bytes2human(stats_after.bytes_sent),
            bytes2human(
                stats_after.bytes_sent - stats_before.bytes_sent) + '/s',
        ))
        printl(templ.format(
            "bytes-recv",
            bytes2human(stats_after.bytes_recv),
            bytes2human(
                stats_after.bytes_recv - stats_before.bytes_recv) + '/s',
        ))
        printl(templ.format(
            "pkts-sent",
            stats_after.packets_sent,
            stats_after.packets_sent - stats_before.packets_sent,
        ))
        printl(templ.format(
            "pkts-recv",
            stats_after.packets_recv,
            stats_after.packets_recv - stats_before.packets_recv,
        ))
        printl("")
        # fmt: on
    win.refresh()
    lineno = 0


def setup():
    curses.start_color()
    curses.use_default_colors()
    for i in range(curses.COLORS):
        curses.init_pair(i + 1, i, -1)
    curses.endwin()
    win.nodelay(1)


def tear_down():
    win.keypad(0)
    curses.nocbreak()
    curses.echo()
    curses.endwin()


def main():
    setup()
    try:
        interval = 0
        while True:
            if win.getch() == ord('q'):
                break
            args = poll(interval)
            refresh_window(*args)
            interval = 0.5
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        tear_down()


if __name__ == '__main__':
    main()
