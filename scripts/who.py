#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
A clone of 'who' command; print information about users who are
currently logged in.

$ python scripts/who.py
giampaolo   tty7     2014-02-23 17:25  (:0)             upstart
giampaolo   pts/7    2014-02-24 18:25  (:192.168.1.56)  sshd
giampaolo   pts/8    2014-02-24 18:25  (:0)             upstart
giampaolo   pts/9    2014-02-27 01:32  (:0)             upstart
"""

from datetime import datetime

import psutil


def main():
    users = psutil.users()
    for user in users:
        proc_name = psutil.Process(user.pid).name() if user.pid else ""
        print("%-12s %-10s %s  (%s) %10s" % (
            user.name,
            user.terminal or '-',
            datetime.fromtimestamp(user.started).strftime("%Y-%m-%d %H:%M"),
            user.host,
            proc_name
        ))


if __name__ == '__main__':
    main()
