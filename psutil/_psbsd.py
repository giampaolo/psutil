#!/usr/bin/env python
#
# $Id$
#

import errno
import os

try:
    from collections import namedtuple
except ImportError:
    from psutil.compat import namedtuple  # python < 2.6

import _psutil_bsd
import _psposix
from psutil.error import AccessDenied, NoSuchProcess


# --- constants

NUM_CPUS = _psutil_bsd.get_num_cpus()
TOTAL_PHYMEM = _psutil_bsd.get_total_phymem()

# --- public functions

def avail_phymem():
    "Return the amount of physical memory available on the system, in bytes."
    return _psutil_bsd.get_avail_phymem()

def used_phymem():
    "Return the amount of physical memory currently in use on the system, in bytes."
    return TOTAL_PHYMEM - _psutil_bsd.get_avail_phymem()

def total_virtmem():
    "Return the amount of total virtual memory available on the system, in bytes."
    return _psutil_bsd.get_total_virtmem()

def avail_virtmem():
    "Return the amount of virtual memory currently in use on the system, in bytes."
    return _psutil_bsd.get_avail_virtmem()

def used_virtmem():
    """Return the amount of used memory currently in use on the system, in bytes."""
    return _psutil_bsd.get_total_virtmem() - _psutil_bsd.get_avail_virtmem()

def get_system_cpu_times():
    """Return a dict representing the following CPU times:
    user, nice, system, idle, interrupt."""
    values = _psutil_bsd.get_system_cpu_times()
    return dict(user=values[0], nice=values[1], system=values[2],
        idle=values[3], irq=values[4])

def get_pid_list():
    """Returns a list of PIDs currently running on the system."""
    return _psutil_bsd.get_pid_list()

def pid_exists(pid):
    """Check For the existence of a unix pid."""
    return _psposix.pid_exists(pid)


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
            if err.errno == errno.EPERM:
                raise AccessDenied(self.pid, self._process_name)
            raise
    return wrapper


class BSDProcess(object):
    """Wrapper class around underlying C implementation."""

    _meminfo_ntuple = namedtuple('meminfo', 'rss vms')
    _cputimes_ntuple = namedtuple('cputimes', 'user system')
    __slots__ = ["pid", "_process_name"]

    def __init__(self, pid):
        self.pid = pid
        self._process_name = None

    @wrap_exceptions
    def get_process_name(self):
        """Return process name as a string of limited len (15)."""
        return _psutil_bsd.get_process_name(self.pid)

    def get_process_exe(self):
        # no such thing as "exe" on BSD; it will maybe be determined
        # later from cmdline[0]
        return ""

    @wrap_exceptions
    def get_process_cmdline(self):
        """Return process cmdline as a list of arguments."""
        return _psutil_bsd.get_process_cmdline(self.pid)

    @wrap_exceptions
    def get_process_ppid(self):
        """Return process parent pid."""
        return _psutil_bsd.get_process_ppid(self.pid)

    @wrap_exceptions
    def get_process_uid(self):
        """Return process real user id."""
        return _psutil_bsd.get_process_uid(self.pid)

    @wrap_exceptions
    def get_process_gid(self):
        """Return process real group id."""
        return _psutil_bsd.get_process_gid(self.pid)

    @wrap_exceptions
    def get_cpu_times(self):
        """return a tuple containing process user/kernel time."""
        user, system = _psutil_bsd.get_cpu_times(self.pid)
        return self._cputimes_ntuple(user, system)

    @wrap_exceptions
    def get_memory_info(self):
        """Return a tuple with the process' RSS and VMS size."""
        rss, vms = _psutil_bsd.get_memory_info(self.pid)
        return self._meminfo_ntuple(rss, vms)

    @wrap_exceptions
    def get_process_create_time(self):
        """Return the start time of the process as a number of seconds since
        the epoch."""
        return _psutil_bsd.get_process_create_time(self.pid)

    @wrap_exceptions
    def get_process_num_threads(self):
        """Return the number of threads belonging to the process."""
        return _psutil_bsd.get_process_num_threads(self.pid)

    def get_open_files(self):
        """Return files opened by process by parsing lsof output."""
        lsof = _psposix.LsofParser(self.pid, self._process_name)
        return lsof.get_process_open_files()

    def get_connections(self):
        """Return etwork connections opened by a process as a list of
        namedtuples by parsing lsof output.
        """
        lsof = _psposix.LsofParser(self.pid, self._process_name)
        return lsof.get_process_connections()


PlatformProcess = BSDProcess

