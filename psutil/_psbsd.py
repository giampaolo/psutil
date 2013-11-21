#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""FreeBSD platform implementation."""

import errno
import os
import sys
import warnings

import _psutil_bsd
import _psutil_posix

from psutil import _psposix
from psutil._common import *
from psutil._compat import namedtuple, wraps
from psutil._error import AccessDenied, NoSuchProcess, TimeoutExpired

__extra__all__ = []

# --- constants

# Since these constants get determined at import time we do not want to
# crash immediately; instead we'll set them to None and most likely
# we'll crash later as they're used for determining process CPU stats
# and creation_time
try:
    NUM_CPUS = _psutil_bsd.get_num_cpus()
except Exception:
    NUM_CPUS = None
    warnings.warn("couldn't determine platform's NUM_CPUS", RuntimeWarning)
try:
    TOTAL_PHYMEM = _psutil_bsd.get_virtual_mem()[0]
except Exception:
    TOTAL_PHYMEM = None
    warnings.warn("couldn't determine platform's TOTAL_PHYMEM", RuntimeWarning)
try:
    BOOT_TIME = _psutil_bsd.get_system_boot_time()
except Exception:
    BOOT_TIME = None
    warnings.warn("couldn't determine platform's BOOT_TIME", RuntimeWarning)

PROC_STATUSES = {
    _psutil_bsd.SSTOP: STATUS_STOPPED,
    _psutil_bsd.SSLEEP: STATUS_SLEEPING,
    _psutil_bsd.SRUN: STATUS_RUNNING,
    _psutil_bsd.SIDL: STATUS_IDLE,
    _psutil_bsd.SWAIT: STATUS_WAITING,
    _psutil_bsd.SLOCK: STATUS_LOCKED,
    _psutil_bsd.SZOMB: STATUS_ZOMBIE,
}

TCP_STATUSES = {
    _psutil_bsd.TCPS_ESTABLISHED: CONN_ESTABLISHED,
    _psutil_bsd.TCPS_SYN_SENT: CONN_SYN_SENT,
    _psutil_bsd.TCPS_SYN_RECEIVED: CONN_SYN_RECV,
    _psutil_bsd.TCPS_FIN_WAIT_1: CONN_FIN_WAIT1,
    _psutil_bsd.TCPS_FIN_WAIT_2: CONN_FIN_WAIT2,
    _psutil_bsd.TCPS_TIME_WAIT: CONN_TIME_WAIT,
    _psutil_bsd.TCPS_CLOSED: CONN_CLOSE,
    _psutil_bsd.TCPS_CLOSE_WAIT: CONN_CLOSE_WAIT,
    _psutil_bsd.TCPS_LAST_ACK: CONN_LAST_ACK,
    _psutil_bsd.TCPS_LISTEN: CONN_LISTEN,
    _psutil_bsd.TCPS_CLOSING: CONN_CLOSING,
    _psutil_bsd.PSUTIL_CONN_NONE: CONN_NONE,
}

PAGESIZE = os.sysconf("SC_PAGE_SIZE")


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
    mem = _psutil_bsd.get_virtual_mem()
    total, free, active, inactive, wired, cached, buffers, shared = mem
    avail = inactive + cached + free
    used = active + wired + cached
    percent = usage_percent((total - avail), total, _round=1)
    return nt_virtmem_info(total, avail, percent, used, free,
                           active, inactive, buffers, cached, shared, wired)


def swap_memory():
    """System swap memory as (total, used, free, sin, sout) namedtuple."""
    total, used, free, sin, sout = \
        [x * PAGESIZE for x in _psutil_bsd.get_swap_mem()]
    percent = usage_percent(used, total, _round=1)
    return nt_swapmeminfo(total, used, free, percent, sin, sout)


_cputimes_ntuple = namedtuple('cputimes', 'user nice system idle irq')

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
            if not os.path.isabs(device) or not os.path.exists(device):
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
net_io_counters = _psutil_bsd.get_net_io_counters
disk_io_counters = _psutil_bsd.get_disk_io_counters
# not public; it's here because we need to test it from test_memory_leask.py
get_num_cpus = _psutil_bsd.get_num_cpus()
get_system_boot_time = _psutil_bsd.get_system_boot_time


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
        tmap = _psposix._get_terminal_map()
        try:
            return tmap[tty_nr]
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
        rawlist = _psutil_bsd.get_process_connections(self.pid, families, types)
        ret = []
        for item in rawlist:
            fd, fam, type, laddr, raddr, status = item
            status = TCP_STATUSES[status]
            nt = nt_connection(fd, fam, type, laddr, raddr, status)
            ret.append(nt)
        return ret

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
        if code in PROC_STATUSES:
            return PROC_STATUSES[code]
        # XXX is this legit? will we even ever get here?
        return "?"

    @wrap_exceptions
    def get_process_io_counters(self):
        rc, wc, rb, wb = _psutil_bsd.get_process_io_counters(self.pid)
        return nt_io(rc, wc, rb, wb)

    nt_mmap_grouped = namedtuple(
        'mmap', 'path rss, private, ref_count, shadow_count')
    nt_mmap_ext = namedtuple(
        'mmap', 'addr, perms path rss, private, ref_count, shadow_count')

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
