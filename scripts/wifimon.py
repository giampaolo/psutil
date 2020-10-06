#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import atexit
import socket
import sys
import time
try:
    import curses
except ImportError:
    sys.exit('platform not supported')

import psutil
from psutil._common import bytes2human


INTERVAL = 0.2


def tear_down():
    win.keypad(0)
    curses.nocbreak()
    curses.echo()
    curses.endwin()


win = curses.initscr()
atexit.register(tear_down)
curses.endwin()
lineno = 0
af_map = {
    socket.AF_INET: 'IPv4',
    socket.AF_INET6: 'IPv6',
    psutil.AF_LINK: 'MAC',
}


def printl(line, highlight=False):
    """A thin wrapper around curses's addstr()."""
    global lineno
    try:
        if highlight:
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
    dashes = "=" * int((float(perc) / 10 * 4))
    empty_dashes = " " * (40 - len(dashes))
    return dashes, empty_dashes


def refresh_window():
    """Print results on screen by using curses."""
    global lineno

    for ifname, info in psutil.wifi_ifaces().items():
        printl("INTERFACE", highlight=True)
        printl("  %s (%s), SSID: %s" % (ifname, info.proto, info.essid))
        printl("")

        printl("LEVELS", highlight=True)
        printl("  Link quality: %s%%" % info.quality_percent)
        dashes, empty_dashes = get_dashes(info.quality_percent)
        line = "  [%s%s]" % (dashes, empty_dashes)
        printl(line)
        printl("")

        printl("  Signal level: %s dBm (%s%%)" % (
            info.signal, info.signal_percent))
        dashes, empty_dashes = get_dashes(info.signal_percent)
        line = "  [%s%s]" % (dashes, empty_dashes)
        printl(line)
        printl("")

        printl("STATISTICS", highlight=True)
        ioc = psutil.net_io_counters(pernic=True)[ifname]
        printl("  RX (recv): %6s (%6s)" % (
            bytes2human(ioc.bytes_recv), '{0:,}'.format(ioc.bytes_recv)))
        printl("  TX (sent): %6s (%6s)" % (
            bytes2human(ioc.bytes_sent), '{0:,}'.format(ioc.bytes_sent)))
        printl("")

        printl("INFO", highlight=True)
        printl("  Mode: %s, Connected to: %s" % (info.mode, info.bssid))
        printl("  Freq: %s MHz" % (info.freq))
        printl("  TX-Power: %s, Power save: %s" % (
            info.txpower, "on" if info.power_save else "off"))
        printl("  Beacons: %s, Nwid: %s, Crypt: %s" % (
            info.beacons, info.discard_nwid, info.discard_crypt))
        printl("  Frag: %s, Retry: %s, Misc: %s" % (
            info.discard_frag, info.discard_retry, info.discard_misc))
        printl("")

        printl("ADDRESSES (%s)" % ifname, highlight=True)
        addrs = psutil.net_if_addrs()[ifname]
        for addr in addrs:
            proto = af_map.get(addr.family, addr.family)
            printl("%6s: %s" % (proto, addr.address))

    printl("")
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
            time.sleep(INTERVAL)
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == '__main__':
    main()
