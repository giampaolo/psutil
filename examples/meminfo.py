#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Print system memory information.
"""

import psutil
from psutil._compat import print_

def to_meg(n):
    return str(int(n / 1024 / 1024)) + "M"

def pprint_ntuple(nt):
    for name in nt._fields:
        value = getattr(nt, name)
        if name != 'percent':
            value = to_meg(value)
        print_('%-10s : %7s' % (name.capitalize(), value))

def main():
    print_('MEMORY\n------')
    pprint_ntuple(psutil.virtual_memory())
    print_('\nSWAP\n----')
    pprint_ntuple(psutil.swap_memory())

if __name__ == '__main__':
    main()
