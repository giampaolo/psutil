#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""OSX platform implementation."""

import errno
import os
import sys

from psutil import _common
from psutil import _psposix
from psutil._common import (conn_tmap, usage_percent, isfile_strict)
from psutil._common import (nt_proc_conn, nt_proc_cpu, nt_proc_ctxsw,
                            nt_proc_file, nt_proc_mem, nt_proc_thread,
                            nt_proc_gids, nt_proc_uids, nt_sys_diskpart,
                            nt_sys_swap, nt_sys_user, nt_sys_vmem)
from psutil._compat import namedtuple, wraps
from psutil._error import AccessDenied, NoSuchProcess, TimeoutExpired
import _psutil_osx as cext
import _psutil_posix


__extra__all__ = []

# --- constants

PAGESIZE = os.sysconf("SC_PAGE_SIZE")

# http://students.mimuw.edu.pl/lxr/source/include/net/tcp_states.h
TCP_STATUSES = {
    cext.TCPS_ESTABLISHED: _common.CONN_ESTABLISHED,
    cext.TCPS_SYN_SENT: _common.CONN_SYN_SENT,
    cext.TCPS_SYN_RECEIVED: _common.CONN_SYN_RECV,
    cext.TCPS_FIN_WAIT_1: _common.CONN_FIN_WAIT1,
    cext.TCPS_FIN_WAIT_2: _common.CONN_FIN_WAIT2,
    cext.TCPS_TIME_WAIT: _common.CONN_TIME_WAIT,
    cext.TCPS_CLOSED: _common.CONN_CLOSE,
    cext.TCPS_CLOSE_WAIT: _common.CONN_CLOSE_WAIT,
    cext.TCPS_LAST_ACK: _common.CONN_LAST_ACK,
    cext.TCPS_LISTEN: _common.CONN_LISTEN,
    cext.TCPS_CLOSING: _common.CONN_CLOSING,
    cext.PSUTIL_CONN_NONE: _common.CONN_NONE,
}

PROC_STATUSES = {
    cext.SIDL: _common.STATUS_IDLE,
    cext.SRUN: _common.STATUS_RUNNING,
    cext.SSLEEP: _common.STATUS_SLEEPING,
    cext.SSTOP: _common.STATUS_STOPPED,
    cext.SZOMB: _common.STATUS_ZOMBIE,
}

# extend base mem ntuple with OSX-specific memory metrics
nt_sys_vmem = namedtuple(
    nt_sys_vmem.__name__,
    list(nt_sys_vmem._fields) + ['active', 'inactive', 'wired'])

nt_sys_cputimes = namedtuple('cputimes', ['user', 'nice', 'system', 'idle'])

nt_proc_extmem = namedtuple('meminfo', ['rss', 'vms', 'pfaults', 'pageins'])


# --- functions

def virtual_memory():
    """System virtual memory as a namedtuple."""
    total, active, inactive, wired, free = cext.virtual_mem()
    avail = inactive + free
    used = active + inactive + wired
    percent = usage_percent((total - avail), total, _round=1)
    return nt_sys_vmem(total, avail, percent, used, free,
                       active, inactive, wired)


def swap_memory():
    """Swap system memory as a (total, used, free, sin, sout) tuple."""
    total, used, free, sin, sout = cext.swap_mem()
    percent = usage_percent(used, total, _round=1)
    return nt_sys_swap(total, used, free, percent, sin, sout)


def cpu_times():
    """Return system CPU times as a namedtuple."""
    user, nice, system, idle = cext.cpu_times()
    return nt_sys_cputimes(user, nice, system, idle)


def per_cpu_times():
    """Return system CPU times as a named tuple"""
    ret = []
    for cpu_t in cext.per_cpu_times():
        user, nice, system, idle = cpu_t
        item = nt_sys_cputimes(user, nice, system, idle)
        ret.append(item)
    return ret


def cpu_count_logical():
    """Return the number of logical CPUs in the system."""
    return cext.cpu_count_logical()


def cpu_count_physical():
    """Return the number of physical CPUs in the system."""
    return cext.cpu_count_phys()


def boot_time():
    """The system boot time expressed in seconds since the epoch."""
    return cext.boot_time()


def disk_partitions(all=False):
    retlist = []
    partitions = cext.disk_partitions()
    for partition in partitions:
        device, mountpoint, fstype, opts = partition
        if device == 'none':
            device = ''
        if not all:
            if not os.path.isabs(device) or not os.path.exists(device):
                continue
        ntuple = nt_sys_diskpart(device, mountpoint, fstype, opts)
        retlist.append(ntuple)
    return retlist


def users():
    retlist = []
    rawlist = cext.users()
    for item in rawlist:
        user, tty, hostname, tstamp = item
        if tty == '~':
            continue  # reboot or shutdown
        if not tstamp:
            continue
        nt = nt_sys_user(user, tty or None, hostname or None, tstamp)
        retlist.append(nt)
    return retlist


pids = cext.pids
pid_exists = _psposix.pid_exists
disk_usage = _psposix.disk_usage
net_io_counters = cext.net_io_counters
disk_io_counters = cext.disk_io_counters


def wrap_exceptions(fun):
    """Decorator which translates bare OSError exceptions into
    NoSuchProcess and AccessDenied.
    """
    @wraps(fun)
    def wrapper(self, *args, **kwargs):
        try:
            return fun(self, *args, **kwargs)
        except OSError:
            err = sys.exc_info()[1]
            if err.errno == errno.ESRCH:
                raise NoSuchProcess(self.pid, self._name)
            if err.errno in (errno.EPERM, errno.EACCES):
                raise AccessDenied(self.pid, self._name)
            raise
    return wrapper


class Process(object):
    """Wrapper class around underlying C implementation."""

    __slots__ = ["pid", "_name"]

    def __init__(self, pid):
        self.pid = pid
        self._name = None

    @wrap_exceptions
    def name(self):
        """Return process name as a string of limited len (15)."""
        return cext.proc_name(self.pid)

    @wrap_exceptions
    def exe(self):
        return cext.proc_exe(self.pid)

    @wrap_exceptions
    def cmdline(self):
        """Return process cmdline as a list of arguments."""
        if not pid_exists(self.pid):
            raise NoSuchProcess(self.pid, self._name)
        return cext.proc_cmdline(self.pid)

    @wrap_exceptions
    def ppid(self):
        """Return process parent pid."""
        return cext.proc_ppid(self.pid)

    @wrap_exceptions
    def cwd(self):
        return cext.proc_cwd(self.pid)

    @wrap_exceptions
    def uids(self):
        real, effective, saved = cext.proc_uids(self.pid)
        return nt_proc_uids(real, effective, saved)

    @wrap_exceptions
    def gids(self):
        real, effective, saved = cext.proc_gids(self.pid)
        return nt_proc_gids(real, effective, saved)

    @wrap_exceptions
    def terminal(self):
        tty_nr = cext.proc_tty_nr(self.pid)
        tmap = _psposix._get_terminal_map()
        try:
            return tmap[tty_nr]
        except KeyError:
            return None

    @wrap_exceptions
    def memory_info(self):
        """Return a tuple with the process' RSS and VMS size."""
        rss, vms = cext.proc_memory_info(self.pid)[:2]
        return nt_proc_mem(rss, vms)

    @wrap_exceptions
    def ext_memory_info(self):
        """Return a tuple with the process' RSS and VMS size."""
        rss, vms, pfaults, pageins = cext.proc_memory_info(self.pid)
        return nt_proc_extmem(rss, vms,
                              pfaults * PAGESIZE,
                              pageins * PAGESIZE)

    @wrap_exceptions
    def cpu_times(self):
        user, system = cext.proc_cpu_times(self.pid)
        return nt_proc_cpu(user, system)

    @wrap_exceptions
    def create_time(self):
        """Return the start time of the process as a number of seconds since
        the epoch."""
        return cext.proc_create_time(self.pid)

    @wrap_exceptions
    def num_ctx_switches(self):
        return nt_proc_ctxsw(*cext.proc_num_ctx_switches(self.pid))

    @wrap_exceptions
    def num_threads(self):
        """Return the number of threads belonging to the process."""
        return cext.proc_num_threads(self.pid)

    @wrap_exceptions
    def open_files(self):
        """Return files opened by process."""
        if self.pid == 0:
            return []
        files = []
        rawlist = cext.proc_open_files(self.pid)
        for path, fd in rawlist:
            if isfile_strict(path):
                ntuple = nt_proc_file(path, fd)
                files.append(ntuple)
        return files

    @wrap_exceptions
    def connections(self, kind='inet'):
        """Return etwork connections opened by a process as a list of
        namedtuples.
        """
        if kind not in conn_tmap:
            raise ValueError("invalid %r kind argument; choose between %s"
                             % (kind, ', '.join([repr(x) for x in conn_tmap])))
        families, types = conn_tmap[kind]
        rawlist = cext.proc_connections(self.pid, families, types)
        ret = []
        for item in rawlist:
            fd, fam, type, laddr, raddr, status = item
            status = TCP_STATUSES[status]
            nt = nt_proc_conn(fd, fam, type, laddr, raddr, status)
            ret.append(nt)
        return ret

    @wrap_exceptions
    def num_fds(self):
        if self.pid == 0:
            return 0
        return cext.proc_num_fds(self.pid)

    @wrap_exceptions
    def wait(self, timeout=None):
        try:
            return _psposix.wait_pid(self.pid, timeout)
        except TimeoutExpired:
            raise TimeoutExpired(timeout, self.pid, self._name)

    @wrap_exceptions
    def nice_get(self):
        return _psutil_posix.getpriority(self.pid)

    @wrap_exceptions
    def nice_set(self, value):
        return _psutil_posix.setpriority(self.pid, value)

    @wrap_exceptions
    def status(self):
        code = cext.proc_status(self.pid)
        # XXX is '?' legit? (we're not supposed to return it anyway)
        return PROC_STATUSES.get(code, '?')

    @wrap_exceptions
    def threads(self):
        """Return the number of threads belonging to the process."""
        rawlist = cext.proc_threads(self.pid)
        retlist = []
        for thread_id, utime, stime in rawlist:
            ntuple = nt_proc_thread(thread_id, utime, stime)
            retlist.append(ntuple)
        return retlist

    nt_mmap_grouped = namedtuple(
        'mmap',
        'path rss private swapped dirtied ref_count shadow_depth')
    nt_mmap_ext = namedtuple(
        'mmap',
        'addr perms path rss private swapped dirtied ref_count shadow_depth')

    @wrap_exceptions
    def memory_maps(self):
        return cext.proc_memory_maps(self.pid)
