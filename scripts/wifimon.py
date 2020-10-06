#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import atexit
import time
import sys
try:
    import curses
except ImportError:
    sys.exit('platform not supported')

import psutil
from psutil._compat import get_terminal_size
from psutil._common import bytes2human


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


def get_dashes(perc):
    dashes = "|" * int((float(perc) / 10 * 4))
    empty_dashes = " " * (40 - len(dashes))
    return dashes, empty_dashes


def refresh_window():
    """Print results on screen by using curses."""
    global lineno

    tsize = get_terminal_size()[0]
    for name, info in psutil.wifi_ifaces().items():
        print_line("INTERFACE")
        print_line("─" * (tsize))
        print_line("  %s (%s), SSID: %s" % (name, info.proto, info.essid))
        print_line("")

        print_line("LEVELS")
        print_line("─" * (tsize))

        print_line("  link quality: %s%%" % info.quality_percent)
        dashes, empty_dashes = get_dashes(info.quality_percent)
        line = "  [%s%s]" % (dashes, empty_dashes)
        print_line(line)
        print_line("")

        print_line("  signal level: %s dBm (%s%%)" % (
            info.signal, info.signal_percent))
        dashes, empty_dashes = get_dashes(info.signal_percent)
        line = "  [%s%s]" % (dashes, empty_dashes)
        print_line(line)
        print_line("")

        print_line("STATISTICS")
        print_line("─" * (tsize))
        ioc = psutil.net_io_counters(pernic=True)[name]
        print_line("  RX: %s" % bytes2human(ioc.bytes_recv))
        print_line("  TX: %s" % bytes2human(ioc.bytes_sent))
        print_line("")

        print_line("INFO")
        print_line("─" * (tsize))
        print_line("  mode: %s, connected to: %s" % (info.mode, info.bssid))
        print_line("  freq: %s MHz" % (info.freq))
        print_line("  tx-power: %s" % (info.txpower))
        print_line("")
        print_line("")

    win.refresh()
    lineno = 0


def main():
    if not hasattr(psutil, "wifi_ifaces"):
        sys.exit('platform not supported')
    if not psutil.wifi_ifaces():
        sys.exit('no Wi-Fi interfaces installed')
    try:
        while True:
            refresh_window()
            time.sleep(.5)
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == '__main__':
    main()
