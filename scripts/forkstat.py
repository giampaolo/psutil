#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A clone of https://github.com/ColinIanKing/forkstat.
It logs process fork(), exec() and exit() activity.
"""

import collections
import sys
import time

import psutil
from psutil._common import hilite


if not psutil.LINUX:
    sys.exit("linux only")

procs_data = collections.defaultdict(dict)
templ = "{}  {:>8} {:>8} {:>8} {:>8} {:>5}"


def colored_event(ev):
    shortname = str(ev._name_).split("_")[-1].lower()

    if not psutil.LINUX:
        return shortname
    color_map = {
        psutil.PROC_EVENT_FORK: "green",
        psutil.PROC_EVENT_EXIT: "red",
        psutil.PROC_EVENT_COMM: "blue",
        psutil.PROC_EVENT_COREDUMP: "brown",
        psutil.PROC_EVENT_EXEC: "yellow",
        psutil.PROC_EVENT_GID: "grey",
        psutil.PROC_EVENT_PTRACE: "lightblue",
        psutil.PROC_EVENT_SID: "violet",
        psutil.PROC_EVENT_UID: "darkgrey",
    }
    return hilite(shortname, color_map.get(ev))


def callback(d):
    pid = d["pid"]
    event = d["event"]
    if event == psutil.PROC_EVENT_FORK:
        procs_data[pid]["started"] = time.monotonic()

        try:
            proc = psutil.Process(d["pid"])
            cmdline = " ".join(proc.cmdline())
        except psutil.NoSuchProcess:
            pass
        else:
            d["cmdline"] = cmdline
            procs_data[pid]["cmdline"] = cmdline

    elif event == psutil.PROC_EVENT_COMM:
        if pid in procs_data:
            d.update(procs_data[pid])

    elif event == psutil.PROC_EVENT_EXIT:
        if pid in procs_data:
            d.update(procs_data[pid])
            elapsed = time.monotonic() - procs_data[pid]["started"]
            d["elapsed"] = f"{elapsed:.3f}s"
            del procs_data[pid]

    info = "thread" if d.get("is_thread") else ""
    parent = d.get("parent_pid", "")
    print(
        templ.format(
            colored_event(d["event"]) + " ",
            d["pid"],
            info,
            parent,
            d.get("elapsed", ""),
            d.get("cmdline", ""),
        )
    )


def main():
    print(
        templ.format("Event", "PID", "Info", "Parent", "Duration", "Process")
    )
    with psutil.ProcessWatcher() as pw:
        for event in pw:
            callback(event)


if __name__ == "__main__":
    main()
