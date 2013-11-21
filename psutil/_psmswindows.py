#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Windows platform implementation."""

import errno
import os
import sys
import warnings

import _psutil_mswindows

from _psutil_mswindows import ERROR_ACCESS_DENIED
from psutil._common import *
from psutil._compat import PY3, xrange, wraps
from psutil._error import AccessDenied, NoSuchProcess, TimeoutExpired

# process priority constants:
# http://msdn.microsoft.com/en-us/library/ms686219(v=vs.85).aspx
from _psutil_mswindows import (ABOVE_NORMAL_PRIORITY_CLASS,
                               BELOW_NORMAL_PRIORITY_CLASS,
                               HIGH_PRIORITY_CLASS,
                               IDLE_PRIORITY_CLASS,
                               NORMAL_PRIORITY_CLASS,
                               REALTIME_PRIORITY_CLASS,
                               INFINITE)


# Windows specific extended namespace
__extra__all__ = ["ABOVE_NORMAL_PRIORITY_CLASS", "BELOW_NORMAL_PRIORITY_CLASS",
                  "HIGH_PRIORITY_CLASS", "IDLE_PRIORITY_CLASS",
                  "NORMAL_PRIORITY_CLASS", "REALTIME_PRIORITY_CLASS",
                  #
                  "CONN_DELETE_TCB",
                  ]

# --- module level constants (gets pushed up to psutil module)

# Since these constants get determined at import time we do not want to
# crash immediately; instead we'll set them to None and most likely
# we'll crash later as they're used for determining process CPU stats
# and creation_time
try:
    NUM_CPUS = _psutil_mswindows.get_num_cpus()
except Exception:
    NUM_CPUS = None
    warnings.warn("couldn't determine platform's NUM_CPUS", RuntimeWarning)
try:
    BOOT_TIME = _psutil_mswindows.get_system_boot_time()
except Exception:
    BOOT_TIME = None
    warnings.warn("couldn't determine platform's BOOT_TIME", RuntimeWarning)
try:
    TOTAL_PHYMEM = _psutil_mswindows.get_virtual_mem()[0]
except Exception:
    TOTAL_PHYMEM = None
    warnings.warn("couldn't determine platform's TOTAL_PHYMEM", RuntimeWarning)

CONN_DELETE_TCB = "DELETE_TCB"
WAIT_TIMEOUT = 0x00000102  # 258 in decimal
ACCESS_DENIED_SET = frozenset([errno.EPERM, errno.EACCES, ERROR_ACCESS_DENIED])

TCP_STATUSES = {
    _psutil_mswindows.MIB_TCP_STATE_ESTAB: CONN_ESTABLISHED,
    _psutil_mswindows.MIB_TCP_STATE_SYN_SENT: CONN_SYN_SENT,
    _psutil_mswindows.MIB_TCP_STATE_SYN_RCVD: CONN_SYN_RECV,
    _psutil_mswindows.MIB_TCP_STATE_FIN_WAIT1: CONN_FIN_WAIT1,
    _psutil_mswindows.MIB_TCP_STATE_FIN_WAIT2: CONN_FIN_WAIT2,
    _psutil_mswindows.MIB_TCP_STATE_TIME_WAIT: CONN_TIME_WAIT,
    _psutil_mswindows.MIB_TCP_STATE_CLOSED: CONN_CLOSE,
    _psutil_mswindows.MIB_TCP_STATE_CLOSE_WAIT: CONN_CLOSE_WAIT,
    _psutil_mswindows.MIB_TCP_STATE_LAST_ACK: CONN_LAST_ACK,
    _psutil_mswindows.MIB_TCP_STATE_LISTEN: CONN_LISTEN,
    _psutil_mswindows.MIB_TCP_STATE_CLOSING: CONN_CLOSING,
    _psutil_mswindows.MIB_TCP_STATE_DELETE_TCB: CONN_DELETE_TCB,
    _psutil_mswindows.PSUTIL_CONN_NONE: CONN_NONE,
}


@memoize
def _win32_QueryDosDevice(s):
    return _psutil_mswindows.win32_QueryDosDevice(s)


def _convert_raw_path(s):
    # convert paths using native DOS format like:
    # "\Device\HarddiskVolume1\Windows\systemew\file.txt"
    # into: "C:\Windows\systemew\file.txt"
    if PY3 and not isinstance(s, str):
        s = s.decode('utf8')
    rawdrive = '\\'.join(s.split('\\')[:3])
    driveletter = _win32_QueryDosDevice(rawdrive)
    return os.path.join(driveletter, s[len(rawdrive):])


# --- public functions

get_system_boot_time = _psutil_mswindows.get_system_boot_time
# ...so that we can test it from test_memory_leask.py
get_num_cpus = _psutil_mswindows.get_num_cpus()


nt_virtmem_info = namedtuple('vmem', ' '.join([
    # all platforms
    'total', 'available', 'percent', 'used', 'free']))

def virtual_memory():
    """System virtual memory as a namedtuple."""
    mem = _psutil_mswindows.get_virtual_mem()
    totphys, availphys, totpagef, availpagef, totvirt, freevirt = mem
    #
    total = totphys
    avail = availphys
    free = availphys
    used = total - avail
    percent = usage_percent((total - avail), total, _round=1)
    return nt_virtmem_info(total, avail, percent, used, free)


def swap_memory():
    """Swap system memory as a (total, used, free, sin, sout) tuple."""
    mem = _psutil_mswindows.get_virtual_mem()
    total = mem[2]
    free = mem[3]
    used = total - free
    percent = usage_percent(used, total, _round=1)
    return nt_swapmeminfo(total, used, free, percent, 0, 0)


def get_disk_usage(path):
    """Return disk usage associated with path."""
    try:
        total, free = _psutil_mswindows.get_disk_usage(path)
    except WindowsError:
        if not os.path.exists(path):
            raise OSError(errno.ENOENT, "No such file or directory: '%s'" % path)
        raise
    used = total - free
    percent = usage_percent(used, total, _round=1)
    return nt_diskinfo(total, used, free, percent)


def disk_partitions(all):
    """Return disk partitions."""
    rawlist = _psutil_mswindows.get_disk_partitions(all)
    return [nt_partition(*x) for x in rawlist]


_cputimes_ntuple = namedtuple('cputimes', 'user system idle')

def get_system_cpu_times():
    """Return system CPU times as a named tuple."""
    user, system, idle = _psutil_mswindows.get_system_cpu_times()
    return _cputimes_ntuple(user, system, idle)


def get_system_per_cpu_times():
    """Return system per-CPU times as a list of named tuples."""
    ret = []
    for cpu_t in _psutil_mswindows.get_system_per_cpu_times():
        user, system, idle = cpu_t
        item = _cputimes_ntuple(user, system, idle)
        ret.append(item)
    return ret


def get_system_users():
    """Return currently connected users as a list of namedtuples."""
    retlist = []
    rawlist = _psutil_mswindows.get_system_users()
    for item in rawlist:
        user, hostname, tstamp = item
        nt = nt_user(user, None, hostname, tstamp)
        retlist.append(nt)
    return retlist


get_pid_list = _psutil_mswindows.get_pid_list
pid_exists = _psutil_mswindows.pid_exists
net_io_counters = _psutil_mswindows.get_net_io_counters
disk_io_counters = _psutil_mswindows.get_disk_io_counters
get_ppid_map = _psutil_mswindows.get_ppid_map  # not meant to be public


def wrap_exceptions(fun):
    """Decorator which translates bare OSError and WindowsError
    exceptions into NoSuchProcess and AccessDenied.
    """
    @wraps(fun)
    def wrapper(self, *args, **kwargs):
        try:
            return fun(self, *args, **kwargs)
        except OSError:
            err = sys.exc_info()[1]
            if err.errno in ACCESS_DENIED_SET:
                raise AccessDenied(self.pid, self._process_name)
            if err.errno == errno.ESRCH:
                raise NoSuchProcess(self.pid, self._process_name)
            raise
    return wrapper


class Process(object):
    """Wrapper class around underlying C implementation."""

    __slots__ = ["pid", "_process_name"]

    def __init__(self, pid):
        self.pid = pid
        self._process_name = None

    @wrap_exceptions
    def get_process_name(self):
        """Return process name, which on Windows is always the final
        part of the executable.
        """
        # This is how PIDs 0 and 4 are always represented in taskmgr
        # and process-hacker.
        if self.pid == 0:
            return "System Idle Process"
        elif self.pid == 4:
            return "System"
        else:
            return os.path.basename(self.get_process_exe())

    @wrap_exceptions
    def get_process_exe(self):
        # Note: os.path.exists(path) may return False even if the file
        # is there, see:
        # http://stackoverflow.com/questions/3112546/os-path-exists-lies
        return _convert_raw_path(_psutil_mswindows.get_process_exe(self.pid))

    @wrap_exceptions
    def get_process_cmdline(self):
        """Return process cmdline as a list of arguments."""
        return _psutil_mswindows.get_process_cmdline(self.pid)

    def get_process_ppid(self):
        """Return process parent pid."""
        try:
            return get_ppid_map()[self.pid]
        except KeyError:
            raise NoSuchProcess(self.pid, self._process_name)

    def _get_raw_meminfo(self):
        try:
            return _psutil_mswindows.get_process_memory_info(self.pid)
        except OSError:
            err = sys.exc_info()[1]
            if err.errno in ACCESS_DENIED_SET:
                return _psutil_mswindows.get_process_memory_info_2(self.pid)
            raise

    @wrap_exceptions
    def get_memory_info(self):
        """Returns a tuple or RSS/VMS memory usage in bytes."""
        # on Windows RSS == WorkingSetSize and VSM == PagefileUsage
        # fields of PROCESS_MEMORY_COUNTERS struct:
        # http://msdn.microsoft.com/en-us/library/windows/desktop/ms684877(v=vs.85).aspx
        t = self._get_raw_meminfo()
        return nt_meminfo(t[2], t[7])

    _nt_ext_mem = namedtuple('meminfo', ' '.join([
        'num_page_faults',
        'peak_wset',
        'wset',
        'peak_paged_pool',
        'paged_pool',
        'peak_nonpaged_pool',
        'nonpaged_pool',
        'pagefile',
        'peak_pagefile',
        'private']))

    @wrap_exceptions
    def get_ext_memory_info(self):
        return self._nt_ext_mem(*self._get_raw_meminfo())

    nt_mmap_grouped = namedtuple('mmap', 'path rss')
    nt_mmap_ext = namedtuple('mmap', 'addr perms path rss')

    def get_memory_maps(self):
        try:
            raw = _psutil_mswindows.get_process_memory_maps(self.pid)
        except OSError:
            # XXX - can't use wrap_exceptions decorator as we're
            # returning a generator; probably needs refactoring.
            err = sys.exc_info()[1]
            if err.errno in (errno.EPERM, errno.EACCES, ERROR_ACCESS_DENIED):
                raise AccessDenied(self.pid, self._process_name)
            if err.errno == errno.ESRCH:
                raise NoSuchProcess(self.pid, self._process_name)
            raise
        else:
            for addr, perm, path, rss in raw:
                path = _convert_raw_path(path)
                addr = hex(addr)
                yield (addr, perm, path, rss)

    @wrap_exceptions
    def kill_process(self):
        """Terminates the process with the given PID."""
        return _psutil_mswindows.kill_process(self.pid)

    @wrap_exceptions
    def process_wait(self, timeout=None):
        if timeout is None:
            timeout = INFINITE
        else:
            # WaitForSingleObject() expects time in milliseconds
            timeout = int(timeout * 1000)
        ret = _psutil_mswindows.process_wait(self.pid, timeout)
        if ret == WAIT_TIMEOUT:
            raise TimeoutExpired(self.pid, self._process_name)
        return ret

    @wrap_exceptions
    def get_process_username(self):
        """Return the name of the user that owns the process"""
        if self.pid in (0, 4):
            return 'NT AUTHORITY\\SYSTEM'
        return _psutil_mswindows.get_process_username(self.pid)

    @wrap_exceptions
    def get_process_create_time(self):
        # special case for kernel process PIDs; return system boot time
        if self.pid in (0, 4):
            return BOOT_TIME
        try:
            return _psutil_mswindows.get_process_create_time(self.pid)
        except OSError:
            err = sys.exc_info()[1]
            if err.errno in ACCESS_DENIED_SET:
                return _psutil_mswindows.get_process_create_time_2(self.pid)
            raise

    @wrap_exceptions
    def get_process_num_threads(self):
        return _psutil_mswindows.get_process_num_threads(self.pid)

    @wrap_exceptions
    def get_process_threads(self):
        rawlist = _psutil_mswindows.get_process_threads(self.pid)
        retlist = []
        for thread_id, utime, stime in rawlist:
            ntuple = nt_thread(thread_id, utime, stime)
            retlist.append(ntuple)
        return retlist

    @wrap_exceptions
    def get_cpu_times(self):
        try:
            ret = _psutil_mswindows.get_process_cpu_times(self.pid)
        except OSError:
            err = sys.exc_info()[1]
            if err.errno in ACCESS_DENIED_SET:
                ret = _psutil_mswindows.get_process_cpu_times_2(self.pid)
            else:
                raise
        return nt_cputimes(*ret)

    @wrap_exceptions
    def suspend_process(self):
        return _psutil_mswindows.suspend_process(self.pid)

    @wrap_exceptions
    def resume_process(self):
        return _psutil_mswindows.resume_process(self.pid)

    @wrap_exceptions
    def get_process_cwd(self):
        if self.pid in (0, 4):
            raise AccessDenied(self.pid, self._process_name)
        # return a normalized pathname since the native C function appends
        # "\\" at the and of the path
        path = _psutil_mswindows.get_process_cwd(self.pid)
        return os.path.normpath(path)

    @wrap_exceptions
    def get_open_files(self):
        if self.pid in (0, 4):
            return []
        retlist = []
        # Filenames come in in native format like:
        # "\Device\HarddiskVolume1\Windows\systemew\file.txt"
        # Convert the first part in the corresponding drive letter
        # (e.g. "C:\") by using Windows's QueryDosDevice()
        raw_file_names = _psutil_mswindows.get_process_open_files(self.pid)
        for file in raw_file_names:
            file = _convert_raw_path(file)
            if isfile_strict(file) and file not in retlist:
                ntuple = nt_openfile(file, -1)
                retlist.append(ntuple)
        return retlist

    @wrap_exceptions
    def get_connections(self, kind='inet'):
        if kind not in conn_tmap:
            raise ValueError("invalid %r kind argument; choose between %s"
                             % (kind, ', '.join([repr(x) for x in conn_tmap])))
        families, types = conn_tmap[kind]
        rawlist = _psutil_mswindows.get_process_connections(self.pid, families,
                                                            types)
        ret = []
        for item in rawlist:
            fd, fam, type, laddr, raddr, status = item
            status = TCP_STATUSES[status]
            nt = nt_connection(fd, fam, type, laddr, raddr, status)
            ret.append(nt)
        return ret

    @wrap_exceptions
    def get_process_nice(self):
        return _psutil_mswindows.get_process_priority(self.pid)

    @wrap_exceptions
    def set_process_nice(self, value):
        return _psutil_mswindows.set_process_priority(self.pid, value)

    # available on Windows >= Vista
    if hasattr(_psutil_mswindows, "get_process_io_priority"):
        @wrap_exceptions
        def get_process_ionice(self):
            return _psutil_mswindows.get_process_io_priority(self.pid)

        @wrap_exceptions
        def set_process_ionice(self, value, _):
            if _:
                raise TypeError("set_process_ionice() on Windows takes only "
                                "1 argument (2 given)")
            if value not in (2, 1, 0):
                raise ValueError("value must be 2 (normal), 1 (low) or 0 "
                                 "(very low); got %r" % value)
            return _psutil_mswindows.set_process_io_priority(self.pid, value)

    @wrap_exceptions
    def get_process_io_counters(self):
        try:
            ret = _psutil_mswindows.get_process_io_counters(self.pid)
        except OSError:
            err = sys.exc_info()[1]
            if err.errno in ACCESS_DENIED_SET:
                ret = _psutil_mswindows.get_process_io_counters_2(self.pid)
            else:
                raise
        return nt_io(*ret)

    @wrap_exceptions
    def get_process_status(self):
        suspended = _psutil_mswindows.is_process_suspended(self.pid)
        if suspended:
            return STATUS_STOPPED
        else:
            return STATUS_RUNNING

    @wrap_exceptions
    def get_process_cpu_affinity(self):
        from_bitmask = lambda x: [i for i in xrange(64) if (1 << i) & x]
        bitmask = _psutil_mswindows.get_process_cpu_affinity(self.pid)
        return from_bitmask(bitmask)

    @wrap_exceptions
    def set_process_cpu_affinity(self, value):
        def to_bitmask(l):
            if not l:
                raise ValueError("invalid argument %r" % l)
            out = 0
            for b in l:
                out |= 2 ** b
            return out

        # SetProcessAffinityMask() states that ERROR_INVALID_PARAMETER
        # is returned for an invalid CPU but this seems not to be true,
        # therefore we check CPUs validy beforehand.
        allcpus = list(range(len(get_system_per_cpu_times())))
        for cpu in value:
            if cpu not in allcpus:
                raise ValueError("invalid CPU %r" % cpu)

        bitmask = to_bitmask(value)
        _psutil_mswindows.set_process_cpu_affinity(self.pid, bitmask)

    @wrap_exceptions
    def get_num_handles(self):
        try:
            return _psutil_mswindows.get_process_num_handles(self.pid)
        except OSError:
            err = sys.exc_info()[1]
            if err.errno in ACCESS_DENIED_SET:
                return _psutil_mswindows.get_process_num_handles_2(self.pid)
            raise

    @wrap_exceptions
    def get_num_ctx_switches(self):
        tupl = _psutil_mswindows.get_process_num_ctx_switches(self.pid)
        return nt_ctxsw(*tupl)
