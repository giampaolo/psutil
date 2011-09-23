#!/usr/bin/env python
#
# $Id$
#

import errno
import os

import _psutil_bsd
import _psutil_posix
import _psposix
from psutil.error import AccessDenied, NoSuchProcess, TimeoutExpired
from psutil._compat import namedtuple
from psutil._common import *

__extra__all__ = []

# --- constants

NUM_CPUS = _psutil_bsd.get_num_cpus()
BOOT_TIME = _psutil_bsd.get_system_boot_time()
_TERMINAL_MAP = _psposix._get_terminal_map()
_cputimes_ntuple = namedtuple('cputimes', 'user nice system idle irq')

# --- public functions

def phymem_usage():
    """Physical system memory as a (total, used, free) tuple."""
    total = _psutil_bsd.get_total_phymem()
    free =  _psutil_bsd.get_avail_phymem()
    used = total - free
    # XXX check out whether we have to do the same math we do on Linux
    percent = usage_percent(used, total, _round=1)
    return ntuple_sysmeminfo(total, used, free, percent)

def virtmem_usage():
    """Virtual system memory as a (total, used, free) tuple."""
    total = _psutil_bsd.get_total_virtmem()
    free =  _psutil_bsd.get_avail_virtmem()
    used = total - free
    percent = usage_percent(used, total, _round=1)
    return ntuple_sysmeminfo(total, used, free, percent)

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

def disk_partitions(all=False):
    retlist = []
    partitions = _psutil_bsd.get_disk_partitions()
    for partition in partitions:
        device, mountpoint, fstype = partition
        if device == 'none':
            device = ''
        if not all:
            if not os.path.isabs(device) \
            or not os.path.exists(device):
                continue
        ntuple = ntuple_partition(device, mountpoint, fstype)
        retlist.append(ntuple)
    return retlist

get_pid_list = _psutil_bsd.get_pid_list
pid_exists = _psposix.pid_exists
get_disk_usage = _psposix.get_disk_usage
network_io_counters = _psutil_osx.get_network_io_counters


def wrap_exceptions(method):
    """Call method(self, pid) into a try/except clause so that if an
    OSError "No such process" exception is raised we assume the process
    has died and raise psutil.NoSuchProcess instead.
    """
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except OSError, err:
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

    @wrap_exceptions
    def get_process_uids(self):
        """Return real, effective and saved user ids."""
        real, effective, saved = _psutil_bsd.get_process_uids(self.pid)
        return ntuple_uids(real, effective, saved)

    @wrap_exceptions
    def get_process_gids(self):
        """Return real, effective and saved group ids."""
        real, effective, saved = _psutil_bsd.get_process_gids(self.pid)
        return ntuple_gids(real, effective, saved)

    @wrap_exceptions
    def get_cpu_times(self):
        """return a tuple containing process user/kernel time."""
        user, system = _psutil_bsd.get_cpu_times(self.pid)
        return ntuple_cputimes(user, system)

    @wrap_exceptions
    def get_memory_info(self):
        """Return a tuple with the process' RSS and VMS size."""
        rss, vms = _psutil_bsd.get_memory_info(self.pid)
        return ntuple_meminfo(rss, vms)

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
    def get_process_threads(self):
        """Return the number of threads belonging to the process."""
        rawlist = _psutil_bsd.get_process_threads(self.pid)
        retlist = []
        for thread_id, utime, stime in rawlist:
            ntuple = ntuple_thread(thread_id, utime, stime)
            retlist.append(ntuple)
        return retlist


    def get_open_files(self):
        """Return files opened by process by parsing lsof output."""
        lsof = _psposix.LsofParser(self.pid, self._process_name)
        return lsof.get_process_open_files()

    def get_connections(self):
        """Return network connections opened by a process as a list of
        namedtuples by parsing lsof output.
        """
        lsof = _psposix.LsofParser(self.pid, self._process_name)
        return lsof.get_process_connections()

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
        return ntuple_io(rc, wc, rb, wb)
