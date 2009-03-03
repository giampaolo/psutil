#!/usr/bin/env python
# _psmswindows.py

import errno

import _psutil_mswindows


NoSuchProcess = _psutil_mswindows.NoSuchProcess


def wrap_privileges(callable):
    """Call callable into a try/except clause so that if a
    WindowsError 5 AccessDenied exception is raised we translate it
    into psutil.AccessDenied
    """
    def wrapper(*args, **kwargs):
        # XXX - figure out why it can't be imported globally
        import psutil
        try:
            return callable(*args, **kwargs)
        except OSError, err:
            if err.errno == errno.EACCES:
                raise psutil.AccessDenied
            raise
    return wrapper


class Impl(object):

    @wrap_privileges
    def get_process_info(self, pid):
        """Returns a tuple that can be passed to the psutil.ProcessInfo class
        constructor.
        """
        # XXX - figure out why it can't be imported globally
        import psutil
        infoTuple = _psutil_mswindows.get_process_info(pid)
        return psutil.ProcessInfo(*infoTuple)

    @wrap_privileges
    def kill_process(self, pid, sig=None):
        """Terminates the process with the given PID."""
        # XXX - figure out why it can't be imported globally
        import psutil
        try:
            return _psutil_mswindows.kill_process(pid)
        except OSError, err:
            # work around issue #24
            if (pid == 0) and (err.errno == errno.EINVAL):
                raise psutil.AccessDenied
            raise

    @wrap_privileges
    def get_username(self, uid):
        return ""

    @wrap_privileges
    def get_group(self, gid):
        return ""

    def get_pid_list(self):
        """Returns a list of PIDs currently running on the system."""
        return _psutil_mswindows.get_pid_list()

    def pid_exists(self, pid):
        return _psutil_mswindows.pid_exists(pid)

