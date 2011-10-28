#!/usr/bin/env python
#
# $Id: iotop.py 1160 2011-10-14 18:50:36Z g.rodola@gmail.com $
#
# Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Shows real-time network statistics.

Author: Giampaolo Rodola' <g.rodola@gmail.com>
"""

import sys
import os
if os.name != 'posix':
    sys.exit('platform not supported')
import curses
import atexit
import time

import psutil


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
        
def bytes2human(n):
    """
    >>> bytes2human(10000)
    '9.8 K'
    >>> bytes2human(100001221)
    '95.4 M'
    """
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i+1)*10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.2f %s' % (value, s)
    return "0.00 B"

def poll(interval):
    """Retrieve raw stats within an interval window."""
    tot_before = psutil.network_io_counters()
    pnic_before = psutil.network_io_counters(pernic=True)
    # sleep some time
    time.sleep(interval)
    tot_after = psutil.network_io_counters()
    pnic_after = psutil.network_io_counters(pernic=True)
    return (tot_before, tot_after, pnic_before, pnic_after)
    

def refresh_window(tot_before, tot_after, pnic_before, pnic_after):
    """Print stats on screen."""
    global lineno
    
    # totals   
    print_line("total bytes:           sent: %-10s   received: %s" \
          % (bytes2human(tot_after.bytes_sent),
             bytes2human(tot_after.bytes_recv))
    )   
    print_line("total packets:         sent: %-10s   received: %s" \
          % (tot_after.packets_sent, tot_after.packets_recv)
    )
    
    # per network interface
    print_line("")
    for nic in pnic_after:
        stats_before = pnic_before[nic]
        stats_after = pnic_after[nic]
        templ = "%-15s %15s %15s"
        print_line(templ % (
                nic, "TOTAL", "PER-SEC"),
            highlight=True
        )
        print_line(templ % (
            "bytes-sent",
            bytes2human(stats_after.bytes_sent),
            bytes2human(stats_after.bytes_sent - stats_before.bytes_sent) + '/s',
        ))
        print_line(templ % (
            "bytes-recv",
            bytes2human(stats_after.bytes_recv),
            bytes2human(stats_after.bytes_recv - stats_before.bytes_recv) + '/s',
        ))
        print_line(templ % (
            "pkts-sent",
            stats_after.packets_sent,
            stats_after.packets_sent - stats_before.packets_sent,
        ))
        print_line(templ % (
            "pkts-recv",
            stats_after.packets_recv,
            stats_after.packets_recv - stats_before.packets_recv,
        ))
        print_line("")
    win.refresh()
    lineno = 0


def run():
    interval = 0
    while 1:
        refresh_window(*poll(interval)) 
        interval = 1

def main():
    try:
        run()
    except (KeyboardInterrupt, SystemExit):
        print

if __name__ == '__main__':
    main()
