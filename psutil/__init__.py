#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

from __future__ import division

__version__ = "0.6.1"
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
    "virtual_memory", "swap_memory",
    "cpu_times", "cpu_percent", "per_cpu_percent",
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
from psutil._compat import property, callable, defaultdict
from psutil._common import cached_property
from psutil._common import (deprecated as _deprecated,
                            nt_disk_iostat as _nt_disk_iostat,
                            nt_net_iostat as _nt_net_iostat,
                            nt_sysmeminfo as _nt_sysmeminfo,
                            isfile_strict as _isfile_strict)
from psutil._common import (STATUS_RUNNING, STATUS_IDLE, STATUS_SLEEPING,
                            STATUS_DISK_SLEEP, STATUS_STOPPED,
                            STATUS_TRACING_STOP, STATUS_ZOMBIE, STATUS_DEAD,
                            STATUS_WAKING, STATUS_LOCKED)

# import the appropriate module for our platform only
if sys.platform.startswith("linux"):
    import psutil._pslinux as _psplatform
    from psutil._pslinux import (phymem_buffers,
                                 cached_phymem,
                                 IOPRIO_CLASS_NONE,
                                 IOPRIO_CLASS_RT,
                                 IOPRIO_CLASS_BE,
                                 IOPRIO_CLASS_IDLE)
    phymem_buffers = _psplatform.phymem_buffers
    cached_phymem = _psplatform.cached_phymem

elif sys.platform.startswith("win32"):
    import psutil._psmswindows as _psplatform
    from psutil._psmswindows import (ABOVE_NORMAL_PRIORITY_CLASS,
                                     BELOW_NORMAL_PRIORITY_CLASS,
                                     HIGH_PRIORITY_CLASS,
                                     IDLE_PRIORITY_CLASS,
                                     NORMAL_PRIORITY_CLASS,
                                     REALTIME_PRIORITY_CLASS)

elif sys.platform.startswith("darwin"):
    import psutil._psosx as _psplatform

elif sys.platform.startswith("freebsd"):
    import psutil._psbsd as _psplatform

else:
    raise NotImplementedError('platform %s is not supported' % sys.platform)

__all__.extend(_psplatform.__extra__all__)

NUM_CPUS = _psplatform.NUM_CPUS
BOOT_TIME = _psplatform.BOOT_TIME
TOTAL_PHYMEM = _psplatform.TOTAL_PHYMEM


class Process(object):
    """Represents an OS process."""

    def __init__(self, pid):
        """Create a new Process object for the given pid.
        Raises NoSuchProcess if pid does not exist.
        """
        self._pid = pid
        self._gone = False
        # platform-specific modules define an _psplatform.Process
        # implementation class
        self._platform_impl = _psplatform.Process(pid)
        self._last_sys_cpu_times = None
        self._last_proc_cpu_times = None
        # cache creation time for later use in is_running() method
        try:
            self.create_time
        except AccessDenied:
            pass
        except NoSuchProcess:
            raise NoSuchProcess(pid, None, 'no process found with pid %s' % pid)

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

    def as_dict(self, attrs=[], ad_value=None):
        """Utility method returning process information as a hashable
        dictionary.

        If 'attrs' is specified it must be a list of strings reflecting
        available Process class's attribute names (e.g. ['get_cpu_times',
        'name']) else all public (read only) attributes are assumed.

        'ad_value' is the value which gets assigned to a dict key in case
        AccessDenied exception is raised when retrieving that particular
        process information.
        """
        excluded_names = set(['send_signal', 'suspend', 'resume', 'terminate',
                              'kill', 'wait', 'is_running', 'as_dict', 'parent',
                              'get_children', 'nice'])
        retdict = dict()
        for name in set(attrs or dir(self)):
            if name.startswith('_'):
                continue
            if name.startswith('set_'):
                continue
            if name in excluded_names:
                continue
            try:
                attr = getattr(self, name)
                if callable(attr):
                    if name == 'get_cpu_percent':
                        ret = attr(interval=0)
                    else:
                        ret = attr()
                else:
                    ret = attr
            except AccessDenied:
                ret = ad_value
            except NotImplementedError:
                # in case of not implemented functionality (may happen
                # on old or exotic systems) we want to crash only if
                # the user explicitly asked for that particular attr
                if attrs:
                    raise
                continue
            if name.startswith('get'):
                if name[3] == '_':
                    name = name[4:]
                elif name == 'getcwd':
                    name = 'cwd'
            retdict[name] = ret
        return retdict

    @property
    def pid(self):
        """The process pid."""
        return self._pid

    @cached_property
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

    @cached_property
    def name(self):
        """The process name."""
        name = self._platform_impl.get_process_name()
        if os.name == 'posix':
            # On UNIX the name gets truncated to the first 15 characters.
            # If it matches the first part of the cmdline we return that
            # one instead because it's usually more explicative.
            # Examples are "gnome-keyring-d" vs. "gnome-keyring-daemon".
            try:
                cmdline = self.cmdline
            except AccessDenied:
                pass
            else:
                if cmdline:
                    extended_name = os.path.basename(cmdline[0])
                    if extended_name.startswith(name):
                        name = extended_name
        # XXX - perhaps needs refactoring
        self._platform_impl._process_name = name
        return name

    @cached_property
    def exe(self):
        """The process executable path. May also be an empty string."""
        def guess_it(fallback):
            # try to guess exe from cmdline[0] in absence of a native
            # exe representation
            cmdline = self.cmdline
            if cmdline and hasattr(os, 'access') and hasattr(os, 'X_OK'):
                exe = cmdline[0]  # the possible exe
                rexe = os.path.realpath(exe)  # ...in case it's a symlink
                if os.path.isabs(rexe) and os.path.isfile(rexe) \
                and os.access(rexe, os.X_OK):
                    return exe
            if isinstance(fallback, AccessDenied):
                raise fallback
            return fallback

        try:
            exe = self._platform_impl.get_process_exe()
        except AccessDenied:
            err = sys.exc_info()[1]
            return guess_it(fallback=err)
        else:
            if not exe:
                # underlying implementation can legitimately return an
                # empty string; if that's the case we don't want to
                # raise AD while guessing from the cmdline
                try:
                    exe = guess_it(fallback=exe)
                except AccessDenied:
                    pass
            return exe

    @cached_property
    def cmdline(self):
        """The command line process has been called with."""
        return self._platform_impl.get_process_cmdline()

    @property
    def status(self):
        """The process current status as a STATUS_* constant."""
        return self._platform_impl.get_process_status()

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

    @cached_property
    def create_time(self):
        """The process creation time as a floating point number
        expressed in seconds since the epoch, in UTC.
        """
        return self._platform_impl.get_process_create_time()

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

    def get_nice(self):
        """Get process niceness (priority)."""
        return self._platform_impl.get_process_nice()

    def set_nice(self, value):
        """Set process niceness (priority)."""
        return self._platform_impl.set_process_nice(value)

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

    # available on Windows and Linux only
    if hasattr(_psplatform.Process, "get_process_cpu_affinity"):

        def get_cpu_affinity(self):
            """Get process current CPU affinity."""
            return self._platform_impl.get_process_cpu_affinity()

        def set_cpu_affinity(self, cpus):
            """Set process current CPU affinity.
            'cpus' is a list of CPUs for which you want to set the
            affinity (e.g. [0, 1]).
            """
            return self._platform_impl.set_process_cpu_affinity(cpus)

    if os.name == 'nt':

        def get_num_handles(self):
            """Return the number of handles opened by this process
            (Windows only).
            """
            return self._platform_impl.get_num_handles()

    if os.name == 'posix':

        def get_num_fds(self):
            """Return the number of file descriptors opened by this
            process (POSIX only).
            """
            return self._platform_impl.get_num_fds()

    def get_num_ctx_switches(self):
        """Return the number voluntary and involuntary context switches
        performed by this process.
        """
        return self._platform_impl.get_num_ctx_switches()

    def get_num_threads(self):
        """Return the number of threads used by this process."""
        return self._platform_impl.get_process_num_threads()

    def get_threads(self):
        """Return threads opened by process as a list of namedtuples
        including thread id and thread CPU times (user/system).
        """
        return self._platform_impl.get_process_threads()

    def get_children(self, recursive=False):
        """Return the children of this process as a list of Process
        objects.
        If recursive is True return all the parent descendants.

        Example (A == this process):

         A ─┐
            │
            ├─ B (child) ─┐
            │             └─ X (grandchild) ─┐
            │                                └─ Y (great grandchild)
            ├─ C (child)
            └─ D (child)

        >>> p.get_children()
        B, C, D
        >>> p.get_children(recursive=True)
        B, X, Y, C, D

        Note that in the example above if process X disappears
        process Y won't be returned either as the reference to
        process A is lost.
        """
        if not self.is_running():
            name = self._platform_impl._process_name
            raise NoSuchProcess(self.pid, name)

        ret = []
        if not recursive:
            for p in process_iter():
                try:
                    if p.ppid == self.pid:
                        # if child happens to be older than its parent
                        # (self) it means child's PID has been reused
                        if self.create_time <= p.create_time:
                            ret.append(p)
                except NoSuchProcess:
                    pass
        else:
            # construct a dict where 'values' are all the processes
            # having 'key' as their parent
            table = defaultdict(list)
            for p in process_iter():
                try:
                    table[p.ppid].append(p)
                except NoSuchProcess:
                    pass
            # At this point we have a mapping table where table[self.pid]
            # are the current process's children.
            # Below, we look for all descendants recursively, similarly
            # to a recursive function call.
            checkpids = [self.pid]
            for pid in checkpids:
                for child in table[pid]:
                    try:
                        # if child happens to be older than its parent
                        # (self) it means child's PID has been reused
                        intime = self.create_time <= child.create_time
                    except NoSuchProcess:
                        pass
                    else:
                        if intime:
                            ret.append(child)
                            if child.pid not in checkpids:
                                checkpids.append(child.pid)
        return ret

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
        # on posix a percentage > 100 is legitimate
        # http://stackoverflow.com/questions/1032357/comprehending-top-cpu-usage
        # on windows we use this ugly hack to avoid troubles with float
        # precision issues
        if os.name != 'posix':
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

    def get_ext_memory_info(self):
        """Return a namedtuple with variable fields depending on the
        platform representing extended memory information about
        the process. All numbers are expressed in bytes.
        """
        return self._platform_impl.get_ext_memory_info()

    def get_memory_percent(self):
        """Compare physical system memory to process resident memory and
        calculate process memory utilization as a percentage.
        """
        rss = self._platform_impl.get_memory_info()[0]
        try:
            return (rss / float(TOTAL_PHYMEM)) * 100
        except ZeroDivisionError:
            return 0.0

    def get_memory_maps(self, grouped=True):
        """Return process's mapped memory regions as a list of nameduples
        whose fields are variable depending on the platform.

        If 'grouped' is True the mapped regions with the same 'path'
        are grouped together and the different memory fields are summed.

        If 'grouped' is False every mapped region is shown as a single
        entity and the namedtuple will also include the mapped region's
        address space ('addr') and permission set ('perms').
        """
        it = self._platform_impl.get_memory_maps()
        if grouped:
            d = {}
            for tupl in it:
                path = tupl[2]
                nums = tupl[3:]
                try:
                    d[path] = map(lambda x, y: x+y, d[path], nums)
                except KeyError:
                    d[path] = nums
            nt = self._platform_impl.nt_mmap_grouped
            return [nt(path, *d[path]) for path in d]
        else:
            nt = self._platform_impl.nt_mmap_ext
            return [nt(*x) for x in it]

    def get_open_files(self):
        """Return files opened by process as a list of namedtuples
        including absolute file name and file descriptor number.
        """
        return self._platform_impl.get_open_files()

    def get_connections(self, kind='inet'):
        """Return connections opened by process as a list of namedtuples.
        The kind parameter filters for connections that fit the following
        criteria:

        Kind Value      Connections using
        inet            IPv4 and IPv6
        inet4           IPv4
        inet6           IPv6
        tcp             TCP
        tcp4            TCP over IPv4
        tcp6            TCP over IPv6
        udp             UDP
        udp4            UDP over IPv4
        udp6            UDP over IPv6
        unix            UNIX socket (both UDP and TCP protocols)
        all             the sum of all the possible families and protocols
        """
        return self._platform_impl.get_connections(kind)

    def is_running(self):
        """Return whether this process is running."""
        if self._gone:
            return False
        try:
            # Checking if pid is alive is not enough as the pid might
            # have been reused by another process.
            # pid + creation time, on the other hand, is supposed to
            # identify a process univocally.
            return self.create_time == \
                   self._platform_impl.get_process_create_time()
        except NoSuchProcess:
            self._gone = True
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
            except OSError:
                err = sys.exc_info()[1]
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

    # --- deprecated API

    @property
    def nice(self):
        """Get or set process niceness (priority).
        Deprecated, use get_nice() instead.
        """
        msg = "this property is deprecated; use Process.get_nice() method instead"
        warnings.warn(msg, category=DeprecationWarning, stacklevel=2)
        return self.get_nice()

    @nice.setter
    def nice(self, value):
        # invoked on "p.nice = num"; change process niceness
        # deprecated in favor of set_nice()
        msg = "this property is deprecated; use Process.set_nice() method instead"
        warnings.warn(msg, category=DeprecationWarning, stacklevel=2)
        return self.set_nice(value)


class Popen(Process):
    """A more convenient interface to stdlib subprocess module.
    It starts a sub process and deals with it exactly as when using
    subprocess.Popen class but in addition also provides all the
    property and methods of psutil.Process class in a single interface:

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
        self._pid = self.__subproc.pid
        self._gone = False
        self._platform_impl = _psplatform.Process(self._pid)
        self._last_sys_cpu_times = None
        self._last_proc_cpu_times = None
        try:
            self.create_time
        except AccessDenied:
            pass
        except NoSuchProcess:
            raise NoSuchProcess(self._pid, None,
                                "no process found with pid %s" % pid)

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


# =====================================================================
# --- system processes related functions
# =====================================================================

get_pid_list = _psplatform.get_pid_list
pid_exists = _psplatform.pid_exists

_pmap = {}

def process_iter():
    """Return a generator yielding a Process class instance for all
    running processes on the local machine.

    Every new Process instance is only created once and then cached
    into an internal table which is updated every time this is used.

    The sorting order in which processes are yielded is based on
    their PIDs.
    """
    def add(pid):
        proc = Process(pid)
        _pmap[proc.pid] = proc
        return proc

    def remove(pid):
        _pmap.pop(pid, None)

    a = set(get_pid_list())
    b = set(_pmap.keys())
    new_pids = a - b
    gone_pids = b - a

    for pid in gone_pids:
        remove(pid)
    for pid, proc in sorted(list(_pmap.items()) + \
                            list(dict.fromkeys(new_pids).items())):
        try:
            if proc is None:  # new process
                yield add(pid)
            else:
                # use is_running() to check whether PID has been reused by
                # another process in which case yield a new Process instance
                if proc.is_running():
                    yield proc
                else:
                    yield add(pid)
        except NoSuchProcess:
            remove(pid)
        except AccessDenied:
            # Process creation time can't be determined hence there's
            # no way to tell whether the pid of the cached process
            # has been reused. Just return the cached version.
            yield proc

# =====================================================================
# --- CPU related functions
# =====================================================================

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

# =====================================================================
# --- system memory related functions
# =====================================================================

def virtual_memory():
    """Return statistics about system memory usage as a namedtuple
    including the following fields, expressed in bytes:

     - total:
       total physical memory available.

     - available:
       the actual amount of available memory that can be given
       instantly to processes that request more memory in bytes; this
       is calculated by summing different memory values depending on
       the platform (e.g. free + buffers + cached on Linux) and it is
       supposed to be used to monitor actual memory usage in a cross
       platform fashion.

     - percent:
       the percentage usage calculated as (total - available) / total * 100

     - used:
       memory used, calculated differently depending on the platform and
       designed for informational purposes only:
        OSX: active + inactive + wired
        BSD: active + wired + cached
        LINUX: total - free

     - free:
       memory not being used at all (zeroed) that is readily available;
       note that this doesn't reflect the actual memory available
       (use 'available' instead)

    Platform-specific fields:

     - active (UNIX):
       memory currently in use or very recently used, and so it is in RAM.

     - inactive (UNIX):
       memory that is marked as not used.

     - buffers (BSD, Linux):
       cache for things like file system metadata.

     - cached (BSD, OSX):
       cache for various things.

     - wired (OSX, BSD):
       memory that is marked to always stay in RAM. It is never moved to disk.

     - shared (BSD):
       memory that may be simultaneously accessed by multiple processes.

    The sum of 'used' and 'available' does not necessarily equal total.
    On Windows 'available' and 'free' are the same.
    """
    return _psplatform.virtual_memory()

def swap_memory():
    """Return system swap memory statistics as a namedtuple including
    the following attributes:

     - total:   total swap memory in bytes
     - used:    used swap memory in bytes
     - free:    free swap memory in bytes
     - percent: the percentage usage
     - sin:     no. of bytes the system has swapped in from disk (cumulative)
     - sout:    no. of bytes the system has swapped out from disk (cumulative)

    'sin' and 'sout' on Windows are meaningless and always set to 0.
    """
    return _psplatform.swap_memory()

# =====================================================================
# --- disks/paritions related functions
# =====================================================================

def disk_usage(path):
    """Return disk usage statistics about the given path as a namedtuple
    including total, used and free space expressed in bytes plus the
    percentage usage.
    """
    return _psplatform.get_disk_usage(path)

def disk_partitions(all=False):
    """Return mounted partitions as a list of namedtuples including
    device, mount point, filesystem type and mount options (a raw
    string separated by commas which may vary depending on the platform).

    If "all" parameter is False return physical devices only and ignore
    all others.
    """
    return _psplatform.disk_partitions(all)

def disk_io_counters(perdisk=False):
    """Return system disk I/O statistics as a namedtuple including
    the following attributes:

     - read_count:  number of reads
     - write_count: number of writes
     - read_bytes:  number of bytes read
     - write_bytes: number of bytes written
     - read_time:   time spent reading from disk (in milliseconds)
     - write_time:  time spent writing to disk (in milliseconds)

    If perdisk is True return the same information for every
    physical disk installed on the system as a dictionary
    with partition names as the keys and the namedutuple
    described above as the values.
    """
    rawdict = _psplatform.disk_io_counters()
    if not rawdict:
        raise RuntimeError("couldn't find any physical disk")
    if perdisk:
        for disk, fields in rawdict.items():
            rawdict[disk] = _nt_disk_iostat(*fields)
        return rawdict
    else:
        return _nt_disk_iostat(*[sum(x) for x in zip(*rawdict.values())])

# =====================================================================
# --- network related functions
# =====================================================================

def network_io_counters(pernic=False):
    """Return network I/O statistics as a namedtuple including
    the following attributes:

     - bytes_sent:   number of bytes sent
     - bytes_recv:   number of bytes received
     - packets_sent: number of packets sent
     - packets_recv: number of packets received
     - errin:        total number of errors while receiving
     - errout:       total number of errors while sending
     - dropin:       total number of incoming packets which were dropped
     - dropout:      total number of outgoing packets which were dropped
                     (always 0 on OSX and BSD)

    If pernic is True return the same information for every
    network interface installed on the system as a dictionary
    with network interface names as the keys and the namedtuple
    described above as the values.
    """
    rawdict = _psplatform.network_io_counters()
    if not rawdict:
        raise RuntimeError("couldn't find any network interface")
    if pernic:
        for nic, fields in rawdict.items():
            rawdict[nic] = _nt_net_iostat(*fields)
        return rawdict
    else:
        return _nt_net_iostat(*[sum(x) for x in zip(*rawdict.values())])

# =====================================================================
# --- other system related functions
# =====================================================================

def get_users():
    """Return users currently connected on the system as a list of
    namedtuples including the following attributes.

     - user: the name of the user
     - terminal: the tty or pseudo-tty associated with the user, if any.
     - host: the host name associated with the entry, if any.
     - started: the creation time as a floating point number expressed in
       seconds since the epoch.
    """
    return _psplatform.get_system_users()

# =====================================================================
# --- deprecated functions
# =====================================================================

@_deprecated()
def get_process_list():
    """Return a list of Process class instances for all running
    processes on the local machine (deprecated).
    """
    return list(process_iter())

@_deprecated()
def phymem_usage():
    """Return the amount of total, used and free physical memory
    on the system in bytes plus the percentage usage.
    Deprecated by psutil.virtual_memory().
    """
    mem = virtual_memory()
    return _nt_sysmeminfo(mem.total, mem.used, mem.free, mem.percent)

@_deprecated("psutil.swap_memory()")
def virtmem_usage():
    return swap_memory()

@_deprecated("psutil.phymem_usage().free")
def avail_phymem():
    return phymem_usage().free

@_deprecated("psutil.phymem_usage().used")
def used_phymem():
    return phymem_usage().used

@_deprecated("psutil.virtmem_usage().total")
def total_virtmem():
    return virtmem_usage().total

@_deprecated("psutil.virtmem_usage().used")
def used_virtmem():
    return virtmem_usage().used

@_deprecated("psutil.virtmem_usage().free")
def avail_virtmem():
    return virtmem_usage().free

def test():
    """List info of all currently running processes emulating ps aux
    output.
    """
    import datetime
    from psutil._compat import print_

    today_day = datetime.date.today()
    templ = "%-10s %5s %4s %4s %7s %7s %-13s %5s %7s  %s"
    attrs = ['pid', 'username', 'get_cpu_percent', 'get_memory_percent', 'name',
             'get_cpu_times', 'create_time', 'get_memory_info']
    if os.name == 'posix':
        attrs.append('terminal')
    print_(templ % ("USER", "PID", "%CPU", "%MEM", "VSZ", "RSS", "TTY", "START",
                    "TIME", "COMMAND"))
    for p in sorted(process_iter(), key=lambda p: p.pid):
        try:
            pinfo = p.as_dict(attrs, ad_value='')
        except NoSuchProcess:
            pass
        else:
            if pinfo['create_time']:
                ctime = datetime.datetime.fromtimestamp(pinfo['create_time'])
                if ctime.date() == today_day:
                    ctime = ctime.strftime("%H:%M")
                else:
                    ctime = ctime.strftime("%b%d")
            cputime = time.strftime("%M:%S", time.localtime(sum(pinfo['cpu_times'])))
            user = pinfo['username']
            if os.name == 'nt' and '\\' in user:
                user = user.split('\\')[1]
            vms = pinfo['memory_info'] and \
                  int(pinfo['memory_info'].vms / 1024) or '?'
            rss = pinfo['memory_info'] and \
                  int(pinfo['memory_info'].rss / 1024) or '?'
            memp = pinfo['memory_percent'] and \
                   round(pinfo['memory_percent'], 1) or '?'
            print_(templ % (user[:10],
                            pinfo['pid'],
                            pinfo['cpu_percent'],
                            memp,
                            vms,
                            rss,
                            pinfo.get('terminal', '') or '?',
                            ctime,
                            cputime,
                            pinfo['name'].strip() or '?'))

if __name__ == "__main__":
    test()

del property, cached_property, division
if sys.version_info < (3, 0):
    del num
