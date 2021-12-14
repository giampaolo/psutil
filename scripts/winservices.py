#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

r"""
List all Windows services installed.

$ python3 scripts/winservices.py
AeLookupSvc (Application Experience)
status: stopped, start: manual, username: localSystem, pid: None
binpath: C:\Windows\system32\svchost.exe -k netsvcs

ALG (Application Layer Gateway Service)
status: stopped, start: manual, username: NT AUTHORITY\LocalService, pid: None
binpath: C:\Windows\System32\alg.exe

APNMCP (Ask Update Service)
status: running, start: automatic, username: LocalSystem, pid: 1108
binpath: "C:\Program Files (x86)\AskPartnerNetwork\Toolbar\apnmcp.exe"

AppIDSvc (Application Identity)
status: stopped, start: manual, username: NT Authority\LocalService, pid: None
binpath: C:\Windows\system32\svchost.exe -k LocalServiceAndNoImpersonation

Appinfo (Application Information)
status: stopped, start: manual, username: LocalSystem, pid: None
binpath: C:\Windows\system32\svchost.exe -k netsvcs
...
"""


import os
import sys

import psutil


if os.name != 'nt':
    sys.exit("platform not supported (Windows only)")


def main():
    for service in psutil.win_service_iter():
        info = service.as_dict()
        print("%r (%r)" % (info['name'], info['display_name']))
        print("status: %s, start: %s, username: %s, pid: %s" % (
            info['status'], info['start_type'], info['username'], info['pid']))
        print("binpath: %s" % info['binpath'])
        print("")


if __name__ == '__main__':
    sys.exit(main())
