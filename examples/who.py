#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of 'who' command; print information about users who are
currently logged in.
"""

import sys
from datetime import datetime

import psutil
from psutil._compat import print_


def main():
    users = psutil.get_users()
    for user in users:
        print_("%-15s %-15s %s  (%s)" % \
            (user.name,
             user.terminal or '-',
             datetime.fromtimestamp(user.started).strftime("%Y-%m-%d %H:%M"),
             user.host)
        )

if __name__ == '__main__':
    main()
