#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Shows CPU workload split across different CPUs.

$ python3 scripts/cpu_workload.py
CPU 0     CPU 1     CPU 2     CPU 3     CPU 4     CPU 5     CPU 6     CPU 7
19.8      20.6      18.2      15.8      6.9       17.3      5.0       20.4
gvfsd     pytho     kwork     chrom     unity     kwork     kwork     kwork
chrom     chrom     indic     ibus-     whoop     nfsd      (sd-p     gvfsd
ibus-     cat       at-sp     chrom     Modem     nfsd4     light     upsta
ibus-     iprt-     ibus-     nacl_     cfg80     kwork     nfsd      bluet
chrom     irqba     gpg-a     chrom     ext4-     biose     nfsd      dio/n
chrom     acpid     bamfd     nvidi     kwork     scsi_     sshd      rpc.m
upsta     rsysl     dbus-     nfsd      biose     scsi_     ext4-     polki
rtkit     avahi     upowe     Netwo     scsi_     biose     UVM T     irq/9
light     rpcbi     snapd     cron      ipv6_     biose     kwork     dbus-
agett     kvm-i     avahi     kwork     biose     biose     scsi_     syste
nfsd      syste     rpc.i     biose     biose     kbloc     kthro     UVM g
nfsd      kwork     kwork     biose     vmsta     kwork     crypt     kaudi
nfsd      scsi_     charg     biose     md        ksoft     kwork     kwork
memca     biose     ksmd      ecryp     ksoft     watch     migra     nvme
therm     biose     kcomp     kswap     migra     cpuhp     watch     biose
syste     biose     kdevt     khuge     watch               cpuhp     biose
led_w     devfr     kwork     write     cpuhp                         biose
rpcio     oom_r     ksoft     kwork     syste                         biose
kwork     kwork     watch     migra                                   acpi_
biose     ksoft     cpuhp     watch                                   watch
biose     migra               cpuhp                                   kinte
biose     watch               rcu_s                                   netns
biose     cpuhp               kthre                                   kwork
cpuhp                                                                 ksoft
watch                                                                 migra
rcu_b                                                                 cpuhp
kwork
"""

from __future__ import print_function
import collections
import os
import sys
import time

import psutil
from psutil._compat import get_terminal_size


if not hasattr(psutil.Process, "cpu_num"):
    sys.exit("platform not supported")


def clean_screen():
    if psutil.POSIX:
        os.system('clear')
    else:
        os.system('cls')


def main():
    num_cpus = psutil.cpu_count()
    if num_cpus > 8:
        num_cpus = 8  # try to fit into screen
        cpus_hidden = True
    else:
        cpus_hidden = False

    while True:
        # header
        clean_screen()
        cpus_percent = psutil.cpu_percent(percpu=True)
        for i in range(num_cpus):
            print("CPU %-6i" % i, end="")
        if cpus_hidden:
            print(" (+ hidden)", end="")

        print()
        for _ in range(num_cpus):
            print("%-10s" % cpus_percent.pop(0), end="")
        print()

        # processes
        procs = collections.defaultdict(list)
        for p in psutil.process_iter(['name', 'cpu_num']):
            procs[p.info['cpu_num']].append(p.info['name'][:5])

        curr_line = 3
        while True:
            for num in range(num_cpus):
                try:
                    pname = procs[num].pop()
                except IndexError:
                    pname = ""
                print("%-10s" % pname[:10], end="")
            print()
            curr_line += 1
            if curr_line >= get_terminal_size()[1]:
                break

        time.sleep(1)


if __name__ == '__main__':
    main()
