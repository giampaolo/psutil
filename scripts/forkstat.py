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


if not psutil.LINUX:
    sys.exit("linux only")

procs_data = collections.defaultdict(dict)
templ = "{:<8} {:>8} {:>8} {:>8} {:>5}"


def print_line():
    print(templ.format("Event", "PID", "Info", "Duration", "Process"))


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

    d["event"] = str(d["event"]._name_).split("_")[-1].lower()
    print(
        templ.format(
            d["event"],
            d["pid"],
            "",
            d.get("elapsed", ""),
            d.get("cmdline", ""),
        )
    )


def main():
    print(templ.format("Event", "PID", "Info", "Duration", "Process"))
    psutil.process_watcher(callback)


if __name__ == "__main__":
    main()
