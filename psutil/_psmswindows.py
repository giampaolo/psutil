#!/usr/bin/env python
#
# $Id$
#
# Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Windows platform implementation."""

import errno
import os
import sys
import platform

import _psutil_mswindows
from psutil.error import AccessDenied, NoSuchProcess, TimeoutExpired
from psutil._compat import namedtuple
from psutil._common import *

# Windows specific extended namespace
__extra__all__ = ["ABOVE_NORMAL_PRIORITY_CLASS", "BELOW_NORMAL_PRIORITY_CLASS",
                  "HIGH_PRIORITY_CLASS", "IDLE_PRIORITY_CLASS",
                  "NORMAL_PRIORITY_CLASS", "REALTIME_PRIORITY_CLASS"]


# --- module level constants (gets pushed up to psutil module)

NUM_CPUS = _psutil_mswindows.get_num_cpus()
BOOT_TIME = _psutil_mswindows.get_system_uptime()
_WIN2000 = platform.win32_ver()[0] == '2000'
ERROR_ACCESS_DENIED = 5
WAIT_TIMEOUT = 0x00000102 # 258 in decimal

# process priority constants:
# http://msdn.microsoft.com/en-us/library/ms686219(v=vs.85).aspx
from _psutil_mswindows import (ABOVE_NORMAL_PRIORITY_CLASS,
                               BELOW_NORMAL_PRIORITY_CLASS,
                               HIGH_PRIORITY_CLASS,
                               IDLE_PRIORITY_CLASS,
                               NORMAL_PRIORITY_CLASS,
                               REALTIME_PRIORITY_CLASS,
                               INFINITE)

# --- public functions

def phymem_usage():
    """Physical system memory as a (total, used, free) tuple."""
    all = _psutil_mswindows.get_system_phymem()
    total, free, total_pagef, avail_pagef, total_virt, free_virt, percent = all
    used = total - free
    return ntuple_sysmeminfo(total, used, free, round(percent, 1))

def virtmem_usage():
    """Virtual system memory as a (total, used, free) tuple."""
    all = _psutil_mswindows.get_system_phymem()
    total_virt = all[4]
    free_virt = all[5]
    used = total_virt - free_virt
    percent = usage_percent(used, total_virt, _round=1)
    return ntuple_sysmeminfo(total_virt, used, free_virt, percent)

def get_disk_usage(path):
    """Return disk usage associated with path."""
    try:
        total, free = _psutil_mswindows.get_disk_usage(path)
    except WindowsError, err:
        if not os.path.exists(path):
            raise OSError(errno.ENOENT, "No such file or directory: '%s'" % path)
        raise
    used = total - free
    percent = usage_percent(used, total, _round=1)
    return ntuple_diskinfo(total, used, free, percent)

def disk_partitions(all):
    """Return disk partitions."""
    retlist = []
    drive_letters = _psutil_mswindows.win32_GetLogicalDriveStrings()
    for letter in drive_letters:
        mountpoint = letter
        type = _psutil_mswindows.win32_GetDriveType(letter)
        if not os.path.exists(mountpoint):
            # usually a CD-ROM device with no disk inserted
            mountpoint = ""
        if not all:
            if type not in ('cdrom', 'fixed', 'removable'):
                continue
            if not mountpoint:
                continue
        ntuple = ntuple_partition(letter, mountpoint, type)
        retlist.append(ntuple)
    return retlist


_cputimes_ntuple = namedtuple('cputimes', 'user system idle')

def get_system_cpu_times():
    """Return system CPU times as a named tuple."""
    user, system, idle = 0, 0, 0
    # computes system global times summing each processor value
    for cpu_time in _psutil_mswindows.get_system_cpu_times():
        user += cpu_time[0]
        system += cpu_time[1]
        idle += cpu_time[2]
    return _cputimes_ntuple(user, system, idle)

def get_system_per_cpu_times():
    """Return system per-CPU times as a list of named tuples."""
    ret = []
    for cpu_t in _psutil_mswindows.get_system_cpu_times():
        user, system, idle = cpu_t
        item = _cputimes_ntuple(user, system, idle)
        ret.append(item)
    return ret

get_pid_list = _psutil_mswindows.get_pid_list
pid_exists = _psutil_mswindows.pid_exists
network_io_counters = _psutil_mswindows.get_network_io_counters

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
            if err.errno in (errno.EPERM, errno.EACCES, ERROR_ACCESS_DENIED):
                raise AccessDenied(self.pid, self._process_name)
            if err.errno == errno.ESRCH:
                raise NoSuchProcess(self.pid, self._process_name)
            raise
    return wrapper


class Process(object):
    """Wrapper class around underlying C implementation."""

    __slots__ = ["pid", "_process_name"]

    def __init__(self, pid):
        self.pid = pid
        self._process_name = None


    @wrap_exceptions
    def get_process_name(self):
        """Return process name as a string of limited len (15)."""
        return _psutil_mswindows.get_process_name(self.pid)

    def get_process_exe(self):
        # no such thing as "exe" on Windows; it will maybe be determined
        # later from cmdline[0]
        if not pid_exists(self.pid):
            raise NoSuchProcess(self.pid, self._process_name)
        if self.pid in (0, 4):
            raise AccessDenied(self.pid, self._process_name)
        return ""

    @wrap_exceptions
    def get_process_cmdline(self):
        """Return process cmdline as a list of arguments."""
        return _psutil_mswindows.get_process_cmdline(self.pid)

    @wrap_exceptions
    def get_process_ppid(self):
        """Return process parent pid."""
        return _psutil_mswindows.get_process_ppid(self.pid)

    @wrap_exceptions
    def get_memory_info(self):
        """Returns a tuple or RSS/VMS memory usage in bytes."""
        # special case for 0 (kernel processes) PID
        if self.pid == 0:
            return ntuple_meminfo(0, 0)
        rss, vms = _psutil_mswindows.get_memory_info(self.pid)
        return ntuple_meminfo(rss, vms)

    @wrap_exceptions
    def kill_process(self):
        """Terminates the process with the given PID."""
        return _psutil_mswindows.kill_process(self.pid)

    @wrap_exceptions
    def process_wait(self, timeout=None):
        if timeout is None:
            timeout = INFINITE
        else:
            # WaitForSingleObject() expects time in milliseconds
            timeout = int(timeout * 1000)
        ret = _psutil_mswindows.process_wait(self.pid, timeout)
        if ret == WAIT_TIMEOUT:
            raise TimeoutExpired(self.pid, self._process_name)
        return ret

    @wrap_exceptions
    def get_process_username(self):
        """Return the name of the user that owns the process"""
        if self.pid in (0, 4) or self.pid == 8 and _WIN2000:
            return 'NT AUTHORITY\\SYSTEM'
        return _psutil_mswindows.get_process_username(self.pid);

    @wrap_exceptions
    def get_process_create_time(self):
        # special case for kernel process PIDs; return system boot time
        if self.pid in (0, 4) or self.pid == 8 and _WIN2000:
            return BOOT_TIME
        return _psutil_mswindows.get_process_create_time(self.pid)

    @wrap_exceptions
    def get_process_num_threads(self):
        return _psutil_mswindows.get_process_num_threads(self.pid)

    @wrap_exceptions
    def get_process_threads(self):
        rawlist = _psutil_mswindows.get_process_threads(self.pid)
        retlist = []
        for thread_id, utime, stime in rawlist:
            ntuple = ntuple_thread(thread_id, utime, stime)
            retlist.append(ntuple)
        return retlist

    @wrap_exceptions
    def get_cpu_times(self):
        user, system = _psutil_mswindows.get_process_cpu_times(self.pid)
        return ntuple_cputimes(user, system)

    @wrap_exceptions
    def suspend_process(self):
        return _psutil_mswindows.suspend_process(self.pid)

    @wrap_exceptions
    def resume_process(self):
        return _psutil_mswindows.resume_process(self.pid)

    @wrap_exceptions
    def get_process_cwd(self):
        if self.pid in (0, 4) or self.pid == 8 and _WIN2000:
            raise AccessDenied(self.pid, self._process_name)
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
                driveletter = _psutil_mswindows.win32_QueryDosDevice(rawdrive)
                file = file.replace(rawdrive, driveletter)
                if os.path.isfile(file) and file not in retlist:
                    ntuple = ntuple_openfile(file, -1)
                    retlist.append(ntuple)
        return retlist

    @wrap_exceptions
    def get_connections(self):
        retlist = _psutil_mswindows.get_process_connections(self.pid)
        return [ntuple_connection(*conn) for conn in retlist]

    @wrap_exceptions
    def get_process_nice(self):
        return _psutil_mswindows.get_process_priority(self.pid)

    @wrap_exceptions
    def set_process_nice(self, value):
        return _psutil_mswindows.set_process_priority(self.pid, value)

    @wrap_exceptions
    def get_process_io_counters(self):
        rc, wc, rb, wb =_psutil_mswindows.get_process_io_counters(self.pid)
        return ntuple_io(rc, wc, rb, wb)

    @wrap_exceptions
    def get_process_status(self):
        suspended = _psutil_mswindows.is_process_suspended(self.pid)
        if suspended:
            return STATUS_STOPPED
        else:
            return STATUS_RUNNING
