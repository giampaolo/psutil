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
from psutil.error import *


def _has_connections_support():
    """Return True if this Windows version supports
    GetExtendedTcpTable() and GetExtendedTcpTable() functions
    introduced in Windows XP SP2.
    """
    # List of minimum supported versions:
    # http://msdn.microsoft.com/en-us/library/aa365928(VS.85).aspx
    # Name mappings:
    # http://msdn.microsoft.com/en-us/library/ms724833(VS.85).aspx
    import re
    maj, _min, build, platf, sp = sys.getwindowsversion()
    try:
        sp = int(re.search(r'(\d)', sp).group())
    except (ValueError, AttributeError):
        sp = -1
    if (maj, _min) < (5, 1):
        # <= 2000
        return False
    elif (maj, _min) == (5, 1):
        # XP
        return sp >= 2
    elif (maj, _min) == (5, 2):
        # XP prof 64-bit / 2003 server / Home server
        ver = platform.win32_ver()[0].upper()
        if ver == 'XP':
            return sp >= 2
        elif ('2003' in ver) or ('SERVER' in ver):
            return sp >= 1
        else:
            return False
    else:
        # Vista, Server 2008, 7 and higher
        return (maj, _min) > (5, 2)


# --- module level constants (gets pushed up to psutil module)

NUM_CPUS = _psutil_mswindows.get_num_cpus()
TOTAL_PHYMEM = _psutil_mswindows.get_total_phymem()
_UPTIME = _psutil_mswindows.get_system_uptime()
_WIN2000 = platform.win32_ver()[0] == '2000'
_CONNECTIONS_SUPPORT = _has_connections_support()
del _has_connections_support

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
    def wrapper(self, pid, *args, **kwargs):
        try:
            return callable(self, pid, *args, **kwargs)
        except OSError, err:
            if err.errno in (errno.EACCES, ERROR_ACCESS_DENIED):
                raise AccessDenied(pid, self._process_name)
            if err.errno == errno.ESRCH:
                raise NoSuchProcess(pid, self._process_name)
            raise
    return wrapper


class Impl(object):

    _meminfo_ntuple = namedtuple('meminfo', 'rss vms')
    _cputimes_ntuple = namedtuple('cputimes', 'user system')
    _connection_ntuple = namedtuple('connection', 'family type local_address '
                                                  'remote_address status fd')
    def __init__(self):
        self._process_name = None

    @wrap_exceptions
    def get_process_info(self, pid):
        """Returns a tuple that can be passed to the psutil.ProcessInfo class
        constructor.
        """
        info_tuple = _psutil_mswindows.get_process_info(pid)
        self._process_name = info_tuple[2]
        return info_tuple

    @wrap_exceptions
    def get_memory_info(self, pid):
        """Returns a tuple or RSS/VMS memory usage in bytes."""
        # special case for 0 (kernel processes) PID
        if pid == 0:
            return (0, 0)
        rss, vms = _psutil_mswindows.get_memory_info(pid)
        return self._meminfo_ntuple(rss, vms)

    @wrap_exceptions
    def kill_process(self, pid):
        """Terminates the process with the given PID."""
        try:
            return _psutil_mswindows.kill_process(pid)
        except OSError, err:
            # work around issue #24
            if (pid == 0) and err.errno in (errno.EINVAL, ERROR_INVALID_PARAMETER):
                raise AccessDenied(pid, self._process_name)
            raise

    @wrap_exceptions
    def get_process_username(self, pid):
        """Return the name of the user that owns the process"""
        if pid in (0, 4) or pid == 8 and _WIN2000:
            return 'NT AUTHORITY\\SYSTEM'
        return _psutil_mswindows.get_process_username(pid);

    @wrap_exceptions
    def get_process_create_time(self, pid):
        # special case for kernel process PIDs; return system uptime
        if pid in (0, 4) or pid == 8 and _WIN2000:
            return _UPTIME
        return _psutil_mswindows.get_process_create_time(pid)

    @wrap_exceptions
    def get_cpu_times(self, pid):
        user, system = _psutil_mswindows.get_process_cpu_times(pid)
        return self._cputimes_ntuple(user, system)

    def suspend_process(self, pid):
        return _psutil_mswindows.suspend_process(pid)

    def resume_process(self, pid):
        return _psutil_mswindows.resume_process(pid)

    @wrap_exceptions
    def get_process_cwd(self, pid):
        if pid in (0, 4) or pid == 8 and _WIN2000:
            return ''
        # return a normalized pathname since the native C function appends
        # "\\" at the and of the path
        path = _psutil_mswindows.get_process_cwd(pid)
        return os.path.normpath(path)

    @wrap_exceptions
    def get_open_files(self, pid):
        if pid in (0, 4) or pid == 8 and _WIN2000:
            return []
        retlist = []
        # Filenames come in in native format like:
        # "\Device\HarddiskVolume1\Windows\systemew\file.txt"
        # Convert the first part in the corresponding drive letter
        # (e.g. "C:\") by using Windows's QueryDosDevice()
        raw_file_names = _psutil_mswindows.get_process_open_files(pid)
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

    if _CONNECTIONS_SUPPORT:
        @wrap_exceptions
        def get_connections(self, pid):
            retlist = _psutil_mswindows.get_process_connections(pid)
            return [self._connection_ntuple(*conn) for conn in retlist]
    else:
        def get_connections(self, pid):
            raise NotImplementedError("feature not supported on this Windows "
                                      "version")

