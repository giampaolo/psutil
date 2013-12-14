#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""OSX platform implementation."""

import errno
import os
import sys

import _psutil_osx
import _psutil_posix

from psutil import _psposix
from psutil._common import *
from psutil._compat import namedtuple, wraps
from psutil._error import AccessDenied, NoSuchProcess, TimeoutExpired

__extra__all__ = []

# --- constants

PAGESIZE = os.sysconf("SC_PAGE_SIZE")

# http://students.mimuw.edu.pl/lxr/source/include/net/tcp_states.h
TCP_STATUSES = {
    _psutil_osx.TCPS_ESTABLISHED: CONN_ESTABLISHED,
    _psutil_osx.TCPS_SYN_SENT: CONN_SYN_SENT,
    _psutil_osx.TCPS_SYN_RECEIVED: CONN_SYN_RECV,
    _psutil_osx.TCPS_FIN_WAIT_1: CONN_FIN_WAIT1,
    _psutil_osx.TCPS_FIN_WAIT_2: CONN_FIN_WAIT2,
    _psutil_osx.TCPS_TIME_WAIT: CONN_TIME_WAIT,
    _psutil_osx.TCPS_CLOSED: CONN_CLOSE,
    _psutil_osx.TCPS_CLOSE_WAIT: CONN_CLOSE_WAIT,
    _psutil_osx.TCPS_LAST_ACK: CONN_LAST_ACK,
    _psutil_osx.TCPS_LISTEN: CONN_LISTEN,
    _psutil_osx.TCPS_CLOSING: CONN_CLOSING,
    _psutil_osx.PSUTIL_CONN_NONE: CONN_NONE,
}

PROC_STATUSES = {
    _psutil_osx.SIDL: STATUS_IDLE,
    _psutil_osx.SRUN: STATUS_RUNNING,
    _psutil_osx.SSLEEP: STATUS_SLEEPING,
    _psutil_osx.SSTOP: STATUS_STOPPED,
    _psutil_osx.SZOMB: STATUS_ZOMBIE,
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
    total, active, inactive, wired, free = _psutil_osx.get_virtual_mem()
    avail = inactive + free
    used = active + inactive + wired
    percent = usage_percent((total - avail), total, _round=1)
    return nt_sys_vmem(total, avail, percent, used, free,
                       active, inactive, wired)


def swap_memory():
    """Swap system memory as a (total, used, free, sin, sout) tuple."""
    total, used, free, sin, sout = _psutil_osx.get_swap_mem()
    percent = usage_percent(used, total, _round=1)
    return nt_sys_swap(total, used, free, percent, sin, sout)


def get_system_cpu_times():
    """Return system CPU times as a namedtuple."""
    user, nice, system, idle = _psutil_osx.get_system_cpu_times()
    return nt_sys_cputimes(user, nice, system, idle)


def get_system_per_cpu_times():
    """Return system CPU times as a named tuple"""
    ret = []
    for cpu_t in _psutil_osx.get_system_per_cpu_times():
        user, nice, system, idle = cpu_t
        item = _cputimes_ntuple(user, nice, system, idle)
        ret.append(item)
    return ret


def get_num_cpus():
    """Return the number of logical CPUs in the system."""
    return _psutil_osx.get_num_cpus()


def get_num_phys_cpus():
    """Return the number of physical CPUs in the system."""
    return _psutil_osx.get_num_phys_cpus()


def get_system_boot_time():
    """The system boot time expressed in seconds since the epoch."""
    return _psutil_osx.get_system_boot_time()


def disk_partitions(all=False):
    retlist = []
    partitions = _psutil_osx.get_disk_partitions()
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


def get_users():
    retlist = []
    rawlist = _psutil_osx.get_users()
    for item in rawlist:
        user, tty, hostname, tstamp = item
        if tty == '~':
            continue  # reboot or shutdown
        if not tstamp:
            continue
        nt = nt_sys_user(user, tty or None, hostname or None, tstamp)
        retlist.append(nt)
    return retlist


get_pids = _psutil_osx.get_pids
pid_exists = _psposix.pid_exists
get_disk_usage = _psposix.get_disk_usage
net_io_counters = _psutil_osx.get_net_io_counters
disk_io_counters = _psutil_osx.get_disk_io_counters


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
                raise NoSuchProcess(self.pid, self._process_name)
            if err.errno in (errno.EPERM, errno.EACCES):
                raise AccessDenied(self.pid, self._process_name)
            raise
    return wrapper


class Process(object):
    """Wrapper class around underlying C implementation."""

    __slots__ = ["pid", "_process_name"]

    def __init__(self, pid):
        self.pid = pid
        self._process_name = None

    @wrap_exceptions
    def get_name(self):
        """Return process name as a string of limited len (15)."""
        return _psutil_osx.get_proc_name(self.pid)

    @wrap_exceptions
    def get_exe(self):
        return _psutil_osx.get_proc_exe(self.pid)

    @wrap_exceptions
    def get_cmdline(self):
        """Return process cmdline as a list of arguments."""
        if not pid_exists(self.pid):
            raise NoSuchProcess(self.pid, self._process_name)
        return _psutil_osx.get_proc_cmdline(self.pid)

    @wrap_exceptions
    def get_ppid(self):
        """Return process parent pid."""
        return _psutil_osx.get_proc_ppid(self.pid)

    @wrap_exceptions
    def get_cwd(self):
        return _psutil_osx.get_proc_cwd(self.pid)

    @wrap_exceptions
    def get_uids(self):
        real, effective, saved = _psutil_osx.get_proc_uids(self.pid)
        return nt_proc_uids(real, effective, saved)

    @wrap_exceptions
    def get_gids(self):
        real, effective, saved = _psutil_osx.get_proc_gids(self.pid)
        return nt_proc_gids(real, effective, saved)

    @wrap_exceptions
    def get_terminal(self):
        tty_nr = _psutil_osx.get_proc_tty_nr(self.pid)
        tmap = _psposix._get_terminal_map()
        try:
            return tmap[tty_nr]
        except KeyError:
            return None

    @wrap_exceptions
    def get_memory_info(self):
        """Return a tuple with the process' RSS and VMS size."""
        rss, vms = _psutil_osx.get_proc_memory_info(self.pid)[:2]
        return nt_proc_mem(rss, vms)

    @wrap_exceptions
    def get_ext_memory_info(self):
        """Return a tuple with the process' RSS and VMS size."""
        rss, vms, pfaults, pageins = \
            _psutil_osx.get_proc_memory_info(self.pid)
        return nt_proc_extmem(rss, vms,
                              pfaults * PAGESIZE,
                              pageins * PAGESIZE)

    @wrap_exceptions
    def get_cpu_times(self):
        user, system = _psutil_osx.get_proc_cpu_times(self.pid)
        return nt_proc_cpu(user, system)

    @wrap_exceptions
    def get_create_time(self):
        """Return the start time of the process as a number of seconds since
        the epoch."""
        return _psutil_osx.get_proc_create_time(self.pid)

    @wrap_exceptions
    def get_num_ctx_switches(self):
        return nt_proc_ctxsw(*_psutil_osx.get_proc_num_ctx_switches(self.pid))

    @wrap_exceptions
    def get_num_threads(self):
        """Return the number of threads belonging to the process."""
        return _psutil_osx.get_proc_num_threads(self.pid)

    @wrap_exceptions
    def get_open_files(self):
        """Return files opened by process."""
        if self.pid == 0:
            return []
        files = []
        rawlist = _psutil_osx.get_proc_open_files(self.pid)
        for path, fd in rawlist:
            if isfile_strict(path):
                ntuple = nt_proc_file(path, fd)
                files.append(ntuple)
        return files

    @wrap_exceptions
    def get_connections(self, kind='inet'):
        """Return etwork connections opened by a process as a list of
        namedtuples.
        """
        if kind not in conn_tmap:
            raise ValueError("invalid %r kind argument; choose between %s"
                             % (kind, ', '.join([repr(x) for x in conn_tmap])))
        families, types = conn_tmap[kind]
        rawlist = _psutil_osx.get_proc_connections(self.pid, families,
                                                   types)
        ret = []
        for item in rawlist:
            fd, fam, type, laddr, raddr, status = item
            status = TCP_STATUSES[status]
            nt = nt_connection(fd, fam, type, laddr, raddr, status)
            ret.append(nt)
        return ret

    @wrap_exceptions
    def get_num_fds(self):
        if self.pid == 0:
            return 0
        return _psutil_osx.get_proc_num_fds(self.pid)

    @wrap_exceptions
    def process_wait(self, timeout=None):
        try:
            return _psposix.wait_pid(self.pid, timeout)
        except TimeoutExpired:
            raise TimeoutExpired(self.pid, self._process_name)

    @wrap_exceptions
    def get_nice(self):
        return _psutil_posix.getpriority(self.pid)

    @wrap_exceptions
    def set_proc_nice(self, value):
        return _psutil_posix.setpriority(self.pid, value)

    @wrap_exceptions
    def get_status(self):
        code = _psutil_osx.get_proc_status(self.pid)
        # XXX is '?' legit? (we're not supposed to return it anyway)
        return PROC_STATUSES.get(code, '?')

    @wrap_exceptions
    def get_threads(self):
        """Return the number of threads belonging to the process."""
        rawlist = _psutil_osx.get_proc_threads(self.pid)
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
    def get_memory_maps(self):
        return _psutil_osx.get_proc_memory_maps(self.pid)
