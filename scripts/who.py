#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of 'who' command; print information about users who are
currently logged in.

$ python scripts/who.py
giampaolo    console    2017-03-25 22:24                loginwindow
giampaolo    ttys000    2017-03-25 23:28 (10.0.2.2)     sshd
"""

from datetime import datetime

import psutil


def main():
    users = psutil.users()
    for user in users:
        proc_name = psutil.Process(user.pid).name() if user.pid else ""
        print("%-12s %-10s %-10s %-14s %s" % (
            user.name,
            user.terminal or '-',
            datetime.fromtimestamp(user.started).strftime("%Y-%m-%d %H:%M"),
            "(%s)" % user.host if user.host else "",
            proc_name
        ))


if __name__ == '__main__':
    main()
