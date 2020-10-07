#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of wavemon (https://github.com/uoaerg/wavemon) showing real time
Wi-Fi activity.
"""

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


win = curses.initscr()
lineno = 0
af_map = {
    socket.AF_INET: 'IPv4',
    socket.AF_INET6: 'IPv6',
    psutil.AF_LINK: 'MAC',
}
colors_map = dict(
    green=35,
    red=10,
    blue=5,
)


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


def printl(line, color=None, bold=False, underline=False):
    """A thin wrapper around curses's addstr()."""
    global lineno
    try:
        flags = 0
        if color:
            flags |= curses.color_pair(colors_map[color])
        if bold:
            flags |= curses.A_BOLD
        if underline:
            flags |= curses.A_UNDERLINE
        win.addstr(lineno, 0, line, flags)
    except curses.error:
        lineno = 0
        win.refresh()
        raise
    else:
        lineno += 1


def print_title(line):
    printl(line, color="blue", bold=True, underline=True)


def get_dashes(perc):
    dashes = "=" * int((float(perc) / 10 * 4))
    empty_dashes = " " * (40 - len(dashes))
    return dashes, empty_dashes


def refresh_window():
    """Print results on screen by using curses."""
    for ifname, info in psutil.wifi_ifaces().items():
        print_title("Interface")
        printl("    %s (%s)" % (ifname, info.proto))
        printl("    SSID: %s" % (info.essid))
        printl("")

        print_title("Levels")
        printl("    Link quality: %s%%" % info.quality_percent)
        dashes, empty_dashes = get_dashes(info.quality_percent)
        line = "    [%s%s]" % (dashes, empty_dashes)
        printl(line, color="green" if info.quality_percent >= 50 else "red",
               bold=True)
        printl("")

        printl("    Signal level: %s dBm (%s%%)" % (
            info.signal, info.signal_percent))
        dashes, empty_dashes = get_dashes(info.signal_percent)
        line = "    [%s%s]" % (dashes, empty_dashes)
        printl(line, color="green" if info.signal_percent >= 50 else "red",
               bold=True)
        printl("")

        print_title("Statistics")
        ioc = psutil.net_io_counters(pernic=True)[ifname]
        printl("    RX (recv): %6s (%6s)" % (
            bytes2human(ioc.bytes_recv), '{0:,}'.format(ioc.bytes_recv)))
        printl("    TX (sent): %6s (%6s)" % (
            bytes2human(ioc.bytes_sent), '{0:,}'.format(ioc.bytes_sent)))
        printl("")

        print_title("Info")
        printl("    Connected to: %s" % (info.bssid))
        printl("    Mode: %s" % (info.mode))
        printl("    Freq: %s MHz" % (info.freq))
        printl("    TX-Power: %s" % (info.txpower))
        printl("    Power save: %s" % ("on" if info.power_save else "off"))
        printl("    Beacons: %s, Nwid: %s, Crypt: %s" % (
            info.beacons, info.discard_nwid, info.discard_crypt))
        printl("    Frag: %s, Retry: %s, Misc: %s" % (
            info.discard_frag, info.discard_retry, info.discard_misc))
        printl("")

        print_title("Addresses (%s)" % ifname)
        addrs = psutil.net_if_addrs()[ifname]
        for addr in addrs:
            proto = af_map.get(addr.family, addr.family)
            printl("%6s: %s" % (proto, addr.address))

    printl("")
    win.refresh()


def main():
    global lineno
    if not hasattr(psutil, "wifi_ifaces"):
        sys.exit('platform not supported')
    if not psutil.wifi_ifaces():
        sys.exit('no Wi-Fi interfaces installed')
    setup()
    try:
        while True:
            if win.getch() == ord('q'):
                break
            refresh_window()
            lineno = 0
            time.sleep(INTERVAL)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        tear_down()


if __name__ == '__main__':
    main()
