#!/usr/bin/env python
#
# $Id$
#
# Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""FreeBSD platform implementation."""

import errno
import os
import sys

import _psutil_bsd
import _psutil_posix
from psutil import _psposix
from psutil.error import AccessDenied, NoSuchProcess, TimeoutExpired
from psutil._compat import namedtuple
from psutil._common import *

__extra__all__ = []

# --- constants

NUM_CPUS = _psutil_bsd.get_num_cpus()
BOOT_TIME = _psutil_bsd.get_system_boot_time()
TOTAL_PHYMEM = _psutil_bsd.get_virtual_mem()[0]
_TERMINAL_MAP = _psposix._get_terminal_map()
_PAGESIZE = os.sysconf("SC_PAGE_SIZE")
_cputimes_ntuple = namedtuple('cputimes', 'user nice system idle irq')

# --- public functions

nt_virtmem_info = namedtuple('vmem', ' '.join([
    # all platforms
    'total', 'available', 'percent', 'used', 'free',
    # FreeBSD specific
    'active',
    'inactive',
    'buffers',
    'cached',
    'shared',
    'wired']))

def virtual_memory():
    """System virtual memory as a namedutple."""
    mem =  _psutil_bsd.get_virtual_mem()
    total, free, active, inactive, wired, cached, buffers, shared = mem
    avail = inactive + cached + free
    used =  active + wired + cached
    percent = usage_percent((total - avail), total, _round=1)
    return nt_virtmem_info(total, avail, percent, used, free,
                           active, inactive, buffers, cached, shared, wired)

def swap_memory():
    """System swap memory as (total, used, free, sin, sout) namedtuple."""
    total, used, free, sin, sout = \
        [x * _PAGESIZE for x in _psutil_bsd.get_swap_mem()]
    percent = usage_percent(used, total, _round=1)
    return nt_swapmeminfo(total, used, free, percent, sin, sout)

def get_system_cpu_times():
    """Return system per-CPU times as a named tuple"""
    user, nice, system, idle, irq = _psutil_bsd.get_system_cpu_times()
    return _cputimes_ntuple(user, nice, system, idle, irq)

def get_system_per_cpu_times():
    """Return system CPU times as a named tuple"""
    ret = []
    for cpu_t in _psutil_bsd.get_system_per_cpu_times():
        user, nice, system, idle, irq = cpu_t
        item = _cputimes_ntuple(user, nice, system, idle, irq)
        ret.append(item)
    return ret

# XXX
# Ok, this is very dirty.
# On FreeBSD < 8 we cannot gather per-cpu information, see:
# http://code.google.com/p/psutil/issues/detail?id=226
# If NUM_CPUS > 1, on first call we return single cpu times to avoid a
# crash at psutil import time.
# Next calls will fail with NotImplementedError
if not hasattr(_psutil_bsd, "get_system_per_cpu_times"):
    def get_system_per_cpu_times():
        if NUM_CPUS == 1:
            return [get_system_cpu_times]
        if get_system_per_cpu_times.__called__:
            raise NotImplementedError("supported only starting from FreeBSD 8")
        get_system_per_cpu_times.__called__ = True
        return [get_system_cpu_times]
get_system_per_cpu_times.__called__ = False

def disk_partitions(all=False):
    retlist = []
    partitions = _psutil_bsd.get_disk_partitions()
    for partition in partitions:
        device, mountpoint, fstype, opts = partition
        if device == 'none':
            device = ''
        if not all:
            if not os.path.isabs(device) \
            or not os.path.exists(device):
                continue
        ntuple = nt_partition(device, mountpoint, fstype, opts)
        retlist.append(ntuple)
    return retlist

def get_system_users():
    retlist = []
    rawlist = _psutil_bsd.get_system_users()
    for item in rawlist:
        user, tty, hostname, tstamp = item
        if tty == '~':
            continue  # reboot or shutdown
        nt = nt_user(user, tty or None, hostname, tstamp)
        retlist.append(nt)
    return retlist

get_pid_list = _psutil_bsd.get_pid_list
pid_exists = _psposix.pid_exists
get_disk_usage = _psposix.get_disk_usage
network_io_counters = _psutil_bsd.get_network_io_counters
disk_io_counters = _psutil_bsd.get_disk_io_counters


def wrap_exceptions(method):
    """Call method(self, pid) into a try/except clause so that if an
    OSError "No such process" exception is raised we assume the process
    has died and raise psutil.NoSuchProcess instead.
    """
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except OSError:
            err = sys.exc_info()[1]
            if err.errno == errno.ESRCH:
                raise NoSuchProcess(self.pid, self._process_name)
            if err.errno in (errno.EPERM, errno.EACCES):
                raise AccessDenied(self.pid, self._process_name)
            raise
    return wrapper

_status_map = {
    _psutil_bsd.SSTOP : STATUS_STOPPED,
    _psutil_bsd.SSLEEP : STATUS_SLEEPING,
    _psutil_bsd.SRUN : STATUS_RUNNING,
    _psutil_bsd.SIDL : STATUS_IDLE,
    _psutil_bsd.SWAIT : STATUS_WAITING,
    _psutil_bsd.SLOCK : STATUS_LOCKED,
    _psutil_bsd.SZOMB : STATUS_ZOMBIE,
}


class Process(object):
    """Wrapper class around underlying C implementation."""

    __slots__ = ["pid", "_process_name"]

    def __init__(self, pid):
        self.pid = pid
        self._process_name = None

    @wrap_exceptions
    def get_process_name(self):
        """Return process name as a string of limited len (15)."""
        return _psutil_bsd.get_process_name(self.pid)

    @wrap_exceptions
    def get_process_exe(self):
        """Return process executable pathname."""
        return _psutil_bsd.get_process_exe(self.pid)

    @wrap_exceptions
    def get_process_cmdline(self):
        """Return process cmdline as a list of arguments."""
        return _psutil_bsd.get_process_cmdline(self.pid)

    @wrap_exceptions
    def get_process_terminal(self):
        tty_nr = _psutil_bsd.get_process_tty_nr(self.pid)
        try:
            return _TERMINAL_MAP[tty_nr]
        except KeyError:
            return None

    @wrap_exceptions
    def get_process_ppid(self):
        """Return process parent pid."""
        return _psutil_bsd.get_process_ppid(self.pid)

    # XXX - available on FreeBSD >= 8 only
    if hasattr(_psutil_bsd, "get_process_cwd"):
        @wrap_exceptions
        def get_process_cwd(self):
            """Return process current working directory."""
            # sometimes we get an empty string, in which case we turn
            # it into None
            return _psutil_bsd.get_process_cwd(self.pid) or None

    @wrap_exceptions
    def get_process_uids(self):
        """Return real, effective and saved user ids."""
        real, effective, saved = _psutil_bsd.get_process_uids(self.pid)
        return nt_uids(real, effective, saved)

    @wrap_exceptions
    def get_process_gids(self):
        """Return real, effective and saved group ids."""
        real, effective, saved = _psutil_bsd.get_process_gids(self.pid)
        return nt_gids(real, effective, saved)

    @wrap_exceptions
    def get_cpu_times(self):
        """return a tuple containing process user/kernel time."""
        user, system = _psutil_bsd.get_process_cpu_times(self.pid)
        return nt_cputimes(user, system)

    @wrap_exceptions
    def get_memory_info(self):
        """Return a tuple with the process' RSS and VMS size."""
        rss, vms = _psutil_bsd.get_process_memory_info(self.pid)[:2]
        return nt_meminfo(rss, vms)

    _nt_ext_mem = namedtuple('meminfo', 'rss vms text data stack')

    @wrap_exceptions
    def get_ext_memory_info(self):
        return self._nt_ext_mem(*_psutil_bsd.get_process_memory_info(self.pid))

    @wrap_exceptions
    def get_process_create_time(self):
        """Return the start time of the process as a number of seconds since
        the epoch."""
        return _psutil_bsd.get_process_create_time(self.pid)

    @wrap_exceptions
    def get_process_num_threads(self):
        """Return the number of threads belonging to the process."""
        return _psutil_bsd.get_process_num_threads(self.pid)

    @wrap_exceptions
    def get_num_ctx_switches(self):
        return nt_ctxsw(*_psutil_bsd.get_process_num_ctx_switches(self.pid))

    @wrap_exceptions
    def get_num_fds(self):
        """Return the number of file descriptors opened by this process."""
        return _psutil_bsd.get_process_num_fds(self.pid)

    @wrap_exceptions
    def get_process_threads(self):
        """Return the number of threads belonging to the process."""
        rawlist = _psutil_bsd.get_process_threads(self.pid)
        retlist = []
        for thread_id, utime, stime in rawlist:
            ntuple = nt_thread(thread_id, utime, stime)
            retlist.append(ntuple)
        return retlist

    @wrap_exceptions
    def get_open_files(self):
        """Return files opened by process as a list of namedtuples."""
        # XXX - C implementation available on FreeBSD >= 8 only
        # else fallback on lsof parser
        if hasattr(_psutil_bsd, "get_process_open_files"):
            rawlist = _psutil_bsd.get_process_open_files(self.pid)
            return [nt_openfile(path, fd) for path, fd in rawlist]
        else:
            lsof = _psposix.LsofParser(self.pid, self._process_name)
            return lsof.get_process_open_files()

    @wrap_exceptions
    def get_connections(self, kind='inet'):
        """Return etwork connections opened by a process as a list of
        namedtuples.
        """
        if kind not in conn_tmap:
            raise ValueError("invalid %r kind argument; choose between %s"
                             % (kind, ', '.join([repr(x) for x in conn_tmap])))
        families, types = conn_tmap[kind]
        ret = _psutil_bsd.get_process_connections(self.pid, families, types)
        return [nt_connection(*conn) for conn in ret]

    @wrap_exceptions
    def process_wait(self, timeout=None):
        try:
            return _psposix.wait_pid(self.pid, timeout)
        except TimeoutExpired:
            raise TimeoutExpired(self.pid, self._process_name)

    @wrap_exceptions
    def get_process_nice(self):
        return _psutil_posix.getpriority(self.pid)

    @wrap_exceptions
    def set_process_nice(self, value):
        return _psutil_posix.setpriority(self.pid, value)

    @wrap_exceptions
    def get_process_status(self):
        code = _psutil_bsd.get_process_status(self.pid)
        if code in _status_map:
            return _status_map[code]
        return constant(-1, "?")

    @wrap_exceptions
    def get_process_io_counters(self):
        rc, wc, rb, wb = _psutil_bsd.get_process_io_counters(self.pid)
        return nt_io(rc, wc, rb, wb)

    nt_mmap_grouped = namedtuple('mmap',
        'path rss, private, ref_count, shadow_count')
    nt_mmap_ext = namedtuple('mmap',
        'addr, perms path rss, private, ref_count, shadow_count')

    @wrap_exceptions
    def get_memory_maps(self):
        return _psutil_bsd.get_process_memory_maps(self.pid)

    # FreeBSD < 8 does not support kinfo_getfile() and kinfo_getvmmap()
    if not hasattr(_psutil_bsd, 'get_process_open_files'):
        def _not_implemented(self):
            raise NotImplementedError("supported only starting from FreeBSD 8")
        get_open_files = _not_implemented
        get_process_cwd = _not_implemented
        get_memory_maps = _not_implemented
        get_num_fds = _not_implemented
