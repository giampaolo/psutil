#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Kill a process by name.
"""

import os
import sys
import psutil


def main():
    if len(sys.argv) != 2:
        sys.exit('usage: %s name' % __file__)
    else:
        NAME = sys.argv[1]

    killed = []
    for proc in psutil.process_iter():
        if proc.name() == NAME and proc.pid != os.getpid():
            proc.kill()
            killed.append(proc.pid)
    if not killed:
        sys.exit('%s: no process found' % NAME)
    else:
        sys.exit(0)

sys.exit(main())
