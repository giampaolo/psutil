#!/usr/bin/env python
#
# $Id$
#

import errno
import os

try:
    from collections import namedtuple
except ImportError:
    from psutil.compat import namedtuple  # python < 2.6

import _psutil_osx
import _psposix
from psutil.error import AccessDenied, NoSuchProcess

# --- constants

NUM_CPUS = _psutil_osx.get_num_cpus()
TOTAL_PHYMEM = _psutil_osx.get_total_phymem()

# --- functions

def avail_phymem():
    "Return the amount of physical memory available on the system, in bytes."
    return _psutil_osx.get_avail_phymem()

def used_phymem():
    "Return the amount of physical memory currently in use on the system, in bytes."
    return TOTAL_PHYMEM - _psutil_osx.get_avail_phymem()

def total_virtmem():
    "Return the amount of total virtual memory available on the system, in bytes."
    return _psutil_osx.get_total_virtmem()

def avail_virtmem():
    "Return the amount of virtual memory currently in use on the system, in bytes."
    return _psutil_osx.get_avail_virtmem()

def used_virtmem():
    """Return the amount of used memory currently in use on the system, in bytes."""
    return _psutil_osx.get_total_virtmem() - _psutil_osx.get_avail_virtmem()

def get_system_cpu_times():
    """Return a dict representing the following CPU times:
    user, nice, system, idle."""
    values = _psutil_osx.get_system_cpu_times()
    return dict(user=values[0], nice=values[1], system=values[2], idle=values[3])

def get_pid_list():
    """Returns a list of PIDs currently running on the system."""
    return _psutil_osx.get_pid_list()

def pid_exists(pid):
    """Check For the existence of a unix pid."""
    return _psposix.pid_exists(pid)

# --- decorator

def wrap_exceptions(callable):
    """Call callable into a try/except clause so that if an
    OSError EPERM exception is raised we translate it into
    psutil.AccessDenied.
    """
    def wrapper(self, *args, **kwargs):
        try:
            return callable(self, *args, **kwargs)
        except OSError, err:
            if err.errno == errno.ESRCH:
                raise NoSuchProcess(self.pid, self._process_name)
            if err.errno == errno.EPERM:
                raise AccessDenied(self.pid, self._process_name)
            raise
    return wrapper


class OSXProcess(object):
    """Wrapper class around underlying C implementation."""

    _meminfo_ntuple = namedtuple('meminfo', 'rss vms')
    _cputimes_ntuple = namedtuple('cputimes', 'user system')
    __slots__ = ["pid", "_process_name"]

    def __init__(self, pid):
        self.pid = pid
        self._process_name = None

    @wrap_exceptions
    def get_process_info(self):
        """Returns a tuple that can be passed to the psutil.ProcessInfo class
        constructor.
        """
        info_tuple = _psutil_osx.get_process_info(self.pid)
        pid, ppid, name, exe, cmdline, uid, gid = info_tuple
        # on OSX, "p_comm" gets truncated to 19 bytes; if it matches
        # the first part of the cmdline we return that one instead 
        # because it's usually more clear.
        # Examples are "sshd" vs. "sshd: root@ttyp1" and "sendmail" 
        # vs. "sendmail: accepting connections".
        # ps aux deals with this by returning both names as a
        # "name (longer name)" string in the COMMAND column.
        if cmdline:
            extended_name = os.path.basename(cmdline[0])
            if extended_name.startswith(name):
                name = extended_name
        self._process_name = name
        return (pid, ppid, name, exe, cmdline, uid, gid)

    @wrap_exceptions
    def get_memory_info(self):
        """Return a tuple with the process' RSS and VMS size."""
        rss, vms = _psutil_osx.get_memory_info(self.pid)
        return self._meminfo_ntuple(rss, vms)

    @wrap_exceptions
    def get_cpu_times(self):
        user, system = _psutil_osx.get_process_cpu_times(self.pid)
        return self._cputimes_ntuple(user, system)

    @wrap_exceptions
    def get_process_create_time(self):
        """Return the start time of the process as a number of seconds since
        the epoch."""
        return _psutil_osx.get_process_create_time(self.pid)

    def get_open_files(self):
        """Return files opened by process by parsing lsof output."""
        lsof = _psposix.LsofParser(self.pid, self._process_name)
        return lsof.get_process_open_files()

    def get_connections(self):
        """Return etwork connections opened by a process as a list of
        namedtuples."""
        lsof = _psposix.LsofParser(self.pid, self._process_name)
        return lsof.get_process_connections()

PlatformProcess = OSXProcess

