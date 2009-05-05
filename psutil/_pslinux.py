#!/usr/bin/env python
#
# $Id$
#

import os
import signal
import errno
import pwd
import grp

# import psutil exceptions we can override with our own
from error import *
from common import CPUTimes

def _get_uptime():
    """Return system boot time (epoch in seconds)"""
    f = open('/proc/stat', 'r')
    for line in f:
        if line.startswith('btime'):
            f.close()
            return float(line.strip().split()[1])

def _get_num_cpus():
    """Return the number of CPUs on the system"""
    num = 0
    f = open('/proc/cpuinfo', 'r')
    for line in f:
        if line.startswith('processor'):
            num += 1
    f.close()
    return num

def _get_total_phymem():
    """Return the total amount of physical memory, in bytes"""
    f = open('/proc/meminfo', 'r')
    for line in f:
        if line.startswith('MemTotal:'):
            f.close()
            return int(line.split()[1]) * 1024


# Number of clock ticks per second
_CLOCK_TICKS = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
_UPTIME = _get_uptime()
NUM_CPUS = _get_num_cpus()
TOTAL_PHYMEM = _get_total_phymem()


def avail_phymem():
    """Return the amount of physical memory available, in bytes."""
    f = open('/proc/meminfo', 'r')
    free = None
    _flag = False
    for line in f:
        if line.startswith('MemFree:'):
            free = int(line.split()[1]) * 1024
            break
    f.close()
    return free

def used_phymem():
    """"Return the amount of physical memory used, in bytes."""
    return (TOTAL_PHYMEM - avail_phymem())

def total_virtmem():
    """"Return the total amount of virtual memory, in bytes."""
    f = open('/proc/meminfo', 'r')
    for line in f:
        if line.startswith('SwapTotal:'):
            f.close()
            return int(line.split()[1]) * 1024

def avail_virtmem():
    "Return the amount of virtual memory currently in use on the system, in bytes."
    f = open('/proc/meminfo', 'r')
    for line in f:
        if line.startswith('SwapFree:'):
            f.close()
            return int(line.split()[1]) * 1024

def used_virtmem():
    """Return the amount of used memory currently in use on the system, in bytes."""
    return total_virtmem() - avail_virtmem()

def cpu_times():
    """Return a CPUTimes instance with the following CPU times:
    user, nice, system, idle, iowait, irq, softirq.
    """
    f = open('/proc/stat', 'r')
    values = f.readline().split()
    f.close()
    values = values[1:8]
    values = tuple([float(x) / _CLOCK_TICKS for x in values])
    return CPUTimes(user=values[0], nice=values[1], system=values[2],
                    idle=values[3], iowait=values[4], irq=values[5],
                    softirq=values[6])


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
                    raise NoSuchProcess(pid)
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
                raise AccessDenied
            raise
    return wrapper


class Impl(object):

    @prevent_zombie
    @wrap_privileges
    def get_process_info(self, pid):
        """Returns a process info class."""
        if pid == 0:
            # special case for 0 (kernel process) PID
            return (pid, 0, 'sched', '', [], 0, 0)

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

        return (pid, self._get_ppid(pid), name, path, cmdline,
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
                raise NoSuchProcess(pid)
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
        # special case for 0 (kernel process) PID
        if pid == 0:
            return (0.0, 0.0)
        f = open("/proc/%s/stat" %pid)
        st = f.read().strip()
        f.close()
        # ignore the first two values ("pid (exe)")
        st = st[st.find(')') + 2:]
        values = st.split(' ')
        utime = float(values[11]) / _CLOCK_TICKS
        stime = float(values[12]) / _CLOCK_TICKS
        return (utime, stime)

    @prevent_zombie
    @wrap_privileges
    def get_process_create_time(self, pid):
        # special case for 0 (kernel processes) PID; return system uptime
        if pid == 0:
            return _UPTIME
        f = open("/proc/%s/stat" %pid)
        st = f.read().strip()
        f.close()
        # ignore the first two values ("pid (exe)")
        st = st[st.find(')') + 2:]
        values = st.split(' ')
        # According to documentation, starttime is in field 21 and the
        # unit is jiffies (clock ticks).
        # We first divide it for clock ticks and then add uptime returning
        # seconds since the epoch, in UTC.
        starttime = (float(values[19]) / _CLOCK_TICKS) + _UPTIME
        return starttime

    @prevent_zombie
    @wrap_privileges
    def get_memory_info(self, pid):
        # special case for 0 (kernel processes) PID
        if pid == 0:
            return (0, 0)
        f = open("/proc/%s/status" % pid)
        virtual_size = 0
        resident_size = 0
        _flag = False
        for line in f:
            if (not _flag) and line.startswith("VmSize:"):
                virtual_size = int(line.split()[1])
                _flag = True
            elif line.startswith("VmRSS"):
                resident_size = int(line.split()[1])
                break
        f.close()
        return (resident_size * 1024, virtual_size * 1024)

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

