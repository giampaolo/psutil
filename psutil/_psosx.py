#!/usr/bin/env python
#
# $Id$
#

import errno
import os

import _psutil_osx
import _psutil_posix
import _psposix
from psutil.error import AccessDenied, NoSuchProcess
from psutil._compat import namedtuple
from psutil._common import *

__all__ = base_module_namespace[:]

# --- constants

NUM_CPUS = _psutil_osx.get_num_cpus()
TOTAL_PHYMEM = _psutil_osx.get_total_phymem()

# --- functions

def avail_phymem():
    "Return the amount of physical memory available on the system, in bytes."
    return _psutil_osx.get_avail_phymem()

def used_phymem():
    "Return the amount of physical memory currently in use on the system, in bytes."
    return TOTAL_PHYMEM - _psutil_osx.get_avail_phymem()

def total_virtmem():
    "Return the amount of total virtual memory available on the system, in bytes."
    return _psutil_osx.get_total_virtmem()

def avail_virtmem():
    "Return the amount of virtual memory currently in use on the system, in bytes."
    return _psutil_osx.get_avail_virtmem()

def used_virtmem():
    """Return the amount of used memory currently in use on the system, in bytes."""
    return _psutil_osx.get_total_virtmem() - _psutil_osx.get_avail_virtmem()

_cputimes_ntuple = namedtuple('cputimes', 'user nice system idle')
def get_system_cpu_times():
    """Return system CPU times as a namedtuple."""
    user, nice, system, idle = _psutil_osx.get_system_cpu_times()
    return _cputimes_ntuple(user, nice, system, idle)

def get_pid_list():
    """Returns a list of PIDs currently running on the system."""
    return _psutil_osx.get_pid_list()

def pid_exists(pid):
    """Check For the existence of a unix pid."""
    return _psposix.pid_exists(pid)

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


class OSXProcess(object):
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
    def get_process_uid(self):
        """Return process real user id."""
        return _psutil_osx.get_process_uid(self.pid)

    @wrap_exceptions
    def get_process_gid(self):
        """Return process real group id."""
        return _psutil_osx.get_process_gid(self.pid)

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

    def get_open_files(self):
        """Return files opened by process by parsing lsof output."""
        lsof = _psposix.LsofParser(self.pid, self._process_name)
        return lsof.get_process_open_files()

    def get_connections(self):
        """Return etwork connections opened by a process as a list of
        namedtuples."""
        lsof = _psposix.LsofParser(self.pid, self._process_name)
        return lsof.get_process_connections()

    @wrap_exceptions
    def process_wait(self):
        return _psposix.wait_pid(self.pid)

    @wrap_exceptions
    def get_process_nice(self):
        return _psutil_posix.getpriority(self.pid)

    @wrap_exceptions
    def set_process_nice(self, value):
        return _psutil_posix.setpriority(self.pid, value)


PlatformProcess = OSXProcess

