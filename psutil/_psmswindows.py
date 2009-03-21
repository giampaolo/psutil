#!/usr/bin/env python
#
# $Id$
#

import errno
import _psutil_mswindows

# import psutil exceptions we can override with our own
from error import *

# module level constants (gets pushed up to psutil module)
NoSuchProcess = _psutil_mswindows.NoSuchProcess
NUM_CPUS = _psutil_mswindows.get_num_cpus()
_UPTIME = _psutil_mswindows.get_system_uptime()
TOTAL_PHYMEM = _psutil_mswindows.get_total_phymem()
TOTAL_VIRTMEM = _psutil_mswindows.get_total_virtmem()

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

