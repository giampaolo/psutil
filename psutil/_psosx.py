#!/usr/bin/env python

# Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""OSX platform implementation."""

import errno
import os
import sys
import warnings

import _psutil_osx
import _psutil_posix
from psutil import _psposix
from psutil._error import AccessDenied, NoSuchProcess, TimeoutExpired
from psutil._compat import namedtuple, wraps
from psutil._common import *

__extra__all__ = []

# --- constants

# Since these constants get determined at import time we do not want to
# crash immediately; instead we'll set them to None and most likely
# we'll crash later as they're used for determining process CPU stats
# and creation_time
try:
    NUM_CPUS = _psutil_osx.get_num_cpus()
except Exception:
    NUM_CPUS = None
    warnings.warn("couldn't determine platform's NUM_CPUS", RuntimeWarning)
try:
    BOOT_TIME = _psutil_osx.get_system_boot_time()
except Exception:
    BOOT_TIME = None
    warnings.warn("couldn't determine platform's BOOT_TIME", RuntimeWarning)
try:
    TOTAL_PHYMEM = _psutil_osx.get_virtual_mem()[0]
except Exception:
    TOTAL_PHYMEM = None
    warnings.warn("couldn't determine platform's TOTAL_PHYMEM", RuntimeWarning)

_PAGESIZE = os.sysconf("SC_PAGE_SIZE")
_cputimes_ntuple = namedtuple('cputimes', 'user nice system idle')

# --- functions

get_system_boot_time = _psutil_osx.get_system_boot_time

nt_virtmem_info = namedtuple('vmem', ' '.join([
    # all platforms
    'total', 'available', 'percent', 'used', 'free',
    # OSX specific
    'active',
    'inactive',
    'wired']))

def virtual_memory():
    """System virtual memory as a namedtuple."""
    total, active, inactive, wired, free = _psutil_osx.get_virtual_mem()
    avail = inactive + free
    used = active + inactive + wired
    percent = usage_percent((total - avail), total, _round=1)
    return nt_virtmem_info(total, avail, percent, used, free,
                           active, inactive, wired)

def swap_memory():
    """Swap system memory as a (total, used, free, sin, sout) tuple."""
    total, used, free, sin, sout = _psutil_osx.get_swap_mem()
    percent = usage_percent(used, total, _round=1)
    return nt_swapmeminfo(total, used, free, percent, sin, sout)

def get_system_cpu_times():
    """Return system CPU times as a namedtuple."""
    user, nice, system, idle = _psutil_osx.get_system_cpu_times()
    return _cputimes_ntuple(user, nice, system, idle)

def get_system_per_cpu_times():
    """Return system CPU times as a named tuple"""
    ret = []
    for cpu_t in _psutil_osx.get_system_per_cpu_times():
        user, nice, system, idle = cpu_t
        item = _cputimes_ntuple(user, nice, system, idle)
        ret.append(item)
    return ret

def disk_partitions(all=False):
    retlist = []
    partitions = _psutil_osx.get_disk_partitions()
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
    rawlist = _psutil_osx.get_system_users()
    for item in rawlist:
        user, tty, hostname, tstamp = item
        if tty == '~':
            continue  # reboot or shutdown
        if not tstamp:
            continue
        nt = nt_user(user, tty or None, hostname or None, tstamp)
        retlist.append(nt)
    return retlist


get_pid_list = _psutil_osx.get_pid_list
pid_exists = _psposix.pid_exists
get_disk_usage = _psposix.get_disk_usage
network_io_counters = _psutil_osx.get_network_io_counters
disk_io_counters = _psutil_osx.get_disk_io_counters

# --- decorator

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


_status_map = {
    _psutil_osx.SIDL : STATUS_IDLE,
    _psutil_osx.SRUN : STATUS_RUNNING,
    _psutil_osx.SSLEEP : STATUS_SLEEPING,
    _psutil_osx.SSTOP : STATUS_STOPPED,
    _psutil_osx.SZOMB : STATUS_ZOMBIE,
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
        return _psutil_osx.get_process_name(self.pid)

    @wrap_exceptions
    def get_process_exe(self):
        return _psutil_osx.get_process_exe(self.pid)

    @wrap_exceptions
    def get_process_cmdline(self):
        """Return process cmdline as a list of arguments."""
        if not pid_exists(self.pid):
            raise NoSuchProcess(self.pid, self._process_name)
        return _psutil_osx.get_process_cmdline(self.pid)

    @wrap_exceptions
    def get_process_ppid(self):
        """Return process parent pid."""
        return _psutil_osx.get_process_ppid(self.pid)

    @wrap_exceptions
    def get_process_cwd(self):
        return _psutil_osx.get_process_cwd(self.pid)

    @wrap_exceptions
    def get_process_uids(self):
        real, effective, saved = _psutil_osx.get_process_uids(self.pid)
        return nt_uids(real, effective, saved)

    @wrap_exceptions
    def get_process_gids(self):
        real, effective, saved = _psutil_osx.get_process_gids(self.pid)
        return nt_gids(real, effective, saved)

    @wrap_exceptions
    def get_process_terminal(self):
        tty_nr = _psutil_osx.get_process_tty_nr(self.pid)
        tmap = _psposix._get_terminal_map()
        try:
            return tmap[tty_nr]
        except KeyError:
            return None

    @wrap_exceptions
    def get_memory_info(self):
        """Return a tuple with the process' RSS and VMS size."""
        rss, vms = _psutil_osx.get_process_memory_info(self.pid)[:2]
        return nt_meminfo(rss, vms)

    _nt_ext_mem = namedtuple('meminfo', 'rss vms pfaults pageins')

    @wrap_exceptions
    def get_ext_memory_info(self):
        """Return a tuple with the process' RSS and VMS size."""
        rss, vms, pfaults, pageins = _psutil_osx.get_process_memory_info(self.pid)
        return self._nt_ext_mem(rss, vms,
                                pfaults * _PAGESIZE,
                                pageins * _PAGESIZE)

    @wrap_exceptions
    def get_cpu_times(self):
        user, system = _psutil_osx.get_process_cpu_times(self.pid)
        return nt_cputimes(user, system)

    @wrap_exceptions
    def get_process_create_time(self):
        """Return the start time of the process as a number of seconds since
        the epoch."""
        return _psutil_osx.get_process_create_time(self.pid)

    @wrap_exceptions
    def get_num_ctx_switches(self):
        return nt_ctxsw(*_psutil_osx.get_process_num_ctx_switches(self.pid))

    @wrap_exceptions
    def get_process_num_threads(self):
        """Return the number of threads belonging to the process."""
        return _psutil_osx.get_process_num_threads(self.pid)

    @wrap_exceptions
    def get_open_files(self):
        """Return files opened by process."""
        if self.pid == 0:
            return []
        files = []
        rawlist = _psutil_osx.get_process_open_files(self.pid)
        for path, fd in rawlist:
            if isfile_strict(path):
                ntuple = nt_openfile(path, fd)
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
        ret = _psutil_osx.get_process_connections(self.pid, families, types)
        return [nt_connection(*conn) for conn in ret]

    @wrap_exceptions
    def get_num_fds(self):
        if self.pid == 0:
            return 0
        return _psutil_osx.get_process_num_fds(self.pid)

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
        code = _psutil_osx.get_process_status(self.pid)
        if code in _status_map:
            return _status_map[code]
        return constant(-1, "?")

    @wrap_exceptions
    def get_process_threads(self):
        """Return the number of threads belonging to the process."""
        rawlist = _psutil_osx.get_process_threads(self.pid)
        retlist = []
        for thread_id, utime, stime in rawlist:
            ntuple = nt_thread(thread_id, utime, stime)
            retlist.append(ntuple)
        return retlist

    nt_mmap_grouped = namedtuple('mmap',
        'path rss private swapped dirtied ref_count shadow_depth')
    nt_mmap_ext = namedtuple('mmap',
        'addr perms path rss private swapped dirtied ref_count shadow_depth')

    @wrap_exceptions
    def get_memory_maps(self):
        return _psutil_osx.get_process_memory_maps(self.pid)
