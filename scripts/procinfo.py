#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Print detailed information about a process.
Author: Giampaolo Rodola' <g.rodola@gmail.com>

pid               11592
name              python3
parent            23412 (bash)
exe               /usr/local/bin/python3.6
cwd               /home/giampaolo/svn/psutil
cmdline           python3 scripts/procinfo.py
started           2016-09-22 05:10
cpu tot time      0:00.70
cpu times         user=0.07, system=0.0, children_user=0.0, children_system=0.0
cpu affinity      [0, 1, 2, 3, 4, 5, 6, 7]
memory            rss=12.1M, vms=64.7M, shared=5.5M, text=2.3M, lib=0B,
                  data=6.4M, dirty=0B
memory %          0.08
user              giampaolo
uids              real=1000, effective=1000, saved=1000
uids              real=1000, effective=1000, saved=1000
terminal          /dev/pts/22
status            running
niceness          0
ionice            class=IOPriority.IOPRIO_CLASS_NONE, value=4
num threads       1
num fds           38
I/O               read_count=26B, write_count=0B, read_bytes=0B, write_bytes=0B
ctx switches      voluntary=0, involuntary=1
resource limits   RLIMIT                     SOFT       HARD
                  virtualmem             infinity   infinity
                  coredumpsize                  0   infinity
                  cputime                infinity   infinity
                  datasize               infinity   infinity
                  filesize               infinity   infinity
                  locks                  infinity   infinity
                  memlock                   65536      65536
                  msgqueue                 819200     819200
                  nice                          0          0
                  openfiles                  1024      65536
                  maxprocesses              63304      63304
                  rss                    infinity   infinity
                  realtimeprio                  0          0
                  rtimesched             infinity   infinity
                  sigspending               63304      63304
                  stack                   8388608   infinity
environ
                  CLUTTER_IM_MODULE         xim
                  COMPIZ_CONFIG_PROFILE     ubuntu
                  DBUS_SESSION_BUS_ADDRESS  unix:abstract=/tmp/dbus-X7DTWzVAZj
                  DEFAULTS_PATH             /usr/share/ubuntu.default.path
                  [...]
memory maps
                  /lib/x86_64-linux-gnu/libnsl-2.23.so
                  [vvar]
                  /lib/x86_64-linux-gnu/ld-2.23.so
                  [anon]
                  [...]
"""

import datetime
import os
import socket
import sys

import psutil


ACCESS_DENIED = ''
RLIMITS_MAP = {
    "RLIMIT_AS": "virtualmem",
    "RLIMIT_CORE": "coredumpsize",
    "RLIMIT_CPU": "cputime",
    "RLIMIT_DATA": "datasize",
    "RLIMIT_FSIZE": "filesize",
    "RLIMIT_LOCKS": "locks",
    "RLIMIT_MEMLOCK": "memlock",
    "RLIMIT_MSGQUEUE": "msgqueue",
    "RLIMIT_NICE": "nice",
    "RLIMIT_NOFILE": "openfiles",
    "RLIMIT_NPROC": "maxprocesses",
    "RLIMIT_RSS": "rss",
    "RLIMIT_RTPRIO": "realtimeprio",
    "RLIMIT_RTTIME": "rtimesched",
    "RLIMIT_SIGPENDING": "sigspending",
    "RLIMIT_STACK": "stack",
}


def convert_bytes(n):
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i + 1) * 10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.1f%s' % (value, s)
    return "%sB" % n


def print_(a, b):
    if sys.stdout.isatty() and psutil.POSIX:
        fmt = '\x1b[1;32m%-13s\x1b[0m %s' % (a, b)
    else:
        fmt = '%-11s %s' % (a, b)
    print(fmt)


def str_ntuple(nt, bytes2human=False):
    if nt == ACCESS_DENIED:
        return ""
    if not bytes2human:
        return ", ".join(["%s=%s" % (x, getattr(nt, x)) for x in nt._fields])
    else:
        return ", ".join(["%s=%s" % (x, convert_bytes(getattr(nt, x)))
                          for x in nt._fields])


def run(pid):
    try:
        proc = psutil.Process(pid)
        pinfo = proc.as_dict(ad_value=ACCESS_DENIED)
    except psutil.NoSuchProcess as err:
        sys.exit(str(err))

    try:
        parent = proc.parent()
        if parent:
            parent = '(%s)' % parent.name()
        else:
            parent = ''
    except psutil.Error:
        parent = ''
    if pinfo['create_time']:
        started = datetime.datetime.fromtimestamp(
            pinfo['create_time']).strftime('%Y-%m-%d %H:%M')
    else:
        started = ACCESS_DENIED
    children = proc.children()

    print_('pid', pinfo['pid'])
    print_('name', pinfo['name'])
    print_('parent', '%s %s' % (pinfo['ppid'], parent))
    print_('exe', pinfo['exe'])
    print_('cwd', pinfo['cwd'])
    print_('cmdline', ' '.join(pinfo['cmdline']))
    print_('started', started)

    cpu_tot_time = datetime.timedelta(seconds=sum(pinfo['cpu_times']))
    cpu_tot_time = "%s:%s.%s" % (
        cpu_tot_time.seconds // 60 % 60,
        str((cpu_tot_time.seconds % 60)).zfill(2),
        str(cpu_tot_time.microseconds)[:2])
    print_('cpu tspent', cpu_tot_time)
    print_('cpu times', str_ntuple(pinfo['cpu_times']))
    if hasattr(proc, "cpu_affinity"):
        print_("cpu affinity", pinfo["cpu_affinity"])

    print_('memory', str_ntuple(pinfo['memory_info'], bytes2human=True))
    print_('memory %', round(pinfo['memory_percent'], 2))
    print_('user', pinfo['username'])
    if psutil.POSIX:
        print_('uids', str_ntuple(pinfo['uids']))
    if psutil.POSIX:
        print_('uids', str_ntuple(pinfo['uids']))
    if psutil.POSIX:
        print_('terminal', pinfo['terminal'] or '')

    print_('status', pinfo['status'])
    print_('niceness', pinfo['nice'])
    if hasattr(proc, "ionice"):
        ionice = proc.ionice()
        print_("ionice", "class=%s, value=%s" % (
            str(ionice.ioclass), ionice.value))

    print_('num threads', pinfo['num_threads'])
    print_('num fds', pinfo['num_fds'])

    if psutil.WINDOWS:
        print_('num handles', pinfo['num_handles'])

    print_('I/O', str_ntuple(pinfo['io_counters'], bytes2human=True))
    print_("ctx switches", str_ntuple(pinfo['num_ctx_switches']))
    if children:
        template = "%-6s %s"
        print_("children", template % ("PID", "NAME"))
        for child in children:
            print_('', 'pid=%s name=%s' % (child.pid, child.name()))

    if pinfo['open_files']:
        print_('open files', 'PATH')
        for file in pinfo['open_files']:
            print_('', file.path)

    if pinfo['threads']:
        template = "%-5s %15s %15s"
        print_('threads', template % ("TID", "USER", "SYSTEM"))
        for thread in pinfo['threads']:
            print_('', template % thread)
        print_('', "total=%s" % len(pinfo['threads']))

    if pinfo['connections']:
        template = '%-5s %-25s %-25s %s'
        print_('connections',
               template % ('PROTO', 'LOCAL ADDR', 'REMOTE ADDR', 'STATUS'))
        for conn in pinfo['connections']:
            if conn.type == socket.SOCK_STREAM:
                type = 'TCP'
            elif conn.type == socket.SOCK_DGRAM:
                type = 'UDP'
            else:
                type = 'UNIX'
            lip, lport = conn.laddr
            if not conn.raddr:
                rip, rport = '*', '*'
            else:
                rip, rport = conn.raddr
            print_('', template % (
                type,
                "%s:%s" % (lip, lport),
                "%s:%s" % (rip, rport),
                conn.status))

    if hasattr(proc, "rlimit"):
        res_names = [x for x in dir(psutil) if x.startswith("RLIMIT")]
        resources = []
        for res_name in res_names:
            try:
                soft, hard = proc.rlimit(getattr(psutil, res_name))
            except psutil.AccessDenied:
                pass
            else:
                resources.append((res_name, soft, hard))
        if resources:
            print_("res limits",
                   "RLIMIT                     SOFT       HARD")
            for res_name, soft, hard in resources:
                if soft == psutil.RLIM_INFINITY:
                    soft = "infinity"
                if hard == psutil.RLIM_INFINITY:
                    hard = "infinity"
                print_('', "%-20s %10s %10s" % (
                    RLIMITS_MAP.get(res_name, res_name), soft, hard))

    if hasattr(proc, "environ") and pinfo['environ']:
        print_("environ", "")
        for i, k in enumerate(sorted(pinfo['environ'])):
            print_("", "%-25s %s" % (k, pinfo['environ'][k]))
            if i >= 3:
                print_("", "[...]")
                break

    if pinfo['memory_maps']:
        print_("mem maps", "")
        for i, region in enumerate(pinfo['memory_maps']):
            print_("", region.path)
            if i >= 3:
                print_("", "[...]")
                break


def main(argv=None):
    help = 'usage: %s [PID]' % __file__
    if argv is None:
        argv = sys.argv
    if len(argv) == 1:
        sys.exit(run(os.getpid()))
    elif len(argv) == 2:
        if argv[1] in ('-h', '--help'):
            sys.exit(help)
        sys.exit(run(int(argv[1])))
    else:
        sys.exit(help)


if __name__ == '__main__':
    sys.exit(main())
