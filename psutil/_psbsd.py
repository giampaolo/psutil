#!/usr/bin/env python
#
# $Id$
#

import os
import signal
import errno
import pwd
import grp

try:
    from collections import namedtuple
except ImportError:
    from psutil.compat import namedtuple  # python < 2.6

from psutil import _psutil_bsd
from psutil import _psposix
from psutil.error import *

NUM_CPUS = _psutil_bsd.get_num_cpus()
TOTAL_PHYMEM = _psutil_bsd.get_total_phymem()

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

def cached_mem():
    """Return the amount of cached memory on the system, in bytes."""
    return _psutil_bsd.get_cached_mem()

def cached_swap():
    """Return 0 as there's no such thing as cached swap on BSD."""
    return 0

def get_system_cpu_times():
    """Return a dict representing the following CPU times:
    user, nice, system, idle, interrupt."""
    values = _psutil_bsd.get_system_cpu_times()
    return dict(user=values[0], nice=values[1], system=values[2],
        idle=values[3], irq=values[4])


def wrap_exceptions(method):
    """Call method(self, pid) into a try/except clause so that if an
    OSError "No such process" exception is raised we assume the process
    has died and raise psutil.NoSuchProcess instead.
    """
    def wrapper(self, pid, *args, **kwargs):
        try:
            return method(self, pid, *args, **kwargs)
        except OSError, err:
            if err.errno == errno.ESRCH:
                raise NoSuchProcess(pid, "process no longer exists")
            if err.errno == errno.EPERM:
                raise AccessDenied(pid)
            raise
    return wrapper


class Impl(object):

    @wrap_exceptions
    def get_process_info(self, pid):
        """Returns a tuple that can be passed to the psutil.ProcessInfo class
        constructor.
        """
        infoTuple = _psutil_bsd.get_process_info(pid)
        return infoTuple

    @wrap_exceptions
    def get_cpu_times(self, pid):
        """return a tuple containing process user/kernel time."""
        user, system = _psutil_bsd.get_cpu_times(pid)
        cputimes = namedtuple('cputimes', 'user system')
        return cputimes(user, system)

    @wrap_exceptions
    def get_memory_info(self, pid):
        """Return a tuple with the process' RSS and VMS size."""
        rss, vms = _psutil_bsd.get_memory_info(pid)
        meminfo = namedtuple('meminfo', 'rss vms')
        return meminfo(rss, vms)

    @wrap_exceptions
    def get_process_create_time(self, pid):
        return _psutil_bsd.get_process_create_time(pid)

    def get_pid_list(self):
        """Returns a list of PIDs currently running on the system."""
        return _psutil_bsd.get_pid_list()

    def pid_exists(self, pid):
        """Check For the existence of a unix pid."""
        return _psposix.pid_exists(pid)


    def get_open_files(self, pid):
        """Return files opened by process by parsing lsof output."""
        return _psposix.LsofParser(pid).get_process_open_files()

    def get_connections(self, pid):
        """Return etwork connections opened by a process as a list of
        namedtuples."""
        return _psposix.LsofParser(pid).get_process_connections()


