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
try:
    import threading
except ImportError:
    import dummy_threading as threading

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


def memoize(fun):
    """A simple memoize decorator for functions supporting (hashable)
    positional arguments.
    It also provides a cache_clear() function for clearing the cache:

    >>> @memoize
    ... def foo()
    ...     return 1
    ...
    >>> foo()
    1
    >>> foo.cache_clear()
    >>>
    """
    @wraps(fun)
    def wrapper(*args, **kwargs):
        key = (args, frozenset(sorted(kwargs.items())))
        lock.acquire()
        try:
            try:
                return cache[key]
            except KeyError:
                ret = cache[key] = fun(*args, **kwargs)
        finally:
            lock.release()
        return ret

    def cache_clear():
        """Clear cache."""
        lock.acquire()
        try:
            cache.clear()
        finally:
            lock.release()

    lock = threading.RLock()
    cache = {}
    wrapper.cache_clear = cache_clear
    return wrapper


# http://code.activestate.com/recipes/577819-deprecated-decorator/
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


def deprecated_method(replacement):
    """A decorator which can be used to mark a method as deprecated
    'replcement' is the method name which will be called instead.
    """
    def outer(fun):
        msg = "%s() is deprecated; use %s() instead" % (
            fun.__name__, replacement)
        if fun.__doc__ is None:
            fun.__doc__ = msg

        @wraps(fun)
        def inner(self, *args, **kwargs):
            warnings.warn(msg, category=DeprecationWarning, stacklevel=2)
            return getattr(self, replacement)(*args, **kwargs)
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


# --- Process.connections() 'kind' parameter mapping

conn_tmap = {
    "all": ([AF_INET, AF_INET6, AF_UNIX], [SOCK_STREAM, SOCK_DGRAM]),
    "tcp": ([AF_INET, AF_INET6], [SOCK_STREAM]),
    "tcp4": ([AF_INET], [SOCK_STREAM]),
    "udp": ([AF_INET, AF_INET6], [SOCK_DGRAM]),
    "udp4": ([AF_INET], [SOCK_DGRAM]),
    "inet": ([AF_INET, AF_INET6], [SOCK_STREAM, SOCK_DGRAM]),
    "inet4": ([AF_INET], [SOCK_STREAM, SOCK_DGRAM]),
    "inet6": ([AF_INET6], [SOCK_STREAM, SOCK_DGRAM]),
}

if AF_INET6 is not None:
    conn_tmap.update({
        "tcp6": ([AF_INET6], [SOCK_STREAM]),
        "udp6": ([AF_INET6], [SOCK_DGRAM]),
    })

if AF_UNIX is not None:
    conn_tmap.update({
        "unix": ([AF_UNIX], [SOCK_STREAM, SOCK_DGRAM]),
    })

del AF_INET, AF_INET6, AF_UNIX, SOCK_STREAM, SOCK_DGRAM, socket


# --- namedtuples for psutil.* system-related functions

# psutil.swap_memory()
sswap = namedtuple('sswap', ['total', 'used', 'free', 'percent', 'sin',
                             'sout'])
# psutil.disk_usage()
sdiskusage = namedtuple('sdiskusage', ['total', 'used', 'free', 'percent'])
# psutil.disk_io_counters()
sdiskio = namedtuple('sdiskio', ['read_count', 'write_count',
                                 'read_bytes', 'write_bytes',
                                 'read_time', 'write_time'])
# psutil.disk_partitions()
sdiskpart = namedtuple('sdiskpart', ['device', 'mountpoint', 'fstype', 'opts'])
# psutil.net_io_counters()
snetio = namedtuple('snetio', ['bytes_sent', 'bytes_recv',
                               'packets_sent', 'packets_recv',
                               'errin', 'errout',
                               'dropin', 'dropout'])
# psutil.users()
suser = namedtuple('suser', ['name', 'terminal', 'host', 'started'])
# psutil.net_connections()
sconn = namedtuple('sconn', ['fd', 'family', 'type', 'laddr', 'raddr',
                             'status', 'pid'])


# --- namedtuples for psutil.Process methods

# psutil.Process.memory_info()
pmem = namedtuple('pmem', ['rss', 'vms'])
# psutil.Process.cpu_times()
pcputimes = namedtuple('pcputimes', ['user', 'system'])
# psutil.Process.open_files()
popenfile = namedtuple('popenfile', ['path', 'fd'])
# psutil.Process.threads()
pthread = namedtuple('pthread', ['id', 'user_time', 'system_time'])
# psutil.Process.uids()
puids = namedtuple('puids', ['real', 'effective', 'saved'])
# psutil.Process.gids()
pgids = namedtuple('pgids', ['real', 'effective', 'saved'])
# psutil.Process.io_counters()
pio = namedtuple('pio', ['read_count', 'write_count',
                         'read_bytes', 'write_bytes'])
# psutil.Process.ionice()
pionice = namedtuple('pionice', ['ioclass', 'value'])
# psutil.Process.ctx_switches()
pctxsw = namedtuple('pctxsw', ['voluntary', 'involuntary'])


# --- misc

# backward compatibility layer for Process.connections() ntuple
class pconn(
    namedtuple('pconn',
               ['fd', 'family', 'type', 'laddr', 'raddr', 'status'])):
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
