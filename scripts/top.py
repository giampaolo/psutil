#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of top / htop.

Author: Giampaolo Rodola' <g.rodola@gmail.com>

$ python3 scripts/top.py
 CPU0  [||||                                    ]  10.9%
 CPU1  [|||||                                   ]  13.1%
 CPU2  [|||||                                   ]  12.8%
 CPU3  [||||                                    ]  11.5%
 Mem   [|||||||||||||||||||||||||||||           ]  73.0% 11017M / 15936M
 Swap  [                                        ]   1.3%   276M / 20467M
 Processes: 347 (sleeping=273, running=1, idle=73)
 Load average: 1.10 1.28 1.34  Uptime: 8 days, 21:15:40

PID    USER       NI   VIRT    RES  CPU%  MEM%     TIME+  NAME
5368   giampaol    0   7.2G   4.3G  41.8  27.7  56:34.18  VirtualBox
24976  giampaol    0   2.1G 487.2M  18.7   3.1  22:05.16  Web Content
22731  giampaol    0   3.2G 596.2M  11.6   3.7  35:04.90  firefox
1202   root        0 807.4M 288.5M  10.6   1.8  12:22.12  Xorg
22811  giampaol    0   2.8G 741.8M   9.0   4.7   2:26.61  Web Content
2590   giampaol    0   2.3G 579.4M   5.5   3.6  28:02.70  compiz
22990  giampaol    0   3.0G   1.2G   4.2   7.6   4:30.32  Web Content
18412  giampaol    0  90.1M  14.5M   3.5   0.1   0:00.26  python3
26971  netdata     0  20.8M   3.9M   2.9   0.0   3:17.14  apps.plugin
2421   giampaol    0   3.3G  36.9M   2.3   0.2  57:14.21  pulseaudio
...
"""

import datetime
import sys
import time
try:
    import curses
except ImportError:
    sys.exit('platform not supported')

import psutil
from psutil._common import bytes2human


win = curses.initscr()
lineno = 0
colors_map = dict(
    green=3,
    red=10,
    yellow=4,
)


def printl(line, color=None, bold=False, highlight=False):
    """A thin wrapper around curses's addstr()."""
    global lineno
    try:
        flags = 0
        if color:
            flags |= curses.color_pair(colors_map[color])
        if bold:
            flags |= curses.A_BOLD
        if highlight:
            line += " " * (win.getmaxyx()[1] - len(line))
            flags |= curses.A_STANDOUT
        win.addstr(lineno, 0, line, flags)
    except curses.error:
        lineno = 0
        win.refresh()
        raise
    else:
        lineno += 1

# --- /curses stuff


def poll(interval):
    # sleep some time
    time.sleep(interval)
    procs = []
    procs_status = {}
    for p in psutil.process_iter():
        try:
            p.dict = p.as_dict(['username', 'nice', 'memory_info',
                                'memory_percent', 'cpu_percent',
                                'cpu_times', 'name', 'status'])
            try:
                procs_status[p.dict['status']] += 1
            except KeyError:
                procs_status[p.dict['status']] = 1
        except psutil.NoSuchProcess:
            pass
        else:
            procs.append(p)

    # return processes sorted by CPU percent usage
    processes = sorted(procs, key=lambda p: p.dict['cpu_percent'],
                       reverse=True)
    return (processes, procs_status)


def get_color(perc):
    if perc <= 30:
        return "green"
    elif perc <= 80:
        return "yellow"
    else:
        return "red"


def print_header(procs_status, num_procs):
    """Print system-related info, above the process list."""

    def get_dashes(perc):
        dashes = "|" * int((float(perc) / 10 * 4))
        empty_dashes = " " * (40 - len(dashes))
        return dashes, empty_dashes

    # cpu usage
    percs = psutil.cpu_percent(interval=0, percpu=True)
    for cpu_num, perc in enumerate(percs):
        dashes, empty_dashes = get_dashes(perc)
        line = " CPU%-2s [%s%s] %5s%%" % (cpu_num, dashes, empty_dashes, perc)
        printl(line, color=get_color(perc))
    mem = psutil.virtual_memory()
    dashes, empty_dashes = get_dashes(mem.percent)
    line = " Mem   [%s%s] %5s%% %6s / %s" % (
        dashes, empty_dashes,
        mem.percent,
        str(int(mem.used / 1024 / 1024)) + "M",
        str(int(mem.total / 1024 / 1024)) + "M"
    )
    printl(line, color=get_color(mem.percent))

    # swap usage
    swap = psutil.swap_memory()
    dashes, empty_dashes = get_dashes(swap.percent)
    line = " Swap  [%s%s] %5s%% %6s / %s" % (
        dashes, empty_dashes,
        swap.percent,
        str(int(swap.used / 1024 / 1024)) + "M",
        str(int(swap.total / 1024 / 1024)) + "M"
    )
    printl(line, color=get_color(swap.percent))

    # processes number and status
    st = []
    for x, y in procs_status.items():
        if y:
            st.append("%s=%s" % (x, y))
    st.sort(key=lambda x: x[:3] in ('run', 'sle'), reverse=1)
    printl(" Processes: %s (%s)" % (num_procs, ', '.join(st)))
    # load average, uptime
    uptime = datetime.datetime.now() - \
        datetime.datetime.fromtimestamp(psutil.boot_time())
    av1, av2, av3 = psutil.getloadavg()
    line = " Load average: %.2f %.2f %.2f  Uptime: %s" \
        % (av1, av2, av3, str(uptime).split('.')[0])
    printl(line)


def refresh_window(procs, procs_status):
    """Print results on screen by using curses."""
    curses.endwin()
    templ = "%-6s %-8s %4s %6s %6s %5s %5s %9s  %2s"
    win.erase()
    header = templ % ("PID", "USER", "NI", "VIRT", "RES", "CPU%", "MEM%",
                      "TIME+", "NAME")
    print_header(procs_status, len(procs))
    printl("")
    printl(header, bold=True, highlight=True)
    for p in procs:
        # TIME+ column shows process CPU cumulative time and it
        # is expressed as: "mm:ss.ms"
        if p.dict['cpu_times'] is not None:
            ctime = datetime.timedelta(seconds=sum(p.dict['cpu_times']))
            ctime = "%s:%s.%s" % (ctime.seconds // 60 % 60,
                                  str((ctime.seconds % 60)).zfill(2),
                                  str(ctime.microseconds)[:2])
        else:
            ctime = ''
        if p.dict['memory_percent'] is not None:
            p.dict['memory_percent'] = round(p.dict['memory_percent'], 1)
        else:
            p.dict['memory_percent'] = ''
        if p.dict['cpu_percent'] is None:
            p.dict['cpu_percent'] = ''
        if p.dict['username']:
            username = p.dict['username'][:8]
        else:
            username = ""
        line = templ % (p.pid,
                        username,
                        p.dict['nice'],
                        bytes2human(getattr(p.dict['memory_info'], 'vms', 0)),
                        bytes2human(getattr(p.dict['memory_info'], 'rss', 0)),
                        p.dict['cpu_percent'],
                        p.dict['memory_percent'],
                        ctime,
                        p.dict['name'] or '',
                        )
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
    setup()
    try:
        interval = 0
        while True:
            if win.getch() == ord('q'):
                break
            args = poll(interval)
            refresh_window(*args)
            interval = 1
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        tear_down()


if __name__ == '__main__':
    main()
