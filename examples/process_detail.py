#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Print detailed information about a process.
Author: Giampaolo Rodola' <g.rodola@gmail.com>

$ python examples/process_detail.py
pid               820
name              python
exe               /usr/bin/python2.7
parent            29613 (bash)
cmdline           python examples/process_detail.py
started           2014-41-27 03:41
user              giampaolo
uids              real=1000, effective=1000, saved=1000
gids              real=1000, effective=1000, saved=1000
terminal          /dev/pts/17
cwd               /ssd/svn/psutil
memory            0.1% (resident=10.6M, virtual=58.5M)
cpu               0.0% (user=0.09, system=0.0)
status            running
niceness          0
num threads       1
I/O               bytes-read=0B, bytes-written=0B
open files
running threads   id=820, user-time=0.09, sys-time=0.0
"""

import datetime
import os
import socket
import sys

import psutil


POSIX = os.name == 'posix'


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
    if sys.stdout.isatty() and POSIX:
        fmt = '\x1b[1;32m%-17s\x1b[0m %s' % (a, b)
    else:
        fmt = '%-15s %s' % (a, b)
    # python 2/3 compatibility layer
    sys.stdout.write(fmt + '\n')
    sys.stdout.flush()


def run(pid):
    ACCESS_DENIED = ''
    try:
        p = psutil.Process(pid)
        pinfo = p.as_dict(ad_value=ACCESS_DENIED)
    except psutil.NoSuchProcess as err:
        sys.exit(str(err))

    try:
        parent = p.parent()
        if parent:
            parent = '(%s)' % parent.name()
        else:
            parent = ''
    except psutil.Error:
        parent = ''
    if pinfo['create_time'] != ACCESS_DENIED:
        started = datetime.datetime.fromtimestamp(
            pinfo['create_time']).strftime('%Y-%m-%d %H:%M')
    else:
        started = ACCESS_DENIED
    io = pinfo.get('io_counters', ACCESS_DENIED)
    if pinfo['memory_info'] != ACCESS_DENIED:
        mem = '%s%% (resident=%s, virtual=%s) ' % (
            round(pinfo['memory_percent'], 1),
            convert_bytes(pinfo['memory_info'].rss),
            convert_bytes(pinfo['memory_info'].vms))
    else:
        mem = ACCESS_DENIED
    children = p.children()

    print_('pid', pinfo['pid'])
    print_('name', pinfo['name'])
    print_('exe', pinfo['exe'])
    print_('parent', '%s %s' % (pinfo['ppid'], parent))
    print_('cmdline', ' '.join(pinfo['cmdline']))
    print_('started', started)
    print_('user', pinfo['username'])
    if POSIX and pinfo['uids'] and pinfo['gids']:
        print_('uids', 'real=%s, effective=%s, saved=%s' % pinfo['uids'])
    if POSIX and pinfo['gids']:
        print_('gids', 'real=%s, effective=%s, saved=%s' % pinfo['gids'])
    if POSIX:
        print_('terminal', pinfo['terminal'] or '')
    print_('cwd', pinfo['cwd'])
    print_('memory', mem)
    print_('cpu', '%s%% (user=%s, system=%s)' % (
        pinfo['cpu_percent'],
        getattr(pinfo['cpu_times'], 'user', '?'),
        getattr(pinfo['cpu_times'], 'system', '?')))
    print_('status', pinfo['status'])
    print_('niceness', pinfo['nice'])
    print_('num threads', pinfo['num_threads'])
    if io != ACCESS_DENIED:
        print_('I/O', 'bytes-read=%s, bytes-written=%s' % (
            convert_bytes(io.read_bytes),
            convert_bytes(io.write_bytes)))
    if children:
        print_('children', '')
        for child in children:
            print_('', 'pid=%s name=%s' % (child.pid, child.name()))

    if pinfo['open_files'] != ACCESS_DENIED:
        print_('open files', '')
        for file in pinfo['open_files']:
            print_('', 'fd=%s %s ' % (file.fd, file.path))

    if pinfo['threads']:
        print_('running threads', '')
        for thread in pinfo['threads']:
            print_('', 'id=%s, user-time=%s, sys-time=%s' % (
                thread.id, thread.user_time, thread.system_time))
    if pinfo['connections'] not in (ACCESS_DENIED, []):
        print_('open connections', '')
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
            print_('', '%s:%s -> %s:%s type=%s status=%s' % (
                lip, lport, rip, rport, type, conn.status))


def main(argv=None):
    if argv is None:
        argv = sys.argv
    if len(argv) == 1:
        sys.exit(run(os.getpid()))
    elif len(argv) == 2:
        sys.exit(run(int(argv[1])))
    else:
        sys.exit('usage: %s [pid]' % __file__)

if __name__ == '__main__':
    sys.exit(main())
