#!/usr/bin/env python
#
# $Id$
#

import os
import signal
import errno
import pwd
import grp

import psutil

# Number of clock ticks per second
CLOCK_TICKS = os.sysconf(os.sysconf_names["SC_CLK_TCK"])


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
                if not self.pid_exists(pid):
                    raise psutil.NoSuchProcess(pid)
            raise
    return wrapper


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
                raise psutil.AccessDenied
            raise
    return wrapper


class Impl(object):

    @prevent_zombie
    @wrap_privileges
    def get_process_info(self, pid):
        """Returns a process info class."""
        if pid == 0:
            # special case for 0 (kernel process) PID
            return psutil.ProcessInfo(pid, 0, 'sched', '', [], 0, 0)

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
            path = ''
            name = _exe

        # determine cmdline
        f = open("/proc/%s/cmdline" %pid)
        try:
            # return the args as a list
            cmdline = [x for x in f.read().split('\x00') if x]
        finally:
            f.close()

        return psutil.ProcessInfo(pid, self._get_ppid(pid), name, path, cmdline,
                                  self._get_process_uid(pid),
                                  self._get_process_gid(pid))

    @wrap_privileges
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
        pids = [int(x) for x in os.listdir('/proc') if x.isdigit()]
        # special case for 0 (kernel process) PID
        pids.insert(0, 0)
        return pids

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

    @prevent_zombie
    @wrap_privileges
    def get_cpu_times(self, pid):
        if pid == 0:
            # special case for 0 (kernel process) PID
            return (0.0, 0.0)
        f = open("/proc/%s/stat" %pid)
        st = f.read().strip()
        f.close()
        # ignore the first two values ("pid (exe)")
        st = st[st.find(')') + 2:]
        values = st.split(' ')
        utime = float(values[11]) / CLOCK_TICKS
        stime = float(values[12]) / CLOCK_TICKS
        return (utime, stime)

    def _get_ppid(self, pid):
        f = open("/proc/%s/status" % pid)
        for line in f:
            if line.startswith("PPid:"):
                # PPid: nnnn
                f.close()
                return int(line.split()[1])

    def _get_process_uid(self, pid):
        # XXX - something faster than readlines() could be used
        f = open("/proc/%s/status" %pid)
        for line in f:
            if line.startswith('Uid:'):
                # Uid line provides 4 values which stand for real,
                # effective, saved set, and file system UIDs.
                # We want to provide real UID only.
                f.close()
                return int(line.split()[1])

    def _get_process_gid(self, pid):
        # XXX - something faster than readlines() could be used
        f = open("/proc/%s/status" %pid)
        for line in f:
            if line.startswith('Gid:'):
                # Uid line provides 4 values which stand for real,
                # effective, saved set, and file system GIDs.
                # We want to provide real GID only.
                f.close()
                return int(line.split()[1])

