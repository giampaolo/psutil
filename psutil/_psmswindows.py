#!/usr/bin/env python
# _psmswindows.py

import psutil
import _psutil_mswindows

NoSuchProcess = _psutil_mswindows.NoSuchProcess

class Impl(object):

    def get_process_info(self, pid):
        """Returns a tuple that can be passed to the psutil.ProcessInfo class
        constructor.
        """
        infoTuple = _psutil_mswindows.get_process_info(pid)
        return psutil.ProcessInfo(*infoTuple)

    def kill_process(self, pid, sig=None):
        """Terminates the process with the given PID."""
        return _psutil_mswindows.kill_process(pid)

    def get_pid_list(self):
        """Returns a list of PIDs currently running on the system."""
        return _psutil_mswindows.get_pid_list()

    def pid_exists(self, pid):
        return pid in _psutil_mswindows.get_pid_list()

