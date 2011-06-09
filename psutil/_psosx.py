#!/usr/bin/env python
#
# $Id$
#

import errno
import os

import _psutil_osx
import _psutil_posix
import _psposix
from psutil.error import AccessDenied, NoSuchProcess, TimeoutExpired
from psutil._compat import namedtuple
from psutil._common import *

__extra__all__ = []

# --- constants

NUM_CPUS = _psutil_osx.get_num_cpus()
BOOT_TIME = _psutil_osx.get_system_boot_time()
_cputimes_ntuple = namedtuple('cputimes', 'user nice system idle')

# --- functions

def get_phymem():
    """Physical system memory as a (total, used, free) tuple."""
    total = _psutil_osx.get_total_phymem()
    free =  _psutil_osx.get_avail_phymem()
    used = total - free
    return (total, used, free)

def get_virtmem():
    """Virtual system memory as a (total, used, free) tuple."""
    total = _psutil_osx.get_total_virtmem()
    free =  _psutil_osx.get_avail_virtmem()
    used = total - free
    return (total, used, free)

def get_system_per_cpu_times():
    # XXX
    raise NotImplementedError

get_pid_list = _psutil_osx.get_pid_list
pid_exists = _psposix.pid_exists

# --- decorator

def wrap_exceptions(callable):
    """Call callable into a try/except clause so that if an
    OSError EPERM exception is raised we translate it into
    psutil.AccessDenied.
    """
    def wrapper(self, *args, **kwargs):
        try:
            return callable(self, *args, **kwargs)
        except OSError, err:
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

    def get_process_exe(self):
        # no such thing as "exe" on OS X; it will maybe be determined
        # later from cmdline[0]
        if not pid_exists(self.pid):
            raise NoSuchProcess(self.pid, self._process_name)
        return ""

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
    def get_process_uids(self):
        real, effective, saved = _psutil_osx.get_process_uids(self.pid)
        return ntuple_uids(real, effective, saved)


    @wrap_exceptions
    def get_process_gids(self):
        real, effective, saved = _psutil_osx.get_process_gids(self.pid)
        return ntuple_gids(real, effective, saved)

    @wrap_exceptions
    def get_memory_info(self):
        """Return a tuple with the process' RSS and VMS size."""
        rss, vms = _psutil_osx.get_memory_info(self.pid)
        return ntuple_meminfo(rss, vms)

    @wrap_exceptions
    def get_cpu_times(self):
        user, system = _psutil_osx.get_cpu_times(self.pid)
        return ntuple_cputimes(user, system)

    @wrap_exceptions
    def get_process_create_time(self):
        """Return the start time of the process as a number of seconds since
        the epoch."""
        return _psutil_osx.get_process_create_time(self.pid)

    @wrap_exceptions
    def get_process_num_threads(self):
        """Return the number of threads belonging to the process."""
        return _psutil_osx.get_process_num_threads(self.pid)

    @wrap_exceptions
    def get_open_files(self):
        """Return files opened by process."""
        if self.pid == 0:
            raise AccessDenied(self.pid, self._process_name)
        files = []
        rawlist = _psutil_osx.get_process_open_files(self.pid)
        for path, fd in rawlist:
            if os.path.isfile(path):
                ntuple = ntuple_openfile(path, fd)
                files.append(ntuple)
        return files

    @wrap_exceptions
    def get_connections(self):
        """Return etwork connections opened by a process as a list of
        namedtuples."""
        retlist = _psutil_osx.get_process_connections(self.pid)
        return [ntuple_connection(*conn) for conn in retlist]

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
            ntuple = ntuple_thread(thread_id, utime, stime)
            retlist.append(ntuple)
        return retlist
