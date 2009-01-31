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

        # determine executable
        try:
            _exe = os.readlink("/proc/%s/exe" %pid)
        except OSError:
            f = open("/proc/%s/stat" %pid)
            try:
                _exe = f.read().split(' ')[1].replace('(', '').replace(')', '')
            finally:
                f.close()

        # determine name and path
        if os.path.isabs(_exe):
            path, name = os.path.split(_exe)
        else:
            path = '<unknown>'
            name = _exe

        # determine cmdline
        f = open("/proc/%s/cmdline" %pid)
        try:
            # return the args as a list
            cmdline = [x for x in f.read().split('\x00') if x]
        finally:
            f.close()

        return psutil.ProcessInfo(pid, name, path, cmdline,
                                  self.get_process_uid(pid),
                                  self.get_process_gid(pid))

    def kill_process(self, pid, sig=signal.SIGKILL):
        """Terminates the process with the given PID."""
        if sig is None:
            sig = signal.SIGKILL
        os.kill(pid, sig)

    def get_pid_list(self):
        """Returns a list of PIDs currently running on the system."""
        return [int(x) for x in os.listdir('/proc') if x.isdigit()]

    def get_process_uid(self, pid):
        # XXX - something faster than readlines() could be used
        f = open("/proc/%s/status" %pid)
        for line in f.readlines():
            if line.startswith('Uid:'):
                # Uid line provides 4 values which stand for real,
                # effective, saved set, and file system UIDs.
                # We want to provide real UID only.
                return int(line.split()[1])

    def get_process_gid(self, pid):
        # XXX - something faster than readlines() could be used
        f = open("/proc/%s/status" %pid)
        for line in f.readlines():
            if line.startswith('Gid:'):
                # Uid line provides 4 values which stand for real,
                # effective, saved set, and file system GIDs.
                # We want to provide real GID only.
                return int(line.split()[1])
