#!/usr/bin/env python
#
# $Id$
#

"""psutil is a module providing convenience functions for managing
processes in a portable way by using Python.
"""

__version__ = "0.2.0"
version_info = tuple([int(num) for num in __version__.split('.')])

__all__ = [
    # exceptions
    "Error", "NoSuchProcess", "AccessDenied",
    # constants
    "NUM_CPUS", "TOTAL_PHYMEM", "version_info", "__version__",
    # classes
    "Process",
    # functions
    "test", "pid_exists", "get_pid_list", "process_iter", "get_process_list",
    "avail_phymem", "used_phymem", "total_virtmem", "avail_virtmem",
    "used_virtmem", "cpu_times", "cpu_percent",
    ]

import sys
import os
import time
import signal
import warnings
import errno
try:
    import pwd
except ImportError:
    pwd = None

from psutil.error import Error, NoSuchProcess, AccessDenied

# import the appropriate module for our platform only
if sys.platform.lower().startswith("linux"):
    from psutil._pslinux import *
    __all__.extend(["cached_phymem", "phymem_buffers"])

elif sys.platform.lower().startswith("win32"):
    from psutil._psmswindows import *

elif sys.platform.lower().startswith("darwin"):
    from psutil._psosx import *

elif sys.platform.lower().startswith("freebsd"):
    from psutil._psbsd import *

else:
    raise NotImplementedError('platform %s is not supported' % sys.platform)


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


class Process(object):
    """Represents an OS process."""

    def __init__(self, pid):
        """Create a new Process object, raises NoSuchProcess if the PID
        does not exist, and ValueError if the parameter is not an
        integer PID."""
        if not isinstance(pid, int):
            raise ValueError("An integer is required")
        if not pid_exists(pid):
            raise NoSuchProcess(pid, None, "no process found with PID %s" % pid)
        self._pid = pid
        # platform-specific modules define an PlatformProcess
        # implementation class
        self._platform_impl = PlatformProcess(pid)
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
        try:
            pid = self.pid
            name = repr(self.name)
            cmdline = self.cmdline and repr(' '.join(self.cmdline))
        except NoSuchProcess:
            details = "(pid=%s (terminated))" % self.pid
        except AccessDenied:
            details = "(pid=%s)" % (self.pid)
        else:
            if cmdline:
                details = "(pid=%s, name=%s, cmdline=%s)" % (pid, name, cmdline)
            else:
                details = "(pid=%s, name=%s)" % (pid, name)
        return "%s.%s %s" % (self.__class__.__module__,
                             self.__class__.__name__, details)

    def __repr__(self):
        return "<%s at %s>" % (self.__str__(), id(self))

    def __eq__(self, other):
        """Test for equality with another Process object based on pid
        and creation time.
        """
        h1 = (self.pid, self.create_time)
        h2 = (other.pid, other.create_time)
        return h1 == h2

    @property
    def pid(self):
        """The process pid."""
        return self._pid

    @property
    def ppid(self):
        """The process parent pid."""
        return self._platform_impl.get_process_ppid()

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
        name = self._platform_impl.get_process_name()
        if os.name == 'posix':
            # On UNIX the name gets truncated to the first 15 characters.
            # If it matches the first part of the cmdline we return that
            # one instead because it's usually more explicative.
            # Examples are "gnome-keyring-d" vs. "gnome-keyring-daemon".
            cmdline = self.cmdline
            if cmdline:
                extended_name = os.path.basename(cmdline[0])
                if extended_name.startswith(name):
                    name = extended_name
        # XXX - perhaps needs refactoring
        self._platform_impl._process_name = name
        return name

    @property
    def exe(self):
        """The process executable as an absolute path name."""
        exe = self._platform_impl.get_process_exe()
        # if we have the cmdline but not the exe, figure it out from argv[0]
        if not exe:
            cmdline = self.cmdline
            if cmdline and hasattr(os, 'access') and hasattr(os, 'X_OK'):
                _exe = os.path.realpath(cmdline[0])
                if os.path.isfile(_exe) and os.access(_exe, os.X_OK):
                    return _exe
        return exe

    @property
    def path(self):
        msg = "'path' property is deprecated; use 'os.path.dirname(exe)' instead"
        warnings.warn(msg, DeprecationWarning)
        return os.path.dirname(self.exe)

    @property
    def cmdline(self):
        """The command line process has been called with."""
        return self._platform_impl.get_process_cmdline()

    @property
    def uid(self):
        """The real user id of the current process."""
        return self._platform_impl.get_process_uid()

    @property
    def gid(self):
        """The real group id of the current process."""
        return self._platform_impl.get_process_gid()

    @property
    def username(self):
        """The name of the user that owns the process."""
        if os.name == 'posix':
            if pwd is None:
                # might happen on compiled-from-sources python
                raise ImportError("requires pwd module shipped with standard python")
            return pwd.getpwuid(self.uid).pw_name
        else:
            return self._platform_impl.get_process_username()

    @property
    def create_time(self):
        """The process creation time as a floating point number
        expressed in seconds since the epoch, in UTC.
        """
        return self._platform_impl.get_process_create_time()

    # available for Windows and Linux only
    if hasattr(PlatformProcess, "get_process_cwd"):
        def getcwd(self):
            """Return a string representing the process current working
            directory.
            """
            return self._platform_impl.get_process_cwd()

    def get_children(self):
        """Return the children of this process as a list of Process
        objects.
        """
        if not self.is_running():
            name = self._platform_impl._process_name
            raise NoSuchProcess(self.pid, name)
        retlist = []
        for proc in process_iter():
            try:
                if proc.ppid == self.pid:
                    retlist.append(proc)
            except NoSuchProcess:
                pass
        return retlist

    def get_cpu_percent(self):
        """Compare process times to system time elapsed since last call
        and calculate CPU utilization as a percentage. It is recommended
        for accuracy that this function be called with at least 1 second
        between calls. The initial delta is calculated from the
        instantiation of the Process object.
        """
        now = time.time()
        # will raise AccessDenied on OS X if not root or in procmod group
        user_t, kern_t = self._platform_impl.get_cpu_times()

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
        return self._platform_impl.get_cpu_times()

    def get_memory_info(self):
        """Return a tuple representing RSS (Resident Set Size) and VMS
        (Virtual Memory Size) in bytes.

        On UNIX RSS and VMS are the same values shown by ps.

        On Windows RSS and VMS refer to "Mem Usage" and "VM Size" columns
        of taskmgr.exe.
        """
        return self._platform_impl.get_memory_info()

    def get_memory_percent(self):
        """Compare physical system memory to process resident memory and
        calculate process memory utilization as a percentage.
        """
        rss = self._platform_impl.get_memory_info()[0]
        try:
            return (rss / float(TOTAL_PHYMEM)) * 100
        except ZeroDivisionError:
            return 0.0

    def get_open_files(self):
        """Return files opened by process as a list of paths."""
        return self._platform_impl.get_open_files()

    def get_connections(self):
        """Return TCP and UPD connections opened by process as a list
        of namedtuple/s.
        For third party processes (!= os.getpid()) results can differ
        depending on user privileges.
        """
        return self._platform_impl.get_connections()

    def is_running(self):
        """Return whether the current process is running in the current
        process list.
        """
        try:
            newproc = Process(self.pid)
            return self == newproc
        except NoSuchProcess:
            return False

    def send_signal(self, sig):
        """Send a signal to process (see signal module constants).
        On Windows only SIGTERM is valid and is treated as an alias
        for kill().
        """
        # safety measure in case the current process has been killed in
        # meantime and the kernel reused its PID
        if not self.is_running():
            name = self._platform_impl._process_name
            raise NoSuchProcess(self.pid, name)
        if os.name == 'posix':
            try:
                os.kill(self.pid, sig)
            except OSError, err:
                name = self._platform_impl._process_name
                if err.errno == errno.ESRCH:
                    raise NoSuchProcess(self.pid, name)
                if err.errno == errno.EPERM:
                    raise AccessDenied(self.pid, name)
                raise
        else:
            if sig == signal.SIGTERM:
                self._platform_impl.kill_process()
            else:
                raise ValueError("only SIGTERM is supported on Windows")

    def suspend(self):
        """Suspend process execution."""
        # safety measure in case the current process has been killed in
        # meantime and the kernel reused its PID
        if not self.is_running():
            name = self._platform_impl._process_name
            raise NoSuchProcess(self.pid, name)
        # windows
        if hasattr(self._platform_impl, "suspend_process"):
            self._platform_impl.suspend_process()
        else:
            # posix
            self.send_signal(signal.SIGSTOP)

    def resume(self):
        """Resume process execution."""
        # safety measure in case the current process has been killed in
        # meantime and the kernel reused its PID
        if not self.is_running():
            name = self._platform_impl._process_name
            raise NoSuchProcess(self.pid, name)
        # windows
        if hasattr(self._platform_impl, "resume_process"):
            self._platform_impl.resume_process()
        else:
            # posix
            self.send_signal(signal.SIGCONT)

    def terminate(self):
        """Terminate the process with SIGTERM.
        On Windows this is an alias for kill().
        """
        self.send_signal(signal.SIGTERM)

    def kill(self):
        """Kill the current process."""
        # safety measure in case the current process has been killed in
        # meantime and the kernel reused its PID
        if not self.is_running():
            name = self._platform_impl._process_name
            raise NoSuchProcess(self.pid, name)
        if os.name == 'posix':
            self.send_signal(signal.SIGKILL)
        else:
            self._platform_impl.kill_process()


def process_iter():
    """Return an iterator yielding a Process class instances for all
    running processes on the local machine.
    """
    pids = get_pid_list()
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

def cpu_percent(interval=0.1):
    """Return a float representing the current system-wide CPU 
    utilization as a percentage.
    """
    t1 = cpu_times()
    t1_all = sum(t1)
    t1_busy = t1_all - t1.idle

    time.sleep(interval)

    t2 = cpu_times()
    t2_all = sum(t2)
    t2_busy = t2_all - t2.idle

    # This should avoid precision issues (t2_busy < t1_busy1).
    # This is based on the assumption that anything beyond 2nd 
    # decimal digit is garbage.
    t1_busy = round(t1_busy, 2)
    t2_busy = round(t2_busy, 2)
 
    if t2_busy == t1_busy:
        return 0.0

    busy_delta = t2_busy - t1_busy
    all_delta = t2_all - t1_all
    busy_perc = (busy_delta / all_delta) * 100
    return round(busy_perc, 1)
    

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
            cmd = "[%s]" % proc.name
        return "%-9s %-5s %-4s %4s %7s %7s %5s %8s %s" \
                % (user, pid, cpu, mem, vsz, rss, start, cputime, cmd)

    print "%-9s %-5s %-4s %4s %7s %7s %5s %7s  %s" \
      % ("USER", "PID", "%CPU", "%MEM", "VSZ", "RSS", "START", "TIME", "COMMAND")
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

