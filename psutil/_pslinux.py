#!/usr/bin/env python
# _pslinux.py

import os
import signal
import socket
import errno

import psutil


def prevent_zombie(method):
    """Call method(self, pid) into a try/except clause so that if an
    IOError "No such file" exception is raised we assume the process
    has died and raise psutil.NoSuchProcess instead.
    """
    def wrapper(self, pid, *args, **kwargs):
        try:
            return method(self, pid, *args, **kwargs)
        except IOError, err:
            if err.errno == errno.ENOENT:  # no such file or directory
                if not pid in self.get_pid_list():
                    raise psutil.NoSuchProcess(pid)
            raise
    return wrapper


class Impl(object):

    @prevent_zombie
    def get_process_info(self, pid):
        """Returns a process info class."""
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

        return psutil.ProcessInfo(pid, self.get_ppid(pid), name, path, cmdline,
                                  self.get_process_uid(pid),
                                  self.get_process_gid(pid))

    def kill_process(self, pid, sig=signal.SIGKILL):
        """Terminates the process with the given PID."""
        if sig is None:
            sig = signal.SIGKILL
        try:
            os.kill(pid, sig)
        except OSError, err:
            if err.errno == errno.ESRCH:
                raise psutil.NoSuchProcess(pid)
            raise

    def get_pid_list(self):
        """Returns a list of PIDs currently running on the system."""
        return [int(x) for x in os.listdir('/proc') if x.isdigit()]

    def pid_exists(self, pid):
        return os.path.exists('/proc/%s' %pid)

    def get_ppid(self, pid):
        f = open("/proc/%s/status" % pid)
        for line in f:
            if line.startswith("PPid:"):
                # PPid: nnnn
                return int(line.split()[1])

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

