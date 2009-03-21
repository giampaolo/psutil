#!/usr/bin/env python
#
# $Id$
#

import os
import signal
import errno
import pwd
import grp

import _psutil_bsd

# import psutil exceptions we can override with our own
from error import *

# module level constants (gets pushed up to psutil module)
NoSuchProcess = _psutil_bsd.NoSuchProcess
NUM_CPUS = _psutil_bsd.get_num_cpus()
# XXX - real implementation needed
TOTAL_PHYMEM = 0
TOTAL_VIRTMEM = 0


def wrap_privileges(callable):
    """Call callable into a try/except clause so that if an
    OSError EPERM exception is raised we translate it into
    psutil.AccessDenied.
    """
    def wrapper(*args, **kwargs):
        try:
            return callable(*args, **kwargs)
        except OSError, err:
            if err.errno == errno.EPERM:
                raise AccessDenied
            raise
    return wrapper

def prevent_zombie(method):
    """Call method(self, pid) into a try/except clause so that if an
    OSError "No such process" exception is raised we assume the process
    has died and raise psutil.NoSuchProcess instead.
    """
    def wrapper(self, pid, *args, **kwargs):
        try:
            return method(self, pid, *args, **kwargs)
        except OSError, err:
            if err.errno == errno.ESRCH:
                raise NoSuchProcess(pid)
            raise
    return wrapper


class Impl(object):

    @wrap_privileges
    def get_process_info(self, pid):
        """Returns a tuple that can be passed to the psutil.ProcessInfo class
        constructor.
        """
        infoTuple = _psutil_bsd.get_process_info(pid)
        return infoTuple

    @wrap_privileges
    def kill_process(self, pid, sig=signal.SIGKILL):
        """Terminates the process with the given PID."""
        if sig is None:
            sig = signal.SIGKILL
        try:
            os.kill(pid, sig)
        except OSError, err:
            if err.errno == errno.ESRCH:
                raise NoSuchProcess(pid)
            raise

    @wrap_privileges
    def get_cpu_times(self, pid):
        """return a tuple containing process user/kernel time."""
        return _psutil_bsd.get_cpu_times(pid)

    @wrap_privileges
    @prevent_zombie
    def get_memory_info(self, pid):
        """Return a tuple with the process' RSS and VMS size."""
        return _psutil_bsd.get_memory_info(pid)

    def get_process_create_time(self, pid):
        return _psutil_bsd.get_process_create_time(pid)

    def get_pid_list(self):
        """Returns a list of PIDs currently running on the system."""
        return _psutil_bsd.get_pid_list()

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


