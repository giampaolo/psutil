#!/usr/bin/env python
#
# $Id$
#

"""psutil is a module providing convenience functions for managing
processes in a portable way by using Python.
"""

__all__ = [
    "NoSuchProcess",
    "AccessDenied",
    "NUM_CPUS",
    "TOTAL_PHYMEM",
    "TOTAL_VIRTMEM",
    "ProcessInfo",
    "Process",
    "pid_exists",
    "get_pid_list",
    "process_iter",
    "get_process_list",]

import sys
import os
import time
try:
    import pwd, grp
except ImportError:
    pwd = grp = None

# exceptions are imported here, but may be overriden by platform
# module implementation later
from error import *

# import the appropriate module for our platform only
if sys.platform.lower().startswith("linux"):
    from _pslinux import *

elif sys.platform.lower().startswith("win32"):
    from _psmswindows import *

elif sys.platform.lower().startswith("darwin"):
    from _psosx import *

elif sys.platform.lower().startswith("freebsd"):
    from _psbsd import *
else:
    raise ImportError('no os specific module found')

# platform-specific modules define an Impl implementation class
_platform_impl = Impl()


class ProcessInfo(object):
    """Class that allows the process information to be passed between
    external code and psutil.  Used directly by the Process class.
    """

    def __init__(self, pid, ppid=None, name=None, path=None, cmdline=None,
                       uid=None, gid=None):
        self.pid = pid
        self.ppid = ppid
        self.name = name
        self.path = path
        self.cmdline = cmdline
        # if we have the cmdline but not the path, figure it out from argv[0]
        if cmdline and not path:
            self.path = os.path.dirname(cmdline[0])
        self.uid = uid
        self.gid = gid
        self.create = None


class Process(object):
    """Represents an OS process."""

    def __init__(self, pid):
        """Create a new Process object, raises NoSuchProcess if the PID
        does not exist, and ValueError if the parameter is not an
        integer PID."""
        if not isinstance(pid, int):
            raise ValueError("An integer is required")
        if not pid_exists(pid):
            raise NoSuchProcess("No process found with PID %s" % pid)
        self._procinfo = ProcessInfo(pid)
        self.is_proxy = True
        # try to init CPU times, if it raises AccessDenied then suppress
        # it so it won't interrupt the constructor. First call to
        # get_cpu_percent() will trigger the AccessDenied exception
        # instead.
        try:
            self._last_sys_time = time.time()
            self._last_user_time, self._last_kern_time = self.get_cpu_times()
        except AccessDenied:
            self._last_user_time, self._last_kern_time = None, None

    def __str__(self):
        return "psutil.Process <PID:%s; PPID:%s; NAME:'%s'; PATH:'%s'; " \
               "CMDLINE:%s; UID:%s; GID:%s;>" \
               %(self.pid, self.ppid, self.name, self.path, self.cmdline, \
                 self.uid, self.gid)

    def __eq__(self, other):
        """Test for equality with another Process object based on PID,
        name etc."""
        if self.pid != other.pid:
            return False

        # make sure both objects are initialized
        self.deproxy()
        other.deproxy()
        # check all non-callable and non-private attributes for equality
        # if the attribute is missing from other then return False
        for attr in dir(self):
            attrobj = getattr(self, attr)
            # skip private attributes
            if attr.startswith("_"):
                continue

            # skip methods and Process objects
            if callable(attrobj) or isinstance(attrobj, Process):
                continue

            # attribute doesn't exist or isn't equal, so return False
            if not hasattr(other, attr):
                return False
            if getattr(self, attr) != getattr(other, attr):
                return False

        return True

    def deproxy(self):
        """Used internally by Process properties. The first call to
        deproxy() initializes the ProcessInfo object in self._procinfo
        with process data read from platform-specific module's
        get_process_info() method.

        This method becomes a NO-OP after the first property is accessed.
        Property data is filled in from the ProcessInfo object created,
        and further calls to deproxy() simply return immediately without
        calling get_process_info().
        """
        if self.is_proxy:
            # get_process_info returns a tuple we use as the arguments
            # to the ProcessInfo constructor
            self._procinfo = ProcessInfo(*_platform_impl.get_process_info(self._procinfo.pid))
            self.is_proxy = False

    @property
    def pid(self):
        """The process pid."""
        return self._procinfo.pid

    @property
    def ppid(self):
        """The process parent pid."""
        self.deproxy()
        return self._procinfo.ppid

    @property
    def parent(self):
        """Return the parent process as a Process object. If no ppid is
        known then return None."""
        if self.ppid is not None:
            return Process(self.ppid)
        return None

    @property
    def name(self):
        """The process name."""
        self.deproxy()
        return self._procinfo.name

    @property
    def path(self):
        """The process path."""
        self.deproxy()
        return self._procinfo.path

    @property
    def cmdline(self):
        """The command line process has been called with."""
        self.deproxy()
        return self._procinfo.cmdline

    @property
    def uid(self):
        """The real user id of the current process."""
        self.deproxy()
        return self._procinfo.uid

    @property
    def gid(self):
        """The real group id of the current process."""
        self.deproxy()
        return self._procinfo.gid

    @property
    def create_time(self):
        """The process creation time as a floating point number
        expressed in seconds since the epoch, in UTC.
        """
        if self._procinfo.create is None:
            self._procinfo.create = _platform_impl.get_process_create_time(self.pid)
        return self._procinfo.create

    def get_cpu_percent(self):
        """Compare process times to system time elapsed since last call
        and calculate CPU utilization as a percentage. It is recommended
        for accuracy that this function be called with at least 1 second
        between calls. The initial delta is calculated from the
        instantiation of the Process object.
        """
        now = time.time()
        # will raise AccessDenied on OS X if not root or in procmod group
        user_t, kern_t = _platform_impl.get_cpu_times(self.pid)

        total_proc_time = float((user_t - self._last_user_time) + \
                                (kern_t - self._last_kern_time))
        try:
            percent = total_proc_time / float((now - self._last_sys_time))
        except ZeroDivisionError:
            percent = 0.000

        # reset the values
        self._last_sys_time = time.time()
        self._last_user_time, self._last_kern_time = self.get_cpu_times()

        return (percent * 100.0) / NUM_CPUS

    def get_cpu_times(self):
        """Return a tuple whose values are process CPU user and system
        time.  These are the same first two values that os.times()
        returns for the current process.
        """
        return _platform_impl.get_cpu_times(self.pid)

    def get_memory_info(self):
        """Return a tuple representing RSS (Resident Set Size) and VMS
        (Virtual Memory Size) in bytes.

        On UNIX RSS and VMS are the same values shown by ps.

        On Windows RSS and VMS refer to "Mem Usage" and "VM Size" columns
        of taskmgr.exe.
        """
        return _platform_impl.get_memory_info(self.pid)

    def get_memory_percent(self):
        """Compare physical system memory to process resident memory and
        calculate process memory utilization as a percentage.
        """
        rss = _platform_impl.get_memory_info(self.pid)[0]
        try:
            return (rss / float(TOTAL_PHYMEM)) * 100
        except ZeroDivisionError:
            return 0.0

    def is_running(self):
        """Return whether the current process is running in the current process
        list."""
        try:
            new_proc = Process(self.pid)
            # calls get_process_info() which may in turn trigger NSP exception
            str(new_proc)
        except NoSuchProcess:
            return False
        return self == new_proc

    def kill(self, sig=None):
        """Kill the current process by using signal sig (defaults to SIGKILL).
        """
        _platform_impl.kill_process(self.pid, sig)


def pid_exists(pid):
    """Check whether the given PID exists in the current process list."""
    return _platform_impl.pid_exists(pid)

def get_pid_list():
    """Return a list of current running PIDs."""
    return _platform_impl.get_pid_list()

def process_iter():
    """Return an iterator yielding a Process class instances for all
    running processes on the local machine.
    """
    pids = _platform_impl.get_pid_list()
    # for each PID, create a proxyied Process object
    # it will lazy init it's name and path later if required
    for pid in pids:
        try:
            yield Process(pid)
        except (NoSuchProcess, AccessDenied):
            continue

def get_process_list():
    """Return a list of Process class instances for all running
    processes on the local machine.
    """
    return list(process_iter())


def test():
    """List info of all currently running processes emulating a
    ps -aux output.
    """
    import datetime
    today_day = datetime.date.today()

    def get_process_info(pid):
        proc = Process(pid)
        uid = proc.uid
        pid = proc.pid
        cpu = round(proc.get_cpu_percent(), 1)
        mem = round(proc.get_memory_percent(), 1)
        rss, vsz = [x / 1024 for x in proc.get_memory_info()]

        # If process has been created today print H:M, else MonthDay
        start = datetime.datetime.fromtimestamp(proc.create_time)
        if start.date() == today_day:
            start = start.strftime("%H:%M")
        else:
            start = start.strftime("%b%d")

        cputime = time.strftime("%M:%S", time.localtime(sum(proc.get_cpu_times())))
        cmd = ' '.join(proc.cmdline)
        # where cmdline is not available UNIX shows process name between
        # [] parentheses
        if not cmd:
            cmd = "[%s]" %proc.name
        return "%-5s %7s %4s %4s %7s %7s %5s %8s %s" \
               %(uid, pid, cpu, mem, vsz, rss, start, cputime, cmd)

    print "%-5s %7s %4s %4s %7s %7s %5s %8s %s" \
       %("UID", "PID", "%CPU", "%MEM", "VSZ", "RSS", "START", "TIME", "COMMAND")
    pids = get_pid_list()
    pids.sort()
    for pid in pids:
        try:
            line = get_process_info(pid)
        except (AccessDenied, NoSuchProcess):
            pass
        else:
            print line

if __name__ == "__main__":
    test()

