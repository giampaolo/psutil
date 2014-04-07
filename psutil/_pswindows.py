#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Windows platform implementation."""

import errno
import os
import sys

from psutil import _common
from psutil._common import conn_tmap, usage_percent, isfile_strict
from psutil._compat import PY3, xrange, wraps, lru_cache, namedtuple
import _psutil_windows as cext

# process priority constants, import from __init__.py:
# http://msdn.microsoft.com/en-us/library/ms686219(v=vs.85).aspx
__extra__all__ = ["ABOVE_NORMAL_PRIORITY_CLASS", "BELOW_NORMAL_PRIORITY_CLASS",
                  "HIGH_PRIORITY_CLASS", "IDLE_PRIORITY_CLASS",
                  "NORMAL_PRIORITY_CLASS", "REALTIME_PRIORITY_CLASS",
                  #
                  "CONN_DELETE_TCB",
                  ]

# --- module level constants (gets pushed up to psutil module)

CONN_DELETE_TCB = "DELETE_TCB"
WAIT_TIMEOUT = 0x00000102  # 258 in decimal
ACCESS_DENIED_SET = frozenset([errno.EPERM, errno.EACCES,
                               cext.ERROR_ACCESS_DENIED])

TCP_STATUSES = {
    cext.MIB_TCP_STATE_ESTAB: _common.CONN_ESTABLISHED,
    cext.MIB_TCP_STATE_SYN_SENT: _common.CONN_SYN_SENT,
    cext.MIB_TCP_STATE_SYN_RCVD: _common.CONN_SYN_RECV,
    cext.MIB_TCP_STATE_FIN_WAIT1: _common.CONN_FIN_WAIT1,
    cext.MIB_TCP_STATE_FIN_WAIT2: _common.CONN_FIN_WAIT2,
    cext.MIB_TCP_STATE_TIME_WAIT: _common.CONN_TIME_WAIT,
    cext.MIB_TCP_STATE_CLOSED: _common.CONN_CLOSE,
    cext.MIB_TCP_STATE_CLOSE_WAIT: _common.CONN_CLOSE_WAIT,
    cext.MIB_TCP_STATE_LAST_ACK: _common.CONN_LAST_ACK,
    cext.MIB_TCP_STATE_LISTEN: _common.CONN_LISTEN,
    cext.MIB_TCP_STATE_CLOSING: _common.CONN_CLOSING,
    cext.MIB_TCP_STATE_DELETE_TCB: CONN_DELETE_TCB,
    cext.PSUTIL_CONN_NONE: _common.CONN_NONE,
}


scputimes = namedtuple('scputimes', ['user', 'system', 'idle'])
svmem = namedtuple('svmem', ['total', 'available', 'percent', 'used', 'free'])
pextmem = namedtuple(
    'pextmem', ['num_page_faults', 'peak_wset', 'wset', 'peak_paged_pool',
                'paged_pool', 'peak_nonpaged_pool', 'nonpaged_pool',
                'pagefile', 'peak_pagefile', 'private'])
pmmap_grouped = namedtuple('pmmap_grouped', ['path', 'rss'])
pmmap_ext = namedtuple(
    'pmmap_ext', 'addr perms ' + ' '.join(pmmap_grouped._fields))

# set later from __init__.py
NoSuchProcess = None
AccessDenied = None
TimeoutExpired = None


@lru_cache(maxsize=512)
def _win32_QueryDosDevice(s):
    return cext.win32_QueryDosDevice(s)


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


def virtual_memory():
    """System virtual memory as a namedtuple."""
    mem = cext.virtual_mem()
    totphys, availphys, totpagef, availpagef, totvirt, freevirt = mem
    #
    total = totphys
    avail = availphys
    free = availphys
    used = total - avail
    percent = usage_percent((total - avail), total, _round=1)
    return svmem(total, avail, percent, used, free)


def swap_memory():
    """Swap system memory as a (total, used, free, sin, sout) tuple."""
    mem = cext.virtual_mem()
    total = mem[2]
    free = mem[3]
    used = total - free
    percent = usage_percent(used, total, _round=1)
    return _common.sswap(total, used, free, percent, 0, 0)


def disk_usage(path):
    """Return disk usage associated with path."""
    try:
        total, free = cext.disk_usage(path)
    except WindowsError:
        if not os.path.exists(path):
            msg = "No such file or directory: '%s'" % path
            raise OSError(errno.ENOENT, msg)
        raise
    used = total - free
    percent = usage_percent(used, total, _round=1)
    return _common.sdiskusage(total, used, free, percent)


def disk_partitions(all):
    """Return disk partitions."""
    rawlist = cext.disk_partitions(all)
    return [_common.sdiskpart(*x) for x in rawlist]


def cpu_times():
    """Return system CPU times as a named tuple."""
    user, system, idle = cext.cpu_times()
    return scputimes(user, system, idle)


def per_cpu_times():
    """Return system per-CPU times as a list of named tuples."""
    ret = []
    for cpu_t in cext.per_cpu_times():
        user, system, idle = cpu_t
        item = scputimes(user, system, idle)
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


def net_connections(kind, _pid=-1):
    """Return socket connections.  If pid == -1 return system-wide
    connections (as opposed to connections opened by one process only).
    """
    if kind not in conn_tmap:
        raise ValueError("invalid %r kind argument; choose between %s"
                         % (kind, ', '.join([repr(x) for x in conn_tmap])))
    families, types = conn_tmap[kind]
    rawlist = cext.net_connections(_pid, families, types)
    ret = []
    for item in rawlist:
        fd, fam, type, laddr, raddr, status, pid = item
        status = TCP_STATUSES[status]
        if _pid == -1:
            nt = _common.sconn(fd, fam, type, laddr, raddr, status, pid)
        else:
            nt = _common.pconn(fd, fam, type, laddr, raddr, status)
        ret.append(nt)
    return ret


def users():
    """Return currently connected users as a list of namedtuples."""
    retlist = []
    rawlist = cext.users()
    for item in rawlist:
        user, hostname, tstamp = item
        nt = _common.suser(user, None, hostname, tstamp)
        retlist.append(nt)
    return retlist


pids = cext.pids
pid_exists = cext.pid_exists
net_io_counters = cext.net_io_counters
disk_io_counters = cext.disk_io_counters
ppid_map = cext.ppid_map  # not meant to be public


def wrap_exceptions(fun):
    """Decorator which translates bare OSError and WindowsError
    exceptions into NoSuchProcess and AccessDenied.
    """
    @wraps(fun)
    def wrapper(self, *args, **kwargs):
        try:
            return fun(self, *args, **kwargs)
        except OSError:
            # support for private module import
            if NoSuchProcess is None or AccessDenied is None:
                raise
            err = sys.exc_info()[1]
            if err.errno in ACCESS_DENIED_SET:
                raise AccessDenied(self.pid, self._name)
            if err.errno == errno.ESRCH:
                raise NoSuchProcess(self.pid, self._name)
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
            return os.path.basename(self.exe())

    @wrap_exceptions
    def exe(self):
        # Note: os.path.exists(path) may return False even if the file
        # is there, see:
        # http://stackoverflow.com/questions/3112546/os-path-exists-lies
        return _convert_raw_path(cext.proc_exe(self.pid))

    @wrap_exceptions
    def cmdline(self):
        return cext.proc_cmdline(self.pid)

    def ppid(self):
        try:
            return ppid_map()[self.pid]
        except KeyError:
            raise NoSuchProcess(self.pid, self._name)

    def _get_raw_meminfo(self):
        try:
            return cext.proc_memory_info(self.pid)
        except OSError:
            err = sys.exc_info()[1]
            if err.errno in ACCESS_DENIED_SET:
                return cext.proc_memory_info_2(self.pid)
            raise

    @wrap_exceptions
    def memory_info(self):
        # on Windows RSS == WorkingSetSize and VSM == PagefileUsage
        # fields of PROCESS_MEMORY_COUNTERS struct:
        # http://msdn.microsoft.com/en-us/library/windows/desktop/
        #     ms684877(v=vs.85).aspx
        t = self._get_raw_meminfo()
        return _common.pmem(t[2], t[7])

    @wrap_exceptions
    def memory_info_ex(self):
        return pextmem(*self._get_raw_meminfo())

    def memory_maps(self):
        try:
            raw = cext.proc_memory_maps(self.pid)
        except OSError:
            # XXX - can't use wrap_exceptions decorator as we're
            # returning a generator; probably needs refactoring.
            err = sys.exc_info()[1]
            if err.errno in ACCESS_DENIED_SET:
                raise AccessDenied(self.pid, self._name)
            if err.errno == errno.ESRCH:
                raise NoSuchProcess(self.pid, self._name)
            raise
        else:
            for addr, perm, path, rss in raw:
                path = _convert_raw_path(path)
                addr = hex(addr)
                yield (addr, perm, path, rss)

    @wrap_exceptions
    def kill(self):
        return cext.proc_kill(self.pid)

    @wrap_exceptions
    def wait(self, timeout=None):
        if timeout is None:
            timeout = cext.INFINITE
        else:
            # WaitForSingleObject() expects time in milliseconds
            timeout = int(timeout * 1000)
        ret = cext.proc_wait(self.pid, timeout)
        if ret == WAIT_TIMEOUT:
            # support for private module import
            if TimeoutExpired is None:
                raise RuntimeError("timeout expired")
            raise TimeoutExpired(timeout, self.pid, self._name)
        return ret

    @wrap_exceptions
    def username(self):
        if self.pid in (0, 4):
            return 'NT AUTHORITY\\SYSTEM'
        return cext.proc_username(self.pid)

    @wrap_exceptions
    def create_time(self):
        # special case for kernel process PIDs; return system boot time
        if self.pid in (0, 4):
            return boot_time()
        try:
            return cext.proc_create_time(self.pid)
        except OSError:
            err = sys.exc_info()[1]
            if err.errno in ACCESS_DENIED_SET:
                return cext.proc_create_time_2(self.pid)
            raise

    @wrap_exceptions
    def num_threads(self):
        return cext.proc_num_threads(self.pid)

    @wrap_exceptions
    def threads(self):
        rawlist = cext.proc_threads(self.pid)
        retlist = []
        for thread_id, utime, stime in rawlist:
            ntuple = _common.pthread(thread_id, utime, stime)
            retlist.append(ntuple)
        return retlist

    @wrap_exceptions
    def cpu_times(self):
        try:
            ret = cext.proc_cpu_times(self.pid)
        except OSError:
            err = sys.exc_info()[1]
            if err.errno in ACCESS_DENIED_SET:
                ret = cext.proc_cpu_times_2(self.pid)
            else:
                raise
        return _common.pcputimes(*ret)

    @wrap_exceptions
    def suspend(self):
        return cext.proc_suspend(self.pid)

    @wrap_exceptions
    def resume(self):
        return cext.proc_resume(self.pid)

    @wrap_exceptions
    def cwd(self):
        if self.pid in (0, 4):
            raise AccessDenied(self.pid, self._name)
        # return a normalized pathname since the native C function appends
        # "\\" at the and of the path
        path = cext.proc_cwd(self.pid)
        return os.path.normpath(path)

    @wrap_exceptions
    def open_files(self):
        if self.pid in (0, 4):
            return []
        retlist = []
        # Filenames come in in native format like:
        # "\Device\HarddiskVolume1\Windows\systemew\file.txt"
        # Convert the first part in the corresponding drive letter
        # (e.g. "C:\") by using Windows's QueryDosDevice()
        raw_file_names = cext.proc_open_files(self.pid)
        for file in raw_file_names:
            file = _convert_raw_path(file)
            if isfile_strict(file) and file not in retlist:
                ntuple = _common.popenfile(file, -1)
                retlist.append(ntuple)
        return retlist

    @wrap_exceptions
    def connections(self, kind='inet'):
        return net_connections(kind, _pid=self.pid)

    @wrap_exceptions
    def nice_get(self):
        return cext.proc_priority_get(self.pid)

    @wrap_exceptions
    def nice_set(self, value):
        return cext.proc_priority_set(self.pid, value)

    # available on Windows >= Vista
    if hasattr(cext, "proc_io_priority_get"):
        @wrap_exceptions
        def ionice_get(self):
            return cext.proc_io_priority_get(self.pid)

        @wrap_exceptions
        def ionice_set(self, value, _):
            if _:
                raise TypeError("set_proc_ionice() on Windows takes only "
                                "1 argument (2 given)")
            if value not in (2, 1, 0):
                raise ValueError("value must be 2 (normal), 1 (low) or 0 "
                                 "(very low); got %r" % value)
            return cext.proc_io_priority_set(self.pid, value)

    @wrap_exceptions
    def io_counters(self):
        try:
            ret = cext.proc_io_counters(self.pid)
        except OSError:
            err = sys.exc_info()[1]
            if err.errno in ACCESS_DENIED_SET:
                ret = cext.proc_io_counters_2(self.pid)
            else:
                raise
        return _common.pio(*ret)

    @wrap_exceptions
    def status(self):
        suspended = cext.proc_is_suspended(self.pid)
        if suspended:
            return _common.STATUS_STOPPED
        else:
            return _common.STATUS_RUNNING

    @wrap_exceptions
    def cpu_affinity_get(self):
        from_bitmask = lambda x: [i for i in xrange(64) if (1 << i) & x]
        bitmask = cext.proc_cpu_affinity_get(self.pid)
        return from_bitmask(bitmask)

    @wrap_exceptions
    def cpu_affinity_set(self, value):
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
        allcpus = list(range(len(per_cpu_times())))
        for cpu in value:
            if cpu not in allcpus:
                raise ValueError("invalid CPU %r" % cpu)

        bitmask = to_bitmask(value)
        cext.proc_cpu_affinity_set(self.pid, bitmask)

    @wrap_exceptions
    def num_handles(self):
        try:
            return cext.proc_num_handles(self.pid)
        except OSError:
            err = sys.exc_info()[1]
            if err.errno in ACCESS_DENIED_SET:
                return cext.proc_num_handles_2(self.pid)
            raise

    @wrap_exceptions
    def num_ctx_switches(self):
        tupl = cext.proc_num_ctx_switches(self.pid)
        return _common.pctxsw(*tupl)
