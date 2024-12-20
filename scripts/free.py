#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A clone of 'free' cmdline utility.

$ python3 scripts/free.py
             total       used       free     shared    buffers      cache
Mem:      10125520    8625996    1499524          0     349500    3307836
Swap:            0          0          0
"""

import psutil


def main():
    virt = psutil.virtual_memory()
    swap = psutil.swap_memory()
    templ = "{:<7} {:>10} {:>10} {:>10} {:>10} {:>10} {:>10}"
    print(
        templ.format("", "total", "used", "free", "shared", "buffers", "cache")
    )
    sect = templ.format(
        'Mem:',
        int(virt.total / 1024),
        int(virt.used / 1024),
        int(virt.free / 1024),
        int(getattr(virt, 'shared', 0) / 1024),
        int(getattr(virt, 'buffers', 0) / 1024),
        int(getattr(virt, 'cached', 0) / 1024),
    )
    print(sect)
    sect = templ.format(
        'Swap:',
        int(swap.total / 1024),
        int(swap.used / 1024),
        int(swap.free / 1024),
        '',
        '',
        '',
    )
    print(sect)


if __name__ == '__main__':
    main()
