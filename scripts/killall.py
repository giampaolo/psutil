#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Kill a process by name."""

import os
import sys

import psutil


def main():
    if len(sys.argv) != 2:
        sys.exit(f"usage: {__file__} name")
    else:
        name = sys.argv[1]

    killed = []
    for proc in psutil.process_iter():
        if proc.name() == name and proc.pid != os.getpid():
            proc.kill()
            killed.append(proc.pid)
    if not killed:
        sys.exit(f"{name}: no process found")
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
