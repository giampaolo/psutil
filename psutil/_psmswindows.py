#!/usr/bin/env python
#
# $Id$
#

import errno
import os
import _psutil_mswindows

# import psutil exceptions we can override with our own
from error import *

try:
    import wmi
except ImportError:
    wmi = None


# --- module level constants (gets pushed up to psutil module)

NoSuchProcess = _psutil_mswindows.NoSuchProcess
NUM_CPUS = _psutil_mswindows.get_num_cpus()
_UPTIME = _psutil_mswindows.get_system_uptime()
TOTAL_PHYMEM = _psutil_mswindows.get_total_phymem()


# --- public functions

def avail_phymem():
    "Return the amount of physical memory available on the system, in bytes."
    return _psutil_mswindows.get_avail_phymem()

def used_phymem():
    "Return the amount of physical memory currently in use on the system, in bytes."
    return TOTAL_PHYMEM - _psutil_mswindows.get_avail_phymem()

def total_virtmem():
    "Return the amount of total virtual memory available on the system, in bytes."
    return _psutil_mswindows.get_total_virtmem()

def avail_virtmem():
    "Return the amount of virtual memory currently in use on the system, in bytes."
    return _psutil_mswindows.get_avail_virtmem()

def used_virtmem():
    """Return the amount of used memory currently in use on the system, in bytes."""
    return _psutil_mswindows.get_total_virtmem() - _psutil_mswindows.get_avail_virtmem()

def get_system_cpu_times():
    """Return a dict representing the following CPU times: user, system, idle."""
    times = _psutil_mswindows.get_system_cpu_times()
    return dict(user=times[0], system=times[1], idle=times[2])


# --- decorator

def wrap_privileges(callable):
    """Call callable into a try/except clause so that if a
    WindowsError 5 AccessDenied exception is raised we translate it
    into psutil.AccessDenied
    """
    def wrapper(*args, **kwargs):
        try:
            return callable(*args, **kwargs)
        except OSError, err:
            if err.errno == errno.EACCES:
                raise AccessDenied
            raise
    return wrapper


class Impl(object):

    @wrap_privileges
    def get_process_info(self, pid):
        """Returns a tuple that can be passed to the psutil.ProcessInfo class
        constructor.
        """
        infoTuple = _psutil_mswindows.get_process_info(pid)
        return infoTuple

    @wrap_privileges
    def get_memory_info(self, pid):
        """Returns a tuple or RSS/VMS memory usage in bytes."""
        # special case for 0 (kernel processes) PID
        if pid == 0:
            return (0, 0)
        return _psutil_mswindows.get_memory_info(pid)

    @wrap_privileges
    def kill_process(self, pid, sig=None):
        """Terminates the process with the given PID."""
        try:
            return _psutil_mswindows.kill_process(pid)
        except OSError, err:
            # work around issue #24
            if (pid == 0) and (err.errno == errno.EINVAL):
                raise AccessDenied
            raise

    def get_process_username(self, pid):
        """Return the name of the user that owns the process"""
        if wmi is None:
            raise NotImplementedError("This functionnality requires pywin32 " \
                                      "extension to be installed")
        else:
            if pid in (0, 4):
                return 'NT AUTHORITY\\SYSTEM'
            w = wmi.WMI().Win32_Process(ProcessId=pid)
            domain, _, username = w[0].GetOwner()
            return "%s\\%s" %(domain, username)

    def get_pid_list(self):
        """Returns a list of PIDs currently running on the system."""
        return _psutil_mswindows.get_pid_list()

    def pid_exists(self, pid):
        return _psutil_mswindows.pid_exists(pid)

    @wrap_privileges
    def get_process_create_time(self, pid):
        # special case for kernel process PIDs; return system uptime
        if pid in (0, 4):
            return _UPTIME
        return _psutil_mswindows.get_process_create_time(pid)

    @wrap_privileges
    def get_cpu_times(self, pid):
        return _psutil_mswindows.get_process_cpu_times(pid)

    def suspend_process(self, pid):
        return _psutil_mswindows.suspend_process(pid)

    def resume_process(self, pid):
        return _psutil_mswindows.resume_process(pid)

    @wrap_privileges
    def get_process_cwd(self, pid):
        if pid in (0, 4):
            return ''
        # return a normalized pathname since the native C function appends
        # "\\" at the and of the path
        path = _psutil_mswindows.get_process_cwd(pid)
        return os.path.normpath(path)
