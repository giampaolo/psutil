# Copyright (c) 2009, Giampaolo Rodola'
# Copyright (c) 2017, Arnon Yaari
# Copyright (c) 2020, François Revol
# All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Haiku platform implementation."""

import functools
# import glob
import os
# import re
# import subprocess
# import sys
from collections import namedtuple

from . import _common
from . import _psposix
from . import _psutil_haiku as cext
from . import _psutil_posix as cext_posix
from ._common import AccessDenied
# from ._common import conn_to_ntuple
from ._common import memoize_when_activated
from ._common import NoSuchProcess
from ._common import usage_percent
from ._common import ZombieProcess
from ._compat import FileNotFoundError
from ._compat import PermissionError
from ._compat import ProcessLookupError
# from ._compat import PY3


__extra__all__ = []


# =====================================================================
# --- globals
# =====================================================================


HAS_NET_IO_COUNTERS = hasattr(cext, "net_io_counters")
HAS_PROC_IO_COUNTERS = hasattr(cext, "proc_io_counters")

PAGE_SIZE = os.sysconf('SC_PAGE_SIZE')
AF_LINK = cext_posix.AF_LINK

PROC_STATUSES = {
    cext.B_THREAD_RUNNING: _common.STATUS_RUNNING,
    cext.B_THREAD_READY: _common.STATUS_IDLE,
    cext.B_THREAD_RECEIVING: _common.STATUS_WAITING,
    cext.B_THREAD_ASLEEP: _common.STATUS_SLEEPING,
    cext.B_THREAD_SUSPENDED: _common.STATUS_STOPPED,
    cext.B_THREAD_WAITING: _common.STATUS_WAITING,
}

team_info_map = dict(
    thread_count=0,
    image_count=1,
    area_count=2,
    uid=3,
    gid=4,
    name=5)

team_usage_info_map = dict(
    user_time=0,
    kernel_time=1)

thread_info_map = dict(
    id=0,
    user_time=1,
    kernel_time=2,
    state=3)


# =====================================================================
# --- named tuples
# =====================================================================


# psutil.Process.memory_info()
pmem = namedtuple('pmem', ['rss', 'vms'])
# psutil.Process.memory_full_info()
pfullmem = pmem
# psutil.Process.cpu_times()
scputimes = namedtuple('scputimes', ['user', 'system', 'idle', 'iowait'])
# psutil.virtual_memory()
svmem = namedtuple('svmem', ['total', 'used', 'percent', 'cached', 'buffers',
                             'ignored', 'needed', 'available'])


# =====================================================================
# --- memory
# =====================================================================


def virtual_memory():
    total, inuse, cached, buffers, ignored, needed, avail = cext.virtual_mem()
    percent = usage_percent((total - avail), total, round_=1)
    return svmem(total, inuse, percent, cached, buffers, ignored, needed,
                 avail)


def swap_memory():
    """Swap system memory as a (total, used, free, sin, sout) tuple."""
    total, free = cext.swap_mem()
    sin = 0
    sout = 0
    used = total - free
    percent = usage_percent(used, total, round_=1)
    return _common.sswap(total, used, free, percent, sin, sout)


# =====================================================================
# --- CPU
# =====================================================================


def cpu_times():
    """Return system-wide CPU times as a named tuple"""
    ret = cext.per_cpu_times()
    return scputimes(*[sum(x) for x in zip(*ret)])


def per_cpu_times():
    """Return system per-CPU times as a list of named tuples"""
    ret = cext.per_cpu_times()
    return [scputimes(*x) for x in ret]


def cpu_count_logical():
    """Return the number of logical CPUs in the system."""
    try:
        return os.sysconf("SC_NPROCESSORS_ONLN")
    except ValueError:
        # mimic os.cpu_count() behavior
        return None


def cpu_count_physical():
    # TODO:
    return None


def cpu_stats():
    """Return various CPU stats as a named tuple."""
    # ctx_switches, interrupts, soft_interrupts, syscalls = cext.cpu_stats()
    # TODO!
    return _common.scpustats(
        0, 0, 0, 0)
    #    ctx_switches, interrupts, soft_interrupts, syscalls)


def cpu_freq():
    """Return CPU frequency.
    """
    curr, min_, max_ = cext.cpu_freq()
    return [_common.scpufreq(curr, min_, max_)]


# =====================================================================
# --- disks
# =====================================================================


# TODO:disk_io_counters = cext.disk_io_counters
disk_usage = _psposix.disk_usage


def disk_partitions(all=False):
    """Return system disk partitions."""
    # TODO - the filtering logic should be better checked so that
    # it tries to reflect 'df' as much as possible
    retlist = []
    partitions = cext.disk_partitions()
    for partition in partitions:
        device, mountpoint, fstype, opts = partition
        if not all:
            # Differently from, say, Linux, we don't have a list of
            # common fs types so the best we can do, AFAIK, is to
            # filter by filesystem having a total size > 0.
            if not disk_usage(mountpoint).total:
                continue
        ntuple = _common.sdiskpart(device, mountpoint, fstype, opts)
        retlist.append(ntuple)
    return retlist


# =====================================================================
# --- network
# =====================================================================


net_if_addrs = cext_posix.net_if_addrs
net_io_counters = cext.net_io_counters


def net_connections(kind, _pid=-1):
    """Return socket connections.  If pid == -1 return system-wide
    connections (as opposed to connections opened by one process only).
    """
    # TODO
    return []


def net_if_stats():
    """Get NIC stats (isup, duplex, speed, mtu)."""
    # TODO
    return {}


# =====================================================================
# --- other system functions
# =====================================================================


def boot_time():
    """The system boot time expressed in seconds since the epoch."""
    return cext.boot_time()


def users():
    """Return currently connected users as a list of namedtuples."""
    retlist = []
    rawlist = cext.users()
    localhost = (':0.0', ':0')
    for item in rawlist:
        user, tty, hostname, tstamp, user_process, pid = item
        # note: the underlying C function includes entries about
        # system boot, run level and others.  We might want
        # to use them in the future.
        if not user_process:
            continue
        if hostname in localhost:
            hostname = 'localhost'
        nt = _common.suser(user, tty, hostname, tstamp, pid)
        retlist.append(nt)
    return retlist


# =====================================================================
# --- processes
# =====================================================================


def pids():
    ls = cext.pids()
    return ls


pid_exists = _psposix.pid_exists


def wrap_exceptions(fun):
    """Call callable into a try/except clause and translate ENOENT,
    EACCES and EPERM in NoSuchProcess or AccessDenied exceptions.
    """
    @functools.wraps(fun)
    def wrapper(self, *args, **kwargs):
        try:
            return fun(self, *args, **kwargs)
        except (FileNotFoundError, ProcessLookupError):
            # ENOENT (no such file or directory) gets raised on open().
            # ESRCH (no such process) can get raised on read() if
            # process is gone in meantime.
            if not pid_exists(self.pid):
                raise NoSuchProcess(self.pid, self._name)
            else:
                raise ZombieProcess(self.pid, self._name, self._ppid)
        except PermissionError:
            raise AccessDenied(self.pid, self._name)
    return wrapper


class Process(object):
    """Wrapper class around underlying C implementation."""

    __slots__ = ["pid", "_name", "_ppid", "_cache"]

    def __init__(self, pid):
        self.pid = pid
        self._name = None
        self._ppid = None

    def oneshot_enter(self):
        self._proc_team_info.cache_activate(self)
        self._proc_team_usage_info.cache_activate(self)

    def oneshot_exit(self):
        self._proc_team_info.cache_deactivate(self)
        self._proc_team_usage_info.cache_deactivate(self)

    @wrap_exceptions
    @memoize_when_activated
    def _proc_team_info(self):
        ret = cext.proc_team_info_oneshot(self.pid)
        assert len(ret) == len(team_info_map)
        return ret

    @wrap_exceptions
    @memoize_when_activated
    def _proc_team_usage_info(self):
        ret = cext.proc_team_usage_info_oneshot(self.pid)
        assert len(ret) == len(team_usage_info_map)
        return ret

    @wrap_exceptions
    def name(self):
        return cext.proc_name(self.pid).rstrip("\x00")

    @wrap_exceptions
    def exe(self):
        return cext.proc_exe(self.pid)

    @wrap_exceptions
    def cmdline(self):
        return cext.proc_cmdline(self.pid)

    @wrap_exceptions
    def environ(self):
        return cext.proc_environ(self.pid)

    @wrap_exceptions
    def create_time(self):
        return None

    @wrap_exceptions
    def num_threads(self):
        return self._proc_team_info()[team_info_map['thread_count']]

    @wrap_exceptions
    def threads(self):
        rawlist = cext.proc_threads(self.pid)
        retlist = []
        for thread_id, utime, stime, state in rawlist:
            ntuple = _common.pthread(thread_id, utime, stime)
            retlist.append(ntuple)
        return retlist

    @wrap_exceptions
    def connections(self, kind='inet'):
        ret = net_connections(kind, _pid=self.pid)
        # The underlying C implementation retrieves all OS connections
        # and filters them by PID.  At this point we can't tell whether
        # an empty list means there were no connections for process or
        # process is no longer active so we force NSP in case the PID
        # is no longer there.
        if not ret:
            # will raise NSP if process is gone
            os.stat('%s/%s' % (self._procfs_path, self.pid))
        return ret

    @wrap_exceptions
    def nice_get(self):
        return cext_posix.getpriority(self.pid)

    @wrap_exceptions
    def nice_set(self, value):
        return cext_posix.setpriority(self.pid, value)

    @wrap_exceptions
    def ppid(self):
        return None

    @wrap_exceptions
    def uids(self):
        uid = self._proc_team_info()[team_info_map['uid']]
        return _common.puids(uid, uid, uid)

    @wrap_exceptions
    def gids(self):
        gid = self._proc_team_info()[team_info_map['gid']]
        return _common.puids(gid, gid, gid)

    @wrap_exceptions
    def cpu_times(self):
        _user, _kern = self._proc_team_usage_info()
        return _common.pcputimes(_user, _kern, _user, _kern)

    @wrap_exceptions
    def terminal(self):
        # TODO
        return None

    @wrap_exceptions
    def cwd(self):
        return None

    @wrap_exceptions
    def memory_info(self):
        # TODO:
        rss = 0
        vms = 0
        return pmem(rss, vms)

    memory_full_info = memory_info

    @wrap_exceptions
    def status(self):
        threads = cext.proc_threads(self.pid)
        code = threads[0][thread_info_map['state']]
        # XXX is '?' legit? (we're not supposed to return it anyway)
        return PROC_STATUSES.get(code, '?')

    def open_files(self):
        # TODO:
        return []

    @wrap_exceptions
    def num_fds(self):
        # TODO:
        return None

    @wrap_exceptions
    def num_ctx_switches(self):
        return _common.pctxsw(
            *cext.proc_num_ctx_switches(self.pid))

    @wrap_exceptions
    def wait(self, timeout=None):
        return _psposix.wait_pid(self.pid, timeout, self._name)

    @wrap_exceptions
    def io_counters(self):
        return _common.pio(
            0,
            0,
            -1,
            -1)
