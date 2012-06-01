#!/usr/bin/env python
#
# $Id$
#
# Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Sun OS Solaris platform implementation."""

import errno
import os
import struct

import _psutil_sunos
import _psutil_posix
import _psposix
from psutil.error import AccessDenied, NoSuchProcess, TimeoutExpired
from psutil._compat import namedtuple
from psutil._common import *


__extra__all__ = []

NUM_CPUS = os.sysconf("SC_NPROCESSORS_ONLN")
BOOT_TIME = _psutil_sunos.get_process_basic_info(0)[3]
_cputimes_ntuple = namedtuple('cputimes', 'user system idle iowait')

disk_io_counters = _psutil_sunos.get_disk_io_counters
get_disk_usage = _psposix.get_disk_usage

def _not_impl(*a, **k):
    raise NotImplementedError

network_io_counters = _not_impl  # TODO
virtmem_usage = _not_impl  # TODO


def phymem_usage():
    """Return physical memory usage statistics as a namedutple including
    total, used, free and percent usage.
    """
    # we could have done this with kstat, but imho this is good enough
    PAGE_SIZE = os.sysconf('SC_PAGE_SIZE')
    total = os.sysconf('SC_PHYS_PAGES')
    total *= PAGE_SIZE
    free = os.sysconf('SC_AVPHYS_PAGES')
    free *= PAGE_SIZE
    used = total - free
    percent = usage_percent(used, total, _round=1)
    return ntuple_sysmeminfo(total, used, free, percent)

def get_pid_list():
    """Returns a list of PIDs currently running on the system."""
    return [int(x) for x in os.listdir('/proc') if x.isdigit()]

def pid_exists(pid):
    """Check for the existence of a unix pid."""
    return _psposix.pid_exists(pid)

def get_system_cpu_times():
    """Return system-wide CPU times as a named tuple"""
    ret = _psutil_sunos.get_system_per_cpu_times()
    return _cputimes_ntuple(*[sum(x) for x in zip(*ret)])

def get_system_per_cpu_times():
    """Return system per-CPU times as a list of named tuples"""
    ret = _psutil_sunos.get_system_per_cpu_times()
    return [_cputimes_ntuple(*x) for x in ret]

def get_system_users():
    """Return currently connected users as a list of namedtuples."""
    retlist = []
    rawlist = _psutil_sunos.get_system_users()
    localhost = (':0.0', ':0')
    for item in rawlist:
        user, tty, hostname, tstamp, user_process = item
        # XXX the underlying C function includes entries about
        # system boot, run level and others.  We might want
        # to use them in the future.
        if not user_process:
            continue
        if hostname in localhost:
            hostname = 'localhost'
        abstty = os.path.join("/dev", tty)
        if os.path.exists(abstty):
            tty = abstty
        nt = ntuple_user(user, tty, hostname, tstamp)
        retlist.append(nt)
    return retlist

def disk_partitions(all=False):
    """Return system disk partitions."""
    # TODO - the filtering logic should be better checked so that
    # it tries to reflect 'df' as much as possible
    retlist = []
    partitions = _psutil_sunos.get_disk_partitions()
    for partition in partitions:
        device, mountpoint, fstype, opts = partition
        if device == 'none':
            device = ''
        if not all:
            if not os.path.isabs(device) \
            or not os.path.exists(device):
                continue
        ntuple = ntuple_partition(device, mountpoint, fstype, opts)
        retlist.append(ntuple)
    return retlist


def wrap_exceptions(callable):
    """Call callable into a try/except clause and translate ENOENT,
    EACCES and EPERM in NoSuchProcess or AccessDenied exceptions.
    """
    def wrapper(self, *args, **kwargs):
        try:
            return callable(self, *args, **kwargs)
        except EnvironmentError, err:
            # ENOENT (no such file or directory) gets raised on open().
            # ESRCH (no such process) can get raised on read() if
            # process is gone in meantime.
            if err.errno in (errno.ENOENT, errno.ESRCH):
                raise NoSuchProcess(self.pid, self._process_name)
            if err.errno in (errno.EPERM, errno.EACCES):
                raise AccessDenied(self.pid, self._process_name)
            raise
    return wrapper


_status_map = {
    _psutil_sunos.SSLEEP : STATUS_SLEEPING,
    _psutil_sunos.SRUN : STATUS_RUNNING,
    _psutil_sunos.SZOMB : STATUS_ZOMBIE,
    _psutil_sunos.SSTOP : STATUS_STOPPED,
    _psutil_sunos.SIDL : STATUS_IDLE,
    _psutil_sunos.SONPROC : STATUS_RUNNING,  # same as run
    _psutil_sunos.SWAIT : STATUS_WAITING,
}


class Process(object):
    """Wrapper class around underlying C implementation."""

    __slots__ = ["pid", "_process_name"]

    def __init__(self, pid):
        self.pid = pid
        self._process_name = None

    @wrap_exceptions
    def get_process_name(self):
        # XXX document max len == 15?
        return _psutil_sunos.get_process_name_and_args(self.pid)[0]

    @wrap_exceptions
    def get_process_exe(self):
        # XXX is this going to be set up later?
        return _psutil_sunos.get_process_name_and_args(self.pid)[0]

    @wrap_exceptions
    def get_process_cmdline(self):
        return _psutil_sunos.get_process_name_and_args(self.pid)[1].split(' ')

    @wrap_exceptions
    def get_process_create_time(self):
        return _psutil_sunos.get_process_basic_info(self.pid)[3]

    @wrap_exceptions
    def get_process_num_threads(self):
        return _psutil_sunos.get_process_basic_info(self.pid)[5]

    @wrap_exceptions
    def get_process_nice(self):
        return _psutil_posix.getpriority(self.pid)

    @wrap_exceptions
    def set_process_nice(self, value):
        return _psutil_posix.setpriority(self.pid, value)

    @wrap_exceptions
    def get_process_ppid(self):
        return _psutil_sunos.get_process_basic_info(self.pid)[0]

    @wrap_exceptions
    def get_process_uids(self):
        real, effective, saved, _, _, _ = _psutil_sunos.get_process_cred(self.pid)
        return ntuple_uids(real, effective, saved)

    @wrap_exceptions
    def get_process_gids(self):
        _, _, _, real, effective, saved = _psutil_sunos.get_process_cred(self.pid)
        return ntuple_uids(real, effective, saved)

    @wrap_exceptions
    def get_cpu_times(self):
        user, system = _psutil_sunos.get_process_cpu_times(self.pid)
        return ntuple_cputimes(user, system)

    def get_process_terminal(self):
        tty = wrap_exceptions(_psutil_sunos.get_process_basic_info(self.pid)[0])
        if tty != _psutil_sunos.PRNODEV:
            for x in (0, 1, 2, 255):
                try:
                    return os.readlink('/proc/%d/path/%d' % (self.pid, x))
                except OSError, err:
                    # XXX - catch EPERM as well?
                    if err.errno != errno.ENOENT:
                        raise

    @wrap_exceptions
    def get_memory_info(self):
        ret = _psutil_sunos.get_process_basic_info(self.pid)
        rss, vms = ret[1] * 1024, ret[2] * 1024
        return ntuple_meminfo(rss, vms)

    @wrap_exceptions
    def get_process_status(self):
        code = _psutil_sunos.get_process_basic_info(self.pid)[6]
        if code in _status_map:
            return _status_map[code]
        return constant(-1, "?")

    @wrap_exceptions
    def get_process_threads(self):
        ret = []
        tids = os.listdir('/proc/%d/lwp' % self.pid)
        for tid in tids:
            if tid.isdigit():  # XXX is this necessary?
                tid = int(tid)
                try:
                    utime, stime = _psutil_sunos.query_process_thread(tid)
                except EnvironmentError, err:
                    # ENOENT == thread gone in meantime
                    if err.errno != errno.ENOENT:
                        raise
                else:
                    nt = ntuple_thread(tid, utime, stime)
                    ret.append(nt)
        return ret

    # TODO this needs to be shared with the Linux implementation
    @wrap_exceptions
    def get_open_files(self):
        retlist = []
        pathdir = '/proc/%d/path' % self.pid
        for fd in os.listdir('/proc/%d/fd' % self.pid):
            path = os.path.join(pathdir, fd)
            if os.path.islink(path):
                try:
                    file = os.readlink(path)
                except OSError, err:
                    # ENOENT == file gone in meantime
                    if err.errno != errno.ENOENT:
                        raise
                else:
                    if os.path.isfile(file):
                        retlist.append(ntuple_openfile(file, int(fd)))
        return retlist

    # TODO
    def get_connections(self, kind='inet'):
        raise NotImplementedError()

    # TODO
    @wrap_exceptions
    def get_process_io_counters(self):
        raise NotImplementedError()

    # TODO
    @wrap_exceptions
    def get_memory_maps(self):
        raise NotImplementedError()

    @wrap_exceptions
    def process_wait(self, timeout=None):
        try:
            return _psposix.wait_pid(self.pid, timeout)
        except TimeoutExpired:
            raise TimeoutExpired(self.pid, self._process_name)
