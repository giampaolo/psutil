#/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common objects shared by all _ps* modules."""

from __future__ import division
import errno
import os
import socket
import stat
import sys
import warnings

from socket import AF_INET, SOCK_STREAM, SOCK_DGRAM

from psutil._compat import namedtuple, wraps

# --- constants

AF_INET6 = getattr(socket, 'AF_INET6', None)
AF_UNIX = getattr(socket, 'AF_UNIX', None)

STATUS_RUNNING = "running"
STATUS_SLEEPING = "sleeping"
STATUS_DISK_SLEEP = "disk-sleep"
STATUS_STOPPED = "stopped"
STATUS_TRACING_STOP = "tracing-stop"
STATUS_ZOMBIE = "zombie"
STATUS_DEAD = "dead"
STATUS_WAKE_KILL = "wake-kill"
STATUS_WAKING = "waking"
STATUS_IDLE = "idle"  # BSD
STATUS_LOCKED = "locked"  # BSD
STATUS_WAITING = "waiting"  # BSD

CONN_ESTABLISHED = "ESTABLISHED"
CONN_SYN_SENT = "SYN_SENT"
CONN_SYN_RECV = "SYN_RECV"
CONN_FIN_WAIT1 = "FIN_WAIT1"
CONN_FIN_WAIT2 = "FIN_WAIT2"
CONN_TIME_WAIT = "TIME_WAIT"
CONN_CLOSE = "CLOSE"
CONN_CLOSE_WAIT = "CLOSE_WAIT"
CONN_LAST_ACK = "LAST_ACK"
CONN_LISTEN = "LISTEN"
CONN_CLOSING = "CLOSING"
CONN_NONE = "NONE"


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


def memoize(f):
    """A simple memoize decorator for functions."""
    cache = {}
    def memf(*x):
        if x not in cache:
            cache[x] = f(*x)
        return cache[x]
    return memf


class cached_property(object):
    """A memoize decorator for class properties."""
    enabled = True

    def __init__(self, func):
        self.func = func

    def __get__(self, instance, type):
        ret = self.func(instance)
        if self.enabled:
            instance.__dict__[self.func.__name__] = ret
        return ret


# http://goo.gl/jYLvf
def deprecated(replacement=None):
    """A decorator which can be used to mark functions as deprecated."""
    def outer(fun):
        msg = "psutil.%s is deprecated" % fun.__name__
        if replacement is not None:
            msg += "; use %s instead" % replacement
        if fun.__doc__ is None:
            fun.__doc__ = msg

        @wraps(fun)
        def inner(*args, **kwargs):
            warnings.warn(msg, category=DeprecationWarning, stacklevel=2)
            return fun(*args, **kwargs)

        return inner
    return outer


def isfile_strict(path):
    """Same as os.path.isfile() but does not swallow EACCES / EPERM
    exceptions, see:
    http://mail.python.org/pipermail/python-dev/2012-June/120787.html
    """
    try:
        st = os.stat(path)
    except OSError:
        err = sys.exc_info()[1]
        if err.errno in (errno.EPERM, errno.EACCES):
            raise
        return False
    else:
        return stat.S_ISREG(st.st_mode)


# --- Process.get_connections() 'kind' parameter mapping

conn_tmap = {
    "all":   ([AF_INET, AF_INET6, AF_UNIX], [SOCK_STREAM, SOCK_DGRAM]),
    "tcp":   ([AF_INET, AF_INET6], [SOCK_STREAM]),
    "tcp4":  ([AF_INET],           [SOCK_STREAM]),
    "udp":   ([AF_INET, AF_INET6], [SOCK_DGRAM]),
    "udp4":  ([AF_INET],           [SOCK_DGRAM]),
    "inet":  ([AF_INET, AF_INET6], [SOCK_STREAM, SOCK_DGRAM]),
    "inet4": ([AF_INET],           [SOCK_STREAM, SOCK_DGRAM]),
    "inet6": ([AF_INET6],          [SOCK_STREAM, SOCK_DGRAM]),
}

if AF_INET6 is not None:
    conn_tmap.update({
        "tcp6": ([AF_INET6],       [SOCK_STREAM]),
        "udp6": ([AF_INET6],       [SOCK_DGRAM]),
    })

if AF_UNIX is not None:
    conn_tmap.update({
        "unix": ([AF_UNIX],        [SOCK_STREAM, SOCK_DGRAM]),
    })

del AF_INET, AF_INET6, AF_UNIX, SOCK_STREAM, SOCK_DGRAM, socket

# --- namedtuples

# system
nt_sysmeminfo = namedtuple('usage', 'total used free percent')
# XXX - would 'available' be better than 'free' as for virtual_memory() nt?
nt_swapmeminfo = namedtuple('swap', 'total used free percent sin sout')
nt_diskinfo = namedtuple('usage', 'total used free percent')
nt_partition = namedtuple('partition',  'device mountpoint fstype opts')
nt_net_iostat = namedtuple(
    'iostat',
    'bytes_sent bytes_recv packets_sent packets_recv errin errout dropin dropout')
nt_disk_iostat = namedtuple(
    'iostat',
    'read_count write_count read_bytes write_bytes read_time write_time')
nt_user = namedtuple('user', 'name terminal host started')

# processes
nt_meminfo = namedtuple('meminfo', 'rss vms')
nt_cputimes = namedtuple('cputimes', 'user system')
nt_openfile = namedtuple('openfile', 'path fd')
nt_thread = namedtuple('thread', 'id user_time system_time')
nt_uids = namedtuple('user', 'real effective saved')
nt_gids = namedtuple('group', 'real effective saved')
nt_io = namedtuple('io', 'read_count write_count read_bytes write_bytes')
nt_ionice = namedtuple('ionice', 'ioclass value')
nt_ctxsw = namedtuple('amount', 'voluntary involuntary')


# --- misc

# backward compatibility layer for Process.get_connections() ntuple
class nt_connection(namedtuple('connection',
                               'fd family type laddr raddr status')):
    __slots__ = ()

    @property
    def local_address(self):
        warnings.warn("'local_address' field is deprecated; use 'laddr'"
                      "instead", category=DeprecationWarning, stacklevel=2)
        return self.laddr

    @property
    def remote_address(self):
        warnings.warn("'remote_address' field is deprecated; use 'raddr'"
                      "instead", category=DeprecationWarning, stacklevel=2)
        return self.raddr
