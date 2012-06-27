#/usr/bin/env python
#
#$Id$
#
# Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common objects shared by all _ps* modules."""

from __future__ import division
from psutil._compat import namedtuple, long

# --- functions

def usage_percent(used, total, _round=None):
    """Calculate percentage usage of 'used' against 'total'."""
    try:
        ret = (used / total) * 100
    except ZeroDivisionError:
        ret = 0
    if _round is not None:
        return round(ret, _round)
    else:
        return ret


class constant(int):
    """A constant type; overrides base int to provide a useful name on str()."""

    def __new__(cls, value, name, doc=None):
        inst = super(constant, cls).__new__(cls, value)
        inst._name = name
        if doc is not None:
            inst.__doc__ = doc
        return inst

    def __str__(self):
        return self._name

    def __eq__(self, other):
        # Use both int or str values when comparing for equality
        # (useful for serialization):
        # >>> st = constant(0, "running")
        # >>> st == 0
        # True
        # >>> st == 'running'
        # True
        if isinstance(other, int):
            return int(self) == other
        if isinstance(other, long):
            return long(self) == other
        if isinstance(other, str):
            return self._name == other
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

def memoize(f):
    """A simple memoize decorator for functions."""
    cache= {}
    def memf(*x):
        if x not in cache:
            cache[x] = f(*x)
        return cache[x]
    return memf

class cached_property(object):
    """A memoize decorator for class properties."""
    def __init__(self, func):
        self.func = func

    def __get__(self, instance, type):
        res = instance.__dict__[self.func.__name__] = self.func(instance)
        return res


# --- constants

STATUS_RUNNING = constant(0, "running")
STATUS_SLEEPING = constant(1, "sleeping")
STATUS_DISK_SLEEP = constant(2, "disk sleep")
STATUS_STOPPED = constant(3, "stopped")
STATUS_TRACING_STOP = constant(4, "tracing stop")
STATUS_ZOMBIE = constant(5, "zombie")
STATUS_DEAD = constant(6, "dead")
STATUS_WAKE_KILL = constant(7, "wake kill")
STATUS_WAKING = constant(8, "waking")
STATUS_IDLE = constant(9, "idle")  # BSD
STATUS_LOCKED = constant(10, "locked")  # BSD
STATUS_WAITING = constant(11, "waiting")  # BSD

# --- Process.get_connections() 'kind' parameter mapping

import socket
from socket import AF_INET, SOCK_STREAM, SOCK_DGRAM
AF_INET6 = getattr(socket, 'AF_INET6', None)

conn_tmap = {
    "all"  : ([AF_INET, AF_INET6], [SOCK_STREAM, SOCK_DGRAM]),
    "tcp"  : ([AF_INET, AF_INET6], [SOCK_STREAM]),
    "tcp4" : ([AF_INET],           [SOCK_STREAM]),
    "udp"  : ([AF_INET, AF_INET6], [SOCK_DGRAM]),
    "udp4" : ([AF_INET],           [SOCK_DGRAM]),
    "inet" : ([AF_INET, AF_INET6], [SOCK_STREAM, SOCK_DGRAM]),
    "inet4": ([AF_INET],           [SOCK_STREAM, SOCK_DGRAM]),
    "inet6": ([AF_INET6],          [SOCK_STREAM, SOCK_DGRAM]),
}

if AF_INET6 is not None:
    conn_tmap.update({
        "tcp6" : ([AF_INET6],          [SOCK_STREAM]),
        "udp6" : ([AF_INET6],          [SOCK_DGRAM]),
    })

del AF_INET, AF_INET6, SOCK_STREAM, SOCK_DGRAM, socket

# --- namedtuples

# system
nt_sys_cputimes = namedtuple('cputimes', 'user nice system idle iowait irq softirq')
nt_sysmeminfo = namedtuple('usage', 'total used free percent')
nt_diskinfo = namedtuple('usage', 'total used free percent')
nt_partition = namedtuple('partition',  'device mountpoint fstype opts')
nt_net_iostat = namedtuple('iostat', 'bytes_sent bytes_recv packets_sent packets_recv')
nt_disk_iostat = namedtuple('iostat', 'read_count write_count read_bytes write_bytes read_time write_time')
nt_user = namedtuple('user', 'name terminal host started')

# processes
nt_meminfo = namedtuple('meminfo', 'rss vms')
nt_cputimes = namedtuple('cputimes', 'user system')
nt_openfile = namedtuple('openfile', 'path fd')
nt_connection = namedtuple('connection', 'fd family type local_address remote_address status')
nt_thread = namedtuple('thread', 'id user_time system_time')
nt_uids = namedtuple('user', 'real effective saved')
nt_gids = namedtuple('group', 'real effective saved')
nt_io = namedtuple('io', 'read_count write_count read_bytes write_bytes')
nt_ionice = namedtuple('ionice', 'ioclass value')
