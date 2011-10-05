#!/usr/bin/env python
#
# $Id$
#
# Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""psutil is a module providing convenience functions for managing
processes and gather system information in a portable way by using
Python.
"""

__version__ = "0.3.1"
version_info = tuple([int(num) for num in __version__.split('.')])

__all__ = [
    # exceptions
    "Error", "NoSuchProcess", "AccessDenied", "TimeoutExpired",
    # constants
    "NUM_CPUS", "TOTAL_PHYMEM", "BOOT_TIME",
    "version_info", "__version__",
    "STATUS_RUNNING", "STATUS_IDLE", "STATUS_SLEEPING", "STATUS_DISK_SLEEP",
    "STATUS_STOPPED", "STATUS_TRACING_STOP", "STATUS_ZOMBIE", "STATUS_DEAD",
    "STATUS_WAKING", "STATUS_LOCKED",
    # classes
    "Process", "Popen",
    # functions
    "test", "pid_exists", "get_pid_list", "process_iter", "get_process_list",
    "phymem_usage", "virtmem_usage"
    "cpu_times", "per_cpu_times", "cpu_percent", "per_cpu_percent",
    "network_io_counters", "disk_io_counters",
    ]

import sys
import os
import time
import signal
import warnings
import errno
import subprocess
try:
    import pwd
except ImportError:
    pwd = None

from psutil.error import Error, NoSuchProcess, AccessDenied, TimeoutExpired
from psutil._compat import property
from psutil._common import (STATUS_RUNNING, STATUS_IDLE, STATUS_SLEEPING,
                            STATUS_DISK_SLEEP, STATUS_STOPPED,
                            STATUS_TRACING_STOP, STATUS_ZOMBIE, STATUS_DEAD,
                            STATUS_WAKING, STATUS_LOCKED
                            )

# import the appropriate module for our platform only
if sys.platform.lower().startswith("linux"):
    import psutil._pslinux as _psplatform
    from psutil._pslinux import (phymem_buffers,
                                 cached_phymem,
                                 IOPRIO_CLASS_NONE,
                                 IOPRIO_CLASS_RT,
                                 IOPRIO_CLASS_BE,
                                 IOPRIO_CLASS_IDLE)
    phymem_buffers = _psplatform.phymem_buffers
    cached_phymem = _psplatform.cached_phymem

elif sys.platform.lower().startswith("win32"):
    import psutil._psmswindows as _psplatform
    from psutil._psmswindows import (ABOVE_NORMAL_PRIORITY_CLASS,
                                     BELOW_NORMAL_PRIORITY_CLASS,
                                     HIGH_PRIORITY_CLASS,
                                     IDLE_PRIORITY_CLASS,
                                     NORMAL_PRIORITY_CLASS,
                                     REALTIME_PRIORITY_CLASS)

elif sys.platform.lower().startswith("darwin"):
    import psutil._psosx as _psplatform

elif sys.platform.lower().startswith("freebsd"):
    import psutil._psbsd as _psplatform

else:
    raise NotImplementedError('platform %s is not supported' % sys.platform)

__all__.extend(_psplatform.__extra__all__)

NUM_CPUS = _psplatform.NUM_CPUS
BOOT_TIME = _psplatform.BOOT_TIME
TOTAL_PHYMEM = _psplatform.phymem_usage()[0]

get_pid_list = _psplatform.get_pid_list
pid_exists = _psplatform.pid_exists


class Process(object):
    """Represents an OS process."""

    def __init__(self, pid):
        """Create a new Process object, raises NoSuchProcess if the PID
        does not exist, and ValueError if the parameter is not an
        integer PID.
        """
        if not isinstance(pid, int):
            raise ValueError("an integer is required")
        if not pid_exists(pid):
            raise NoSuchProcess(pid, None, "no process found with pid %s" % pid)
        self._pid = pid
        # platform-specific modules define an _psplatform.Process
        # implementation class
        self._platform_impl = _psplatform.Process(pid)
        self._last_sys_cpu_times = None
        self._last_proc_cpu_times = None

    def __str__(self):
        try:
            pid = self.pid
            name = repr(self.name)
        except NoSuchProcess:
            details = "(pid=%s (terminated))" % self.pid
        except AccessDenied:
            details = "(pid=%s)" % (self.pid)
        else:
            details = "(pid=%s, name=%s)" % (pid, name)
        return "%s.%s%s" % (self.__class__.__module__,
                            self.__class__.__name__, details)

    def __repr__(self):
        return "<%s at %s>" % (self.__str__(), id(self))

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
        """Return the parent process as a Process object. If no parent
        pid is known return None.
        """
        ppid = self.ppid
        if ppid is not None:
            try:
                return Process(ppid)
            except NoSuchProcess:
                pass

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
        if not exe:
            raise AccessDenied(self.pid, self._platform_impl._process_name)
        return exe

    @property
    def cmdline(self):
        """The command line process has been called with."""
        return self._platform_impl.get_process_cmdline()

    @property
    def status(self):
        """The process current status as a STATUS_* constant."""
        return self._platform_impl.get_process_status()

    @property
    def nice(self):
        """Get or set process niceness (priority)."""
        return self._platform_impl.get_process_nice()

    @nice.setter
    def nice(self, value):
        # invoked on "p.nice = num"; change process niceness
        return self._platform_impl.set_process_nice(value)

    if os.name == 'posix':

        @property
        def uids(self):
            """Return a named tuple denoting the process real,
            effective, and saved user ids.
            """
            return self._platform_impl.get_process_uids()

        @property
        def gids(self):
            """Return a named tuple denoting the process real,
            effective, and saved group ids.
            """
            return self._platform_impl.get_process_gids()

        @property
        def terminal(self):
            """The terminal associated with this process, if any,
            else None.
            """
            return self._platform_impl.get_process_terminal()

    @property
    def username(self):
        """The name of the user that owns the process.
        On UNIX this is calculated by using *real* process uid.
        """
        if os.name == 'posix':
            if pwd is None:
                # might happen if python was installed from sources
                raise ImportError("requires pwd module shipped with standard python")
            return pwd.getpwuid(self.uids.real).pw_name
        else:
            return self._platform_impl.get_process_username()

    @property
    def create_time(self):
        """The process creation time as a floating point number
        expressed in seconds since the epoch, in UTC.
        """
        return self._platform_impl.get_process_create_time()

    # available for Windows and Linux only
    if hasattr(_psplatform.Process, "get_process_cwd"):

        def getcwd(self):
            """Return a string representing the process current working
            directory.
            """
            return self._platform_impl.get_process_cwd()

    # Linux, BSD and Windows only
    if hasattr(_psplatform.Process, "get_process_io_counters"):

        def get_io_counters(self):
            """Return process I/O statistics as a namedtuple including
            the number of read/write calls performed and the amount of
            bytes read and written by the process.
            """
            return self._platform_impl.get_process_io_counters()

    # available only on Linux
    if hasattr(_psplatform.Process, "get_process_ionice"):

        def get_ionice(self):
            """Return process I/O niceness (priority) as a namedtuple."""
            return self._platform_impl.get_process_ionice()

        def set_ionice(self, ioclass, value=None):
            """Set process I/O niceness (priority).
            ioclass is one of the IOPRIO_CLASS_* constants.
            iodata is a number which goes from 0 to 7. The higher the
            value, the lower the I/O priority of the process.
            """
            return self._platform_impl.set_process_ionice(ioclass, value)

    def get_num_threads(self):
        """Return the number of threads used by this process."""
        return self._platform_impl.get_process_num_threads()

    def get_threads(self):
        """Return threads opened by process as a list of namedtuples
        including thread id and thread CPU times (user/system).
        """
        return self._platform_impl.get_process_threads()

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

    def get_cpu_percent(self, interval=0.1):
        """Return a float representing the current process CPU
        utilization as a percentage.

        When interval is > 0.0 compares process times to system CPU
        times elapsed before and after the interval (blocking).

        When interval is 0.0 or None compares process times to system CPU
        times elapsed since last call, returning immediately.
        In this case is recommended for accuracy that this function be
        called with at least 0.1 seconds between calls.
        """
        blocking = interval is not None and interval > 0.0
        if blocking:
            st1 = sum(cpu_times())
            pt1 = self._platform_impl.get_cpu_times()
            time.sleep(interval)
            st2 = sum(cpu_times())
            pt2 = self._platform_impl.get_cpu_times()
        else:
            st1 = self._last_sys_cpu_times
            pt1 = self._last_proc_cpu_times
            st2 = sum(cpu_times())
            pt2 = self._platform_impl.get_cpu_times()
            if st1 is None or pt1 is None:
                self._last_sys_cpu_times = st2
                self._last_proc_cpu_times = pt2
                return 0.0

        delta_proc = (pt2.user - pt1.user) + (pt2.system - pt1.system)
        delta_time = st2 - st1
        # reset values for next call in case of interval == None
        self._last_sys_cpu_times = st2
        self._last_proc_cpu_times = pt2

        try:
            # the utilization split between all CPUs
            overall_percent = (delta_proc / delta_time) * 100
        except ZeroDivisionError:
            # interval was too low
            return 0.0
        # the utilization of a single CPU
        single_cpu_percent = overall_percent * NUM_CPUS
        # ugly hack to avoid troubles with float precision issues
        if single_cpu_percent > 100.0:
            return 100.0
        return round(single_cpu_percent, 1)

    def get_cpu_times(self):
        """Return a tuple whose values are process CPU user and system
        times. The same as os.times() but per-process.
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
        """Return files opened by process as a list of namedtuples
        including absolute file name and file descriptor number.
        """
        return self._platform_impl.get_open_files()

    def get_connections(self):
        """Return TCP and UPD connections opened by process as a list
        of namedtuples.
        On BSD and OSX results for third party processes (!= os.getpid())
        can differ depending on user privileges.
        """
        return self._platform_impl.get_connections()

    def is_running(self):
        """Return whether this process is running."""
        try:
            # Test for equality with another Process object based
            # on pid and creation time.
            # This pair is supposed to indentify a Process instance
            # univocally over the time (the PID alone is not enough as
            # it might refer to a process which is gone in meantime
            # and its PID reused by another process).
            new_self = Process(self.pid)
            p1 = (self.pid, self.create_time)
            p2 = (new_self.pid, new_self.create_time)
        except NoSuchProcess:
            return False
        else:
            return p1 == p2

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

    def wait(self, timeout=None):
        """Wait for process to terminate and, if process is a children
        of the current one also return its exit code, else None.
        """
        if timeout is not None and not timeout >= 0:
            raise ValueError("timeout must be a positive integer")
        return self._platform_impl.process_wait(timeout)


class Popen(Process):
    """A more convenient interface to stdlib subprocess module.
    It starts a sub process and deals with it exactly as when using
    subprocess.Popen class but in addition also provides all the
    property and methods of psutil.Process class in a unique interface:

      >>> import psutil
      >>> from subprocess import PIPE
      >>> p = psutil.Popen(["/usr/bin/python", "-c", "print 'hi'"], stdout=PIPE)
      >>> p.name
      'python'
      >>> p.uids
      user(real=1000, effective=1000, saved=1000)
      >>> p.username
      'giampaolo'
      >>> p.communicate()
      ('hi\n', None)
      >>> p.terminate()
      >>> p.wait(timeout=2)
      0
      >>>

    For method names common to both classes such as kill(), terminate()
    and wait(), psutil.Process implementation takes precedence.

    For a complete documentation refers to:
    http://docs.python.org/library/subprocess.html
    """

    def __init__(self, *args, **kwargs):
        self.__subproc = subprocess.Popen(*args, **kwargs)
        Process.__init__(self, self.__subproc.pid)

    def __dir__(self):
        return list(set(dir(Popen) + dir(subprocess.Popen)))

    def __getattribute__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            try:
                return object.__getattribute__(self.__subproc, name)
            except AttributeError:
                raise AttributeError("%s instance has no attribute '%s'"
                                      %(self.__class__.__name__, name))

def process_iter():
    """Return an iterator yielding a Process class instances for all
    running processes on the local machine.
    """
    pids = get_pid_list()
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

def cpu_times(percpu=False):
    """Return system-wide CPU times as a namedtuple object.
    Every CPU time represents the time CPU has spent in the given mode.
    The attributes availability varies depending on the platform.
    Here follows a list of all available attributes:
     - user
     - system
     - idle
     - nice (UNIX)
     - iowait (Linux)
     - irq (Linux, FreeBSD)
     - softirq (Linux)

    When percpu is True return a list of nameduples for each CPU.
    First element of the list refers to first CPU, second element
    to second CPU and so on.
    The order of the list is consistent across calls.
    """
    if not percpu:
        return _psplatform.get_system_cpu_times()
    else:
        return _psplatform.get_system_per_cpu_times()


_last_cpu_times = cpu_times()
_last_per_cpu_times = cpu_times(percpu=True)

def cpu_percent(interval=0.1, percpu=False):
    """Return a float representing the current system-wide CPU
    utilization as a percentage.

    When interval is > 0.0 compares system CPU times elapsed before
    and after the interval (blocking).

    When interval is 0.0 or None compares system CPU times elapsed
    since last call or module import, returning immediately.
    In this case is recommended for accuracy that this function be
    called with at least 0.1 seconds between calls.

    When percpu is True returns a list of floats representing the
    utilization as a percentage for each CPU.
    First element of the list refers to first CPU, second element
    to second CPU and so on.
    The order of the list is consistent across calls.
    """
    global _last_cpu_times
    global _last_per_cpu_times
    blocking = interval is not None and interval > 0.0

    def calculate(t1, t2):
        t1_all = sum(t1)
        t1_busy = t1_all - t1.idle

        t2_all = sum(t2)
        t2_busy = t2_all - t2.idle

        # this usually indicates a float precision issue
        if t2_busy <= t1_busy:
            return 0.0

        busy_delta = t2_busy - t1_busy
        all_delta = t2_all - t1_all
        busy_perc = (busy_delta / all_delta) * 100
        return round(busy_perc, 1)

    # system-wide usage
    if not percpu:
        if blocking:
            t1 = cpu_times()
            time.sleep(interval)
        else:
            t1 = _last_cpu_times
        _last_cpu_times = cpu_times()
        return calculate(t1, _last_cpu_times)
    # per-cpu usage
    else:
        ret = []
        if blocking:
            tot1 = cpu_times(percpu=True)
            time.sleep(interval)
        else:
            tot1 = _last_per_cpu_times
        _last_per_cpu_times = cpu_times(percpu=True)
        for t1, t2 in zip(tot1, _last_per_cpu_times):
            ret.append(calculate(t1, t2))
        return ret

def phymem_usage():
    """Return the amount of total, used and free physical memory
    on the system in bytes plus the percentage usage.
    """
    return _psplatform.phymem_usage()

def virtmem_usage():
    """Return the amount of total, used and free virtual memory
    on the system in bytes plus the percentage usage.

    On Linux they match the values returned by free command line utility.
    On OS X and FreeBSD they represent the same values as returned by
    sysctl vm.vmtotal. On Windows they are determined by reading the
    PageFile values of MEMORYSTATUSEX structure.
    """
    return _psplatform.virtmem_usage()

def disk_usage(path):
    """Return disk usage statistics about the given path as a namedtuple
    including total, used and free space expressed in bytes plus the
    percentage usage.
    """
    return _psplatform.get_disk_usage(path)

def disk_partitions(all=False):
    """Return mounted partitions as a list of namedtuples including
    device, mount point and filesystem type.

    If "all" parameter is False return physical devices only and ignore
    all others.
    """
    return _psplatform.disk_partitions(all)

if hasattr(_psplatform, "network_io_counters"):

    def network_io_counters(pernic=False):
        """Return network I/O statistics as a namedtuple including:
         - number of bytes sent
         - number of bytes received
         - number of packets sent
         - number of packets received

        If pernic is True return the same information for every
        network interface installed on the system as a dictionary
        with network interface names as the keys and the namedtuple
        described above as the values.
        """
        from psutil._common import ntuple_net_iostat
        rawdict = _psplatform.network_io_counters()
        if pernic:
            for nic, fields in rawdict.iteritems():
                rawdict[nic] = ntuple_net_iostat(*fields)
            return rawdict
        else:
            bytes_sent, bytes_recv, packets_sent, packets_recv = 0, 0, 0, 0
            for _, fields in rawdict.iteritems():
                bytes_sent += fields[0]
                bytes_recv += fields[1]
                packets_sent += fields[2]
                packets_recv += fields[3]
            return ntuple_net_iostat(bytes_sent, bytes_recv,
                                     packets_sent, packets_recv)

if hasattr(_psplatform, "disk_io_counters"):

    def disk_io_counters(perdisk=False):
        """Return system disk I/O statistics as a namedtuple including:
         - number of bytes read
         - number of bytes written
         - number of reads
         - number of writes
         - time spent reading from disk (in nanoseconds)
         - time spent writing to disk (in nanoseconds)

        If perdisk is True return the same information for every
        physical disk installed on the system as a dictionary
        with partition names as the keys and the namedutuple
        described above as the values.
        """
        from psutil._common import ntuple_disk_iostat
        rawdict = _psplatform.disk_io_counters()
        if perdisk:
            for disk, fields in rawdict.iteritems():
                rawdict[disk] = ntuple_disk_iostat(*fields)
            return rawdict
        else:
            reads, writes, rbytes, wbytes, rtime, wtime = 0, 0, 0, 0, 0, 0
            for _, fields in rawdict.iteritems():
                reads += fields[0]
                writes += fields[1]
                rbytes += fields[2]
                wbytes += fields[3]
                rtime += fields[4]
                wtime += fields[5]
            return ntuple_disk_iostat(reads, writes, rbytes, wbytes, rtime, wtime)


def _deprecated(replacement):
    # a decorator which can be used to mark functions as deprecated
    def outer(fun):
        def inner(*args, **kwargs):
            msg = "psutil.%s is deprecated; use %s instead" \
                  % (fun.__name__, replacement)
            warnings.warn(msg, category=DeprecationWarning, stacklevel=2)
            return fun(*args, **kwargs)
        return inner
    return outer

# --- deprecated functions

@_deprecated("psutil.phymem_usage")
def avail_phymem():
    return phymem_usage().free

@_deprecated("psutil.phymem_usage")
def used_phymem():
    return phymem_usage().used

@_deprecated("psutil.virtmem_usage")
def total_virtmem():
    return virtmem_usage().total

@_deprecated("psutil.virtmem_usage")
def used_virtmem():
    return virtmem_usage().used

@_deprecated("psutil.virtmem_usage")
def avail_virtmem():
    return virtmem_usage().free

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
        cpu = round(proc.get_cpu_percent(interval=None), 1)
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

