#!/usr/bin/env python
#
# $Id$
#

import errno
import os
import subprocess
import socket
import re
import sys
import platform

try:
    from collections import namedtuple
except ImportError:
    from psutil.compat import namedtuple  # python < 2.6

import _psutil_mswindows
from psutil.error import AccessDenied, NoSuchProcess



# --- module level constants (gets pushed up to psutil module)

NUM_CPUS = _psutil_mswindows.get_num_cpus()
TOTAL_PHYMEM = _psutil_mswindows.get_total_phymem()
_UPTIME = _psutil_mswindows.get_system_uptime()
_WIN2000 = platform.win32_ver()[0] == '2000'

ERROR_ACCESS_DENIED = 5
ERROR_INVALID_PARAMETER = 87

# --- public functions

def avail_phymem():
    "Return the amount of physical memory available on the system, in bytes."
    return _psutil_mswindows.get_avail_phymem()

def used_phymem():
    "Return the amount of physical memory currently in use on the system, in bytes."
    return TOTAL_PHYMEM - _psutil_mswindows.get_avail_phymem()

def total_virtmem():
    "Return the amount of total virtual memory available on the system, in bytes."
    return _psutil_mswindows.get_total_virtmem()

def avail_virtmem():
    "Return the amount of virtual memory currently in use on the system, in bytes."
    return _psutil_mswindows.get_avail_virtmem()

def used_virtmem():
    """Return the amount of used memory currently in use on the system, in bytes."""
    return _psutil_mswindows.get_total_virtmem() - _psutil_mswindows.get_avail_virtmem()

def get_system_cpu_times():
    """Return a dict representing the following CPU times: user, system, idle."""
    times = _psutil_mswindows.get_system_cpu_times()
    return dict(user=times[0], system=times[1], idle=times[2])

def get_pid_list():
    """Returns a list of PIDs currently running on the system."""
    return _psutil_mswindows.get_pid_list()

def pid_exists(pid):
    return _psutil_mswindows.pid_exists(pid)


# --- decorator

def wrap_exceptions(callable):
    """Call callable into a try/except clause so that if a
    WindowsError 5 AccessDenied exception is raised we translate it
    into psutil.AccessDenied
    """
    def wrapper(self, *args, **kwargs):
        try:
            return callable(self, *args, **kwargs)
        except OSError, err:
            if err.errno in (errno.EACCES, ERROR_ACCESS_DENIED):
                raise AccessDenied(self.pid, self._process_name)
            if err.errno == errno.ESRCH:
                raise NoSuchProcess(self.pid, self._process_name)
            raise
    return wrapper


class WindowsProcess(object):
    """Wrapper class around underlying C implementation."""

    _meminfo_ntuple = namedtuple('meminfo', 'rss vms')
    _cputimes_ntuple = namedtuple('cputimes', 'user system')
    _connection_ntuple = namedtuple('connection', 'family type local_address '
                                                  'remote_address status fd')
    __slots__ = ["pid", "_process_name"]

    def __init__(self, pid):
        self.pid = pid
        self._process_name = None


    @wrap_exceptions
    def get_process_name(self):
        """Return process name as a string of limited len (15)."""
        return _psutil_mswindows.get_process_name(self.pid)

    def get_process_exe(self):
        # no such thing as "exe" on BSD; it will maybe be determined
        # later from cmdline[0]
        if not pid_exists(self.pid):
            raise NoSuchProcess(self.pid, self._process_name)
        return ""

    @wrap_exceptions
    def get_process_cmdline(self):
        """Return process cmdline as a list of arguments."""
        return _psutil_mswindows.get_process_cmdline(self.pid)

    @wrap_exceptions
    def get_process_ppid(self):
        """Return process parent pid."""
        return _psutil_mswindows.get_process_ppid(self.pid)

    def get_process_uid(self):
        # no such thing as uid on Windows
        if not pid_exists(self.pid):
            raise NoSuchProcess(self.pid, self._process_name)
        return -1

    def get_process_gid(self):
        # no such thing as gid on Windows
        if not pid_exists(self.pid):
            raise NoSuchProcess(self.pid, self._process_name)
        return -1

    @wrap_exceptions
    def get_memory_info(self):
        """Returns a tuple or RSS/VMS memory usage in bytes."""
        # special case for 0 (kernel processes) PID
        if self.pid == 0:
            return self._meminfo_ntuple(0, 0)
        rss, vms = _psutil_mswindows.get_memory_info(self.pid)
        return self._meminfo_ntuple(rss, vms)

    @wrap_exceptions
    def kill_process(self):
        """Terminates the process with the given PID."""
        try:
            return _psutil_mswindows.kill_process(self.pid)
        except OSError, err:
            # work around issue #24
            if (self.pid == 0) and \
            err.errno in (errno.EINVAL, ERROR_INVALID_PARAMETER):
                raise AccessDenied(self.pid, self._process_name)
            raise

    @wrap_exceptions
    def get_process_username(self):
        """Return the name of the user that owns the process"""
        if self.pid in (0, 4) or self.pid == 8 and _WIN2000:
            return 'NT AUTHORITY\\SYSTEM'
        return _psutil_mswindows.get_process_username(self.pid);

    @wrap_exceptions
    def get_process_create_time(self):
        # special case for kernel process PIDs; return system uptime
        if self.pid in (0, 4) or self.pid == 8 and _WIN2000:
            return _UPTIME
        return _psutil_mswindows.get_process_create_time(self.pid)

    @wrap_exceptions
    def get_process_num_threads(self):
        return _psutil_mswindows.get_process_num_threads(self.pid)

    @wrap_exceptions
    def get_cpu_times(self):
        user, system = _psutil_mswindows.get_process_cpu_times(self.pid)
        return self._cputimes_ntuple(user, system)

    def suspend_process(self):
        return _psutil_mswindows.suspend_process(self.pid)

    def resume_process(self):
        return _psutil_mswindows.resume_process(self.pid)

    @wrap_exceptions
    def get_process_cwd(self):
        if self.pid in (0, 4) or self.pid == 8 and _WIN2000:
            return ''
        # return a normalized pathname since the native C function appends
        # "\\" at the and of the path
        path = _psutil_mswindows.get_process_cwd(self.pid)
        return os.path.normpath(path)

    @wrap_exceptions
    def get_open_files(self):
        if self.pid in (0, 4) or self.pid == 8 and _WIN2000:
            return []
        retlist = []
        # Filenames come in in native format like:
        # "\Device\HarddiskVolume1\Windows\systemew\file.txt"
        # Convert the first part in the corresponding drive letter
        # (e.g. "C:\") by using Windows's QueryDosDevice()
        raw_file_names = _psutil_mswindows.get_process_open_files(self.pid)
        for file in raw_file_names:
            if sys.version_info >= (3,):
                file = file.decode('utf8')
            if file.startswith('\\Device\\'):
                rawdrive = '\\'.join(file.split('\\')[:3])
                driveletter = _psutil_mswindows._QueryDosDevice(rawdrive)
                file = file.replace(rawdrive, driveletter)
                if os.path.isfile(file) and file not in retlist:
                    retlist.append(file)
        return retlist

    @wrap_exceptions
    def get_connections(self):
        retlist = _psutil_mswindows.get_process_connections(self.pid)
        return [self._connection_ntuple(*conn) for conn in retlist]

PlatformProcess = WindowsProcess
