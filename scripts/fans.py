#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Show fans information.

$ python fans.py
asus
    cpu_fan              3200 RPM
"""

from __future__ import print_function
import sys

import psutil


def main():
    if not hasattr(psutil, "sensors_fans"):
        return sys.exit("platform not supported")
    fans = psutil.sensors_fans()
    if not fans:
        print("no fans detected")
        return
    for name, entries in fans.items():
        print(name)
        for entry in entries:
            print("    %-20s %s RPM" % (entry.label or name, entry.current))
        print()


if __name__ == '__main__':
    main()
