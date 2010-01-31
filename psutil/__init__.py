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
    "ProcessInfo",
    "Process",
    "test",
    "CPUTimes",
    "pid_exists",
    "get_pid_list",
    "process_iter",
    "get_process_list",
    "TOTAL_PHYMEM",
    "avail_phymem",
    "used_phymem",
    "total_virtmem",
    "avail_virtmem",
    "used_virtmem",
    "cpu_times",
    "cpu_percent",
    ]

__version__ = '0.1.3'


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


class CPUTimes:
    """This class contains information about CPU times.
    It is not used directly but it's returned as an instance by
    psutil.cpu_times() function.

    Every CPU time is accessible in form of an attribute and represents
    the time CPU has spent in the given mode.

    The attributes availability varies depending on the platform.
    Here follows a list of all available attributes:

     - user
     - system
     - idle
     - nice (UNIX)
     - iowait (Linux)
     - irq (Linux, FreeBSD)
     - softirq (Linux)
    """

    def __init__(self, **kwargs):
        self.__attrs = []
        for name in kwargs:
            setattr(self, name, kwargs[name])
            self.__attrs.append(name)

    def __str__(self):
        string = []
        for attr in self.__attrs:
            value = getattr(self, attr)
            string.append("%s=%s" %(attr, value))
        return '; '.join(string)

    def __iter__(self):
        for attr in self.__attrs:
            yield getattr(self, attr)


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
        self.username = None
        self.groupname = None


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
        """Test for equality with another Process object based on PID
        and creation time."""
        h1 = (self.pid, self.create_time)
        h2 = (other.pid, other.create_time)
        return h1 == h2

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
    def username(self):
        """The name of the user that owns the process."""
    	if self._procinfo.username is not None:
    		return self._procinfo.username
        if pwd is not None:
            self._procinfo.username = pwd.getpwuid(self.uid).pw_name
        else:
            self._procinfo.username =  _platform_impl.get_process_username(self.pid)
    	return self._procinfo.username

    @property
    def groupname(self):
        """The real groupname of the current process.
        On Windows machines, the most powerful among the well known groups
        the user owning the process belongs to is returned
        """
    	if self._procinfo.groupname is not None:
    		return self._procinfo.groupname
        if grp is not None:
            self._procinfo.groupname = grp.getgrgid(self.gid).gr_name
        else:
            # Windows
            self._procinfo.groupname = _platform_impl.get_process_groupname(self.username)

    	return self._procinfo.groupname

    @property
    def environ(self):
        """The process environment variables as a dictionary."""
        return _platform_impl.get_process_environ(self.pid)

    @property
    def create_time(self):
        """The process creation time as a floating point number
        expressed in seconds since the epoch, in UTC.
        """
        if self._procinfo.create is None:
            self._procinfo.create = _platform_impl.get_process_create_time(self.pid)
        return self._procinfo.create

    if sys.platform.lower().startswith("linux") \
    or sys.platform.lower().startswith("win32"):
        def getcwd(self):
            """Return a string representing the process current working
            directory.
            """
            return _platform_impl.get_process_cwd(self.pid)

    def suspend(self):
        """Suspend process execution."""
        # windows
        if hasattr(_platform_impl, "suspend_process"):
            _platform_impl.suspend_process(self.pid)
        # posix
        try:
            os.kill(self.pid, signal.SIGSTOP)
        except OSError, err:
            if err.errno == errno.ESRCH:
                raise NoSuchProcess(self.pid)
            raise

    def resume(self):
        """Resume process execution."""
        if hasattr(_platform_impl, "resume_process"):        
            _platform_impl.resume_process(self.pid)
        # posix
        try:
            os.kill(self.pid, signal.SIGCONT)
        except OSError, err:
            if err.errno == errno.ESRCH:
                raise NoSuchProcess(self.pid)
            raise

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

        return (percent * 100.0)

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
            newproc = Process(self.pid)
            return self == newproc
        except NoSuchProcess:
            return False

    def kill(self, sig=None):
        """Kill the current process by using signal sig (defaults to SIGKILL).
        """
        # safety measure in case the current process has been killed in
        # meantime and the kernel reused its PID
        if not self.is_running():
            raise NoSuchProcess
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

def cpu_times():
    """Return system CPU times as a CPUTimes object."""
    values = get_system_cpu_times()
    return CPUTimes(**values)

_last_idle_time = cpu_times().idle
_last_time = time.time()

def cpu_percent():
    """Return the current system-wide CPU utilization as a percentage. For
    highest accuracy, it is recommended that this be called at least 1/10th
    of a second after importing the module or calling cpu_percent() in a
    previous call, to allow for a larger time delta from which to calculate
    the percentage value.
    """
    global _last_idle_time
    global _last_time

    idle_time = cpu_times().idle
    curr_time = time.time()

    time_delta = curr_time - _last_time
    idle_delta = idle_time - _last_idle_time

    # reset values for next run
    _last_idle_time = idle_time
    _last_time = curr_time

    # Removed; see Issue #67: http://code.google.com/p/psutil/issues/detail?id=67
    # invalid data, will not be accurate so return 0.0 to avoid an overflow
    #if time_delta < idle_delta:
    #    return 0.0

    try :
        idle_percent = (idle_delta / time_delta) * 100.0
        util_percent = (100 * NUM_CPUS) - idle_percent
    except ZeroDivisionError:
        return 0.0

    return util_percent / NUM_CPUS


def test():
    """List info of all currently running processes emulating a
    ps -aux output.
    """
    import datetime
    today_day = datetime.date.today()

    def get_process_info(pid):
        proc = Process(pid)
        user = proc.username
        if os.name == 'nt' and '\\' in user:
            user = user.split('\\')[1]
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
        return "%-9s %-5s %-4s %4s %7s %7s %5s %8s %s" \
               %(user, pid, cpu, mem, vsz, rss, start, cputime, cmd)

    print "%-9s %-5s %-4s %4s %7s %7s %5s %7s  %s" \
       %("USER", "PID", "%CPU", "%MEM", "VSZ", "RSS", "START", "TIME", "COMMAND")
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
