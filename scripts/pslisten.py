#!/usr/bin/env python

import psutil
import socket
import operator
import subprocess
import datetime

entries = []
host_max_width = 0
user_max_width = 0
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
                entry['proto'] = 'UDP'
            elif netcon.type == socket.SocketKind.SOCK_STREAM:
                entry['proto'] = 'TCP'
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
            entry['pgid'] = '?'
            entry['sid'] = '?'
            entry['nice'] = proc.nice()
            entry['cpu_percent'] = proc.cpu_percent()
            entry['memory_percent'] = proc.memory_percent()
            entry['num_threads'] = proc.num_threads()
            entry['started'] = datetime.datetime.utcfromtimestamp(
                    proc.create_time())

        entries.append(entry)

        if len(entry['host']) > host_max_width:
            host_max_width = len(entry['host'])
        if len(entry['username']) > user_max_width:
            user_max_width = len(entry['username'])

print('{:>5} {:>{host_max_width}} {:>5} {:>{user_max_width}} {:>5} {:>5} '
      '{:>5} {:>5} {:>3} {:>5} {:>5} {:>5}  {:>19} {}'.format(
          'PROTO', 'HOST', 'PORT', 'USER', 'PID', 'PPID', 'PGID', 'SID', 'NIC',
          '%CPU', '%MEM', '#TH', 'STARTED', 'COMMAND',
          host_max_width=host_max_width, user_max_width=user_max_width))

for entry in sorted(entries, key=lambda e: (e['port'], e['proto'])):
    print('{:>5} {:>{host_max_width}} {:>5} {:>{user_max_width}} {:>5} {:>5} '
          '{:>5} {:>5} {:>3} {: 5.1f} {: 5.1f} {:>5}  {:%Y-%m-%d %H:%M:%S} '
          '{}'.format(
              entry['proto'], entry['host'], entry['port'], entry['username'],
              entry['pid'], entry['ppid'], entry['pgid'], entry['sid'],
              entry['nice'], entry['cpu_percent'], entry['memory_percent'],
              entry['num_threads'], entry['started'], entry['cmdline'],
              host_max_width=host_max_width, user_max_width=user_max_width))
