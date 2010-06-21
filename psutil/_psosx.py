#!/usr/bin/env python
#
# $Id$
#

import os
import signal
import errno

import _psutil_osx

# import psutil exceptions we can override with our own
from error import *

# module level constants (gets pushed up to psutil module)
NUM_CPUS = _psutil_osx.get_num_cpus()
TOTAL_PHYMEM = _psutil_osx.get_total_phymem()

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

def cached_mem():
    """Return the amount of cached memory on the system, in bytes."""
    raise NotImplementedError("This feature not yet implemented on OS X.")

def cached_swap():
    """Return the amount of cached swap on the system, in bytes."""
    raise NotImplementedError("This feature not yet implemented on OS X.")

def get_system_cpu_times():
    """Return a dict representing the following CPU times:
    user, nice, system, idle."""
    values = _psutil_osx.get_system_cpu_times()
    return dict(user=values[0], nice=values[1], system=values[2], idle=values[3])

def wrap_privileges(callable):
    """Call callable into a try/except clause so that if an
    OSError EPERM exception is raised we translate it into
    psutil.AccessDenied.
    """
    def wrapper(*args, **kwargs):
        try:
            return callable(*args, **kwargs)
        except OSError, err:
            if err.errno == errno.ESRCH:
                raise NoSuchProcess(pid, "process no longer exists")
            if err.errno == errno.EPERM:
                raise AccessDenied(pid)
            raise
    return wrapper


class Impl(object):

    @wrap_privileges
    def get_process_info(self, pid):
        """Returns a tuple that can be passed to the psutil.ProcessInfo class
        constructor.
        """
        infoTuple = _psutil_osx.get_process_info(pid)
        return infoTuple

    @wrap_privileges
    def get_memory_info(self, pid):
        """Return a tuple with the process' RSS and VMS size."""
        return _psutil_osx.get_memory_info(pid)

    def get_cpu_times(self, pid):
        return _psutil_osx.get_process_cpu_times(pid)

    def get_process_create_time(self, pid):
        """Return the start time of the process as a number of seconds since
        the epoch."""
        return _psutil_osx.get_process_create_time(pid)


    def get_pid_list(self):
        """Returns a list of PIDs currently running on the system."""
        return _psutil_osx.get_pid_list()

    def pid_exists(self, pid):
        """Check For the existence of a unix pid."""
        if pid < 0:
            return False

        try:
            os.kill(pid, 0)
        except OSError, e:
            return e.errno == errno.EPERM
        else:
            return True

