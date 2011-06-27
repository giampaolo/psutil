#!/usr/bin/env python

"""
Print detailed information about a process.
"""

import os
import datetime
import socket
import sys

import psutil
from psutil._compat import namedtuple


def convert_bytes(n):
    if n == 0:
        return '0B'
    symbols = ('k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i+1)*10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.1f%s' % (value, s)

def print_(a, b):
    if sys.stdout.isatty():
        fmt = '\x1b[1;32m%-17s\x1b[0m %s' %(a, b)
    else:
        fmt = '%-15s %s' %(a, b)
    print fmt

def run(pid):
    p = psutil.Process(pid)
    if p.parent:
        parent = '(%s)' % p.parent.name
    else:
        parent = ''
    started = datetime.datetime.fromtimestamp(p.create_time).strftime('%Y-%M-%d %H:%M')
    io = p.get_io_counters()
    mem = p.get_memory_info()
    mem = '%s%% (resident=%s, virtual=%s) ' %(round(p.get_memory_percent(), 1),
                                              convert_bytes(mem.rss),
                                              convert_bytes(mem.vms))
    cpu_times = p.get_cpu_times()
    cpu_percent = p.get_cpu_percent(0)
    children = p.get_children()
    files = p.get_open_files()
    threads = p.get_threads()
    connections = p.get_connections()

    print_('pid', p.pid)
    print_('name', p.name)
    print_('exe', p.exe)
    print_('parent', '%s %s' % (p.ppid, parent))
    print_('cmdline', ' '.join(p.cmdline))
    print_('started', started)
    print_('user', p.username)
    if os.name == 'posix':
        print_('uids', 'real=%s, effective=%s, saved=%s' % p.uids)
        print_('gids', 'real=%s, effective=%s, saved=%s' % p.gids)
        print_('terminal', p.terminal or '')
    if hasattr(p, 'getcwd'):
        print_('cwd', p.getcwd())
    print_('memory', mem)
    print_('cpu', '%s%% (user=%s, system=%s)' % (cpu_percent,
                                                 cpu_times.user,
                                                 cpu_times.system))
    print_('status', p.status)
    print_('niceness', p.nice)
    print_('num threads', p.get_num_threads())
    if hasattr(p, 'get_io_counters'):
        print_('I/O', 'bytes-read=%s, bytes-written=%s' % \
                                               (convert_bytes(io.read_bytes),
                                                convert_bytes(io.write_bytes)))
    if children:
        print_('children', '')
        for child in children:
            print_('', 'pid=%s name=%s' % (child.pid, child.name))

    if files:
        print_('open files', '')
        for file in files:
            print_('',  'fd=%s %s ' % (file.fd, file.path))

    if threads:
        print_('running threads', '')
        for thread in threads:
            print_('',  'id=%s, user-time=%s, sys-time=%s' \
                         % (thread.id, thread.user_time, thread.system_time))
    if connections:
        print_('open connections', '')
        for conn in connections:
            type = 'TCP' if conn.type == socket.SOCK_STREAM else 'UDP'
            lip, lport = conn.local_address
            if not conn.remote_address:
                rip, rport = '*', '*'
            else:
                rip, rport = conn.remote_address
            print_('',  '%s:%s -> %s:%s type=%s status=%s' \
                         % (lip, lport, rip, rport, type, conn.status))

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
