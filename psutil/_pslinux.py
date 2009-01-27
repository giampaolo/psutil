#!/usr/bin/env python
# _pslinux.py

import os
import signal


class Impl(object):

    def process_exists(self, pid):
        """Checks whether or not a process exists with the given PID."""
        return pid in self.get_pid_list()

    def get_process_info(self, pid):
        """Returns a process info class."""
        # XXX - figure out why it can't be imported globally (see r54)
        import psutil
        try:
            exe = os.readlink("/proc/%s/exe" %pid)
        except OSError:
            exe = '<unknown>'
        path, name = os.path.split(exe)
        f = open("/proc/%s/cmdline" %pid)
        try:
            # return the args as a list, dropping the last line (always empty)
            cmdline = f.read().split('\x00')[:-1]
        finally:
            f.close()
        return psutil.ProcessInfo(pid, name, path, cmdline)

    def kill_process(self, pid, sig=signal.SIGKILL):
        """Terminates the process with the given PID."""
        if sig is None:
            sig = signal.SIGKILL
        os.kill(pid, sig)

    def get_pid_list(self):
        """Returns a list of PIDs currently running on the system."""
        return [int(x) for x in os.listdir('/proc') if x.isdigit()]
