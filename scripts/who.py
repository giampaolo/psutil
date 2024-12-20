#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A clone of 'who' command; print information about users who are
currently logged in.

$ python3 scripts/who.py
giampaolo    console    2017-03-25 22:24                loginwindow
giampaolo    ttys000    2017-03-25 23:28 (10.0.2.2)     sshd
"""

from datetime import datetime

import psutil


def main():
    users = psutil.users()
    for user in users:
        proc_name = psutil.Process(user.pid).name() if user.pid else ""
        line = "{:<12} {:<10} {:<10} {:<14} {}".format(
            user.name,
            user.terminal or '-',
            datetime.fromtimestamp(user.started).strftime("%Y-%m-%d %H:%M"),
            f"({user.host or ''})",
            proc_name,
        )
        print(line)


if __name__ == '__main__':
    main()
