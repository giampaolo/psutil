#!/usr/bin/env python
'''
pslisten.py - list processes listening on tcp/udp sockets

Copyright (C) 2016 Internet Archive
Use of this source code is governed by a BSD-style license that can be
found in the LICENSE file.
'''

import psutil
import socket
import operator
import subprocess
import datetime
import argparse
import sys
import os

def gather_info():
    '''
    Returns a list of dicts with keys 'pid', 'cmdline', 'username', 'ppid',
    'nice', 'cpu_percent', 'memory_percent', 'num_threads', 'started'.
    '''
    entries = []
    for netcon in psutil.net_connections():
        if not netcon.raddr and netcon.laddr[1] > 0:
            entry = {
                'netcon': netcon,
                'host': netcon.laddr[0],
                'port': netcon.laddr[1],
                'pid': netcon.pid,
            }

            if netcon.family == socket.AddressFamily.AF_INET:
                if netcon.type == socket.SocketKind.SOCK_DGRAM:
                    entry['proto'] = 'UDP4'
                elif netcon.type == socket.SocketKind.SOCK_STREAM:
                    entry['proto'] = 'TCP4'
                else:
                    next # log something?
            elif netcon.family == socket.AddressFamily.AF_INET6:
                if netcon.type == socket.SocketKind.SOCK_DGRAM:
                    entry['proto'] = 'UDP6'
                elif netcon.type == socket.SocketKind.SOCK_STREAM:
                    entry['proto'] = 'TCP6'
                else:
                    next # log something?
            else:
                next # log something?

            if entry['pid']:
                proc = psutil.Process(entry['pid'])
                entry['cmdline'] = subprocess.list2cmdline(proc.cmdline())
                entry['username'] = proc.username()
                entry['ppid'] = proc.ppid()
                entry['nice'] = proc.nice()
                entry['cpu_percent'] = proc.cpu_percent()
                entry['memory_percent'] = proc.memory_percent()
                entry['num_threads'] = proc.num_threads()
                entry['started'] = datetime.datetime.utcfromtimestamp(
                        proc.create_time())

            entries.append(entry)

    return entries

def print_table(entries):
    host_max_width = 0
    user_max_width = 0

    for entry in entries:
        if len(entry['host']) > host_max_width:
            host_max_width = len(entry['host'])
        if len(entry['username']) > user_max_width:
            user_max_width = len(entry['username'])

    print('{:>5} {:>{host_max_width}} {:>5} {:>{user_max_width}} {:>5} {:>5} '
          # '{:>5} {:>5} '
          '{:>3} {:>5} {:>5} {:>5}  {:>19} {}'.format(
              'PROTO', 'HOST', 'PORT', 'USER', 'PID', 'PPID',
              # 'PGID', 'SID',
              'NIC', '%CPU', '%MEM', '#TH', 'STARTED', 'COMMAND',
              host_max_width=host_max_width, user_max_width=user_max_width))

    for entry in sorted(entries, key=lambda e: (e['port'], e['proto'])):
        print('{:>5} {:>{host_max_width}} {:>5} {:>{user_max_width}} {:>5} {:>5} '
              # '{:>5} {:>5} '
              '{:>3} {: 5.1f} {: 5.1f} {:>5}  {:%Y-%m-%d %H:%M:%S} '
              '{}'.format(
                  entry['proto'], entry['host'], entry['port'], entry['username'],
                  entry['pid'], entry['ppid'],
                  # entry['pgid'], entry['sid'],
                  entry['nice'], entry['cpu_percent'], entry['memory_percent'],
                  entry['num_threads'], entry['started'], entry['cmdline'],
                  host_max_width=host_max_width, user_max_width=user_max_width))

def main():
    arg_parser = argparse.ArgumentParser(
            prog=os.path.basename(sys.argv[0]),
            description='list processes listening on tcp/udp sockets')
    proto_group = arg_parser.add_argument_group(
            title='protocol', description=(
            'the following options limit the listing by listening '
            'protocol (by default, all are listening processes are listed)'))
    proto_group.add_argument(
            '--tcp4', dest='protos', action='append_const', const='TCP4',
            help='list processes listening on IPv4 TCP')
    proto_group.add_argument(
            '--tcp6', dest='protos', action='append_const', const='TCP6',
            help='list processes listening on IPv6 TCP')
    proto_group.add_argument(
            '--udp4', dest='protos', action='append_const', const='UDP4',
            help='list processes listening on IPv4 UDP')
    proto_group.add_argument(
            '--udp6', dest='protos', action='append_const', const='UDP6',
            help='list processes listening on IPv6 UDP')

    arg_parser.add_argument(
            '-P', '--public', dest='public', action='store_true',
            help='do not list sockets listening on localhost')
    args = arg_parser.parse_args(args=sys.argv[1:])

    all_entries = gather_info()
    entries = [entry for entry in all_entries
               if (not args.protos or entry['proto'] in args.protos)
               and (not args.public or not entry['host'] in ('127.0.0.1', '::1'))]
    print_table(entries)

if __name__ == '__main__':
    main()

