#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Sun OS Solaris platform implementation."""

import errno
import os
import struct
import subprocess
import socket

import _psutil_sunos
import _psutil_posix
from psutil import _psposix
from psutil._error import AccessDenied, NoSuchProcess, TimeoutExpired
from psutil._compat import namedtuple, PY3
from psutil._common import *


__extra__all__ = ["CONN_IDLE", "CONN_BOUND"]

PAGE_SIZE = os.sysconf('SC_PAGE_SIZE')
NUM_CPUS = os.sysconf("SC_NPROCESSORS_ONLN")
BOOT_TIME = _psutil_sunos.get_process_basic_info(0)[3]
TOTAL_PHYMEM = os.sysconf('SC_PHYS_PAGES') * PAGE_SIZE

CONN_IDLE = constant(11, "IDLE")
CONN_BOUND = constant(12, "BOUND")

_PAGESIZE = os.sysconf("SC_PAGE_SIZE")
_cputimes_ntuple = namedtuple('cputimes', 'user system idle iowait')

disk_io_counters = _psutil_sunos.get_disk_io_counters
net_io_counters = _psutil_sunos.get_net_io_counters
get_disk_usage = _psposix.get_disk_usage
get_system_boot_time = lambda: _psutil_sunos.get_process_basic_info(0)[3]

nt_virtmem_info = namedtuple('vmem', ' '.join([
    # all platforms
    'total', 'available', 'percent', 'used', 'free']))

def virtual_memory():
    # we could have done this with kstat, but imho this is good enough
    total = os.sysconf('SC_PHYS_PAGES') * PAGE_SIZE
    # note: there's no difference on Solaris
    free = avail = os.sysconf('SC_AVPHYS_PAGES') * PAGE_SIZE
    used = total - free
    percent = usage_percent(used, total, _round=1)
    return nt_virtmem_info(total, avail, percent, used, free)

def swap_memory():
    sin, sout = _psutil_sunos.get_swap_mem()

    # XXX
    # we are supposed to get total/free by doing so:
    # http://cvs.opensolaris.org/source/xref/onnv/onnv-gate/usr/src/cmd/swap/swap.c
    # ...nevertheless I can't manage to obtain the same numbers as 'swap'
    # cmdline utility, so let's parse its output (sigh!)
    p = subprocess.Popen(['swap', '-l', '-k'], stdout=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if PY3:
        stdout = stdout.decode(sys.stdout.encoding)
    if p.returncode != 0:
        raise RuntimeError("'swap -l -k' failed (retcode=%s)" % retcode)

    lines = stdout.strip().split('\n')[1:]
    if not lines:
        raise RuntimeError('no swap device(s) configured')
    total = free = 0
    for line in lines:
        line = line.split()
        t, f = line[-2:]
        t = t.replace('K', '')
        f = f.replace('K', '')
        total += int(int(t) * 1024)
        free += int(int(f) * 1024)
    used = total - free
    percent = usage_percent(used, total, _round=1)
    return nt_swapmeminfo(total, used, free, percent,
                          sin * _PAGESIZE, sout * _PAGESIZE)

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
        # note: the underlying C function includes entries about
        # system boot, run level and others.  We might want
        # to use them in the future.
        if not user_process:
            continue
        if hostname in localhost:
            hostname = 'localhost'
        nt = nt_user(user, tty, hostname, tstamp)
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
            # Differently from, say, Linux, we don't have a list of
            # common fs types so the best we can do, AFAIK, is to
            # filter by filesystem having a total size > 0.
            if not get_disk_usage(mountpoint).total:
                continue
        ntuple = nt_partition(device, mountpoint, fstype, opts)
        retlist.append(ntuple)
    return retlist


def wrap_exceptions(callable):
    """Call callable into a try/except clause and translate ENOENT,
    EACCES and EPERM in NoSuchProcess or AccessDenied exceptions.
    """
    def wrapper(self, *args, **kwargs):
        try:
            return callable(self, *args, **kwargs)
        except EnvironmentError:
            # ENOENT (no such file or directory) gets raised on open().
            # ESRCH (no such process) can get raised on read() if
            # process is gone in meantime.
            err = sys.exc_info()[1]
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

_conn_status_map = {_psutil_sunos.TCPS_ESTABLISHED : CONN_ESTABLISHED,
                    _psutil_sunos.TCPS_SYN_SENT : CONN_SYN_SENT,
                    _psutil_sunos.TCPS_SYN_RCVD : CONN_SYN_RECV,
                    _psutil_sunos.TCPS_FIN_WAIT_1 : CONN_FIN_WAIT1,
                    _psutil_sunos.TCPS_FIN_WAIT_2 : CONN_FIN_WAIT2,
                    _psutil_sunos.TCPS_TIME_WAIT : CONN_TIME_WAIT,
                    _psutil_sunos.TCPS_CLOSED : CONN_CLOSE,
                    _psutil_sunos.TCPS_CLOSE_WAIT : CONN_CLOSE_WAIT,
                    _psutil_sunos.TCPS_LAST_ACK : CONN_LAST_ACK,
                    _psutil_sunos.TCPS_LISTEN : CONN_LISTEN,
                    _psutil_sunos.TCPS_CLOSING : CONN_CLOSING,
                    _psutil_sunos.PSUTIL_CONN_NONE : CONN_NONE,
                    _psutil_sunos.TCPS_IDLE : CONN_IDLE,  # sunos specific
                    _psutil_sunos.TCPS_BOUND : CONN_BOUND,  # sunos specific
                    }


class Process(object):
    """Wrapper class around underlying C implementation."""

    __slots__ = ["pid", "_process_name"]

    def __init__(self, pid):
        self.pid = pid
        self._process_name = None

    @wrap_exceptions
    def get_process_name(self):
        # note: max len == 15
        return _psutil_sunos.get_process_name_and_args(self.pid)[0]

    @wrap_exceptions
    def get_process_exe(self):
        # Will be guess later from cmdline but we want to explicitly
        # invoke cmdline here in order to get an AccessDenied
        # exception if the user has not enough privileges.
        self.get_process_cmdline()
        return ""

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
        # For some reason getpriority(3) return ESRCH (no such process)
        # for certain low-pid processes, no matter what (even as root).
        # The process actually exists though, as it has a name,
        # creation time, etc.
        # The best thing we can do here appears to be raising AD.
        # Note: tested on Solaris 11; on Open Solaris 5 everything is
        # fine.
        try:
            return _psutil_posix.getpriority(self.pid)
        except EnvironmentError:
            err = sys.exc_info()[1]
            if err.errno in (errno.ENOENT, errno.ESRCH):
                if pid_exists(self.pid):
                    raise AccessDenied(self.pid, self._process_name)
            raise

    @wrap_exceptions
    def set_process_nice(self, value):
        if self.pid in (2, 3):
            # Special case PIDs: internally setpriority(3) return ESRCH
            # (no such process), no matter what.
            # The process actually exists though, as it has a name,
            # creation time, etc.
            raise AccessDenied(self.pid, self._process_name)
        return _psutil_posix.setpriority(self.pid, value)

    @wrap_exceptions
    def get_process_ppid(self):
        return _psutil_sunos.get_process_basic_info(self.pid)[0]

    @wrap_exceptions
    def get_process_uids(self):
        real, effective, saved, _, _, _ = _psutil_sunos.get_process_cred(self.pid)
        return nt_uids(real, effective, saved)

    @wrap_exceptions
    def get_process_gids(self):
        _, _, _, real, effective, saved = _psutil_sunos.get_process_cred(self.pid)
        return nt_uids(real, effective, saved)

    @wrap_exceptions
    def get_cpu_times(self):
        user, system = _psutil_sunos.get_process_cpu_times(self.pid)
        return nt_cputimes(user, system)

    @wrap_exceptions
    def get_process_terminal(self):
        hit_enoent = False
        tty = wrap_exceptions(_psutil_sunos.get_process_basic_info(self.pid)[0])
        if tty != _psutil_sunos.PRNODEV:
            for x in (0, 1, 2, 255):
                try:
                    return os.readlink('/proc/%d/path/%d' % (self.pid, x))
                except OSError:
                    err = sys.exc_info()[1]
                    if err.errno == errno.ENOENT:
                        hit_enoent = True
                        continue
                    raise
        if hit_enoent:
            # raise NSP if the process disappeared on us
            os.stat('/proc/%s' % self.pid)

    @wrap_exceptions
    def get_process_cwd(self):
        # /proc/PID/path/cwd may not be resolved by readlink() even if
        # it exists (ls shows it). If that's the case and the process
        # is still alive return None (we can return None also on BSD).
        # Reference: http://goo.gl/55XgO
        try:
            return os.readlink("/proc/%s/path/cwd" % self.pid)
        except OSError:
            err = sys.exc_info()[1]
            if err.errno == errno.ENOENT:
                os.stat("/proc/%s" % self.pid)
                return None
            raise

    @wrap_exceptions
    def get_memory_info(self):
        ret = _psutil_sunos.get_process_basic_info(self.pid)
        rss, vms = ret[1] * 1024, ret[2] * 1024
        return nt_meminfo(rss, vms)

    # it seems Solaris uses rss and vms only
    get_ext_memory_info = get_memory_info

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
        hit_enoent = False
        for tid in tids:
            tid = int(tid)
            try:
                utime, stime = _psutil_sunos.query_process_thread(self.pid, tid)
            except EnvironmentError:
                # ENOENT == thread gone in meantime
                err = sys.exc_info()[1]
                if err.errno == errno.ENOENT:
                    hit_enoent = True
                    continue
                raise
            else:
                nt = nt_thread(tid, utime, stime)
                ret.append(nt)
        if hit_enoent:
            # raise NSP if the process disappeared on us
            os.stat('/proc/%s' % self.pid)
        return ret

    @wrap_exceptions
    def get_open_files(self):
        retlist = []
        hit_enoent = False
        pathdir = '/proc/%d/path' % self.pid
        for fd in os.listdir('/proc/%d/fd' % self.pid):
            path = os.path.join(pathdir, fd)
            if os.path.islink(path):
                try:
                    file = os.readlink(path)
                except OSError:
                    # ENOENT == file which is gone in the meantime
                    err = sys.exc_info()[1]
                    if err.errno == errno.ENOENT:
                        hit_enoent = True
                        continue
                    raise
                else:
                    if isfile_strict(file):
                        retlist.append(nt_openfile(file, int(fd)))
        if hit_enoent:
            # raise NSP if the process disappeared on us
            os.stat('/proc/%s' % self.pid)
        return retlist

    def _get_unix_sockets(self, pid):
        """Get UNIX sockets used by process by parsing 'pfiles' output."""
        # TODO: rewrite this in C (...but the damn netstat source code
        # does not include this part! Argh!!)
        cmd = "pfiles %s" % pid
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if PY3:
            stdout, stderr = [x.decode(sys.stdout.encoding)
                              for x in (stdout, stderr)]
        if p.returncode != 0:
            if 'permission denied' in stderr.lower():
                raise AccessDenied(self.pid, self._process_name)
            if 'no such process' in stderr.lower():
                raise NoSuchProcess(self.pid, self._process_name)
            raise RuntimeError("%r command error\n%s" % (cmd, stderr))

        lines = stdout.split('\n')[2:]
        for i, line in enumerate(lines):
            line = line.lstrip()
            if line.startswith('sockname: AF_UNIX'):
                path = line.split(' ', 2)[2]
                type = lines[i-2].strip()
                if type == 'SOCK_STREAM':
                    type = socket.SOCK_STREAM
                elif type == 'SOCK_DGRAM':
                    type = socket.SOCK_DGRAM
                else:
                    type = -1
                yield (-1, socket.AF_UNIX, type, path, "", CONN_NONE)

    @wrap_exceptions
    def get_connections(self, kind='inet'):
        if kind not in conn_tmap:
            raise ValueError("invalid %r kind argument; choose between %s"
                             % (kind, ', '.join([repr(x) for x in conn_tmap])))
        families, types = conn_tmap[kind]
        rawlist = _psutil_sunos.get_process_connections(self.pid, families, types)
        # The underlying C implementation retrieves all OS connections
        # and filters them by PID.  At this point we can't tell whether
        # an empty list means there were no connections for process or
        # process is no longer active so we force NSP in case the PID
        # is no longer there.
        if not rawlist:
            os.stat('/proc/%s' % self.pid)  # will raise NSP if process is gone

        ret = []
        for item in rawlist:
            fd, fam, type, laddr, raddr, status = item
            if fam not in families:
                continue
            if type not in types:
                continue
            status = _conn_status_map[status]
            nt = nt_connection(fd, fam, type, laddr, raddr, status)
            ret.append(nt)

        # UNIX sockets
        if socket.AF_UNIX in families:
            ret.extend([nt_connection(*conn) for conn in \
                        self._get_unix_sockets(self.pid)])
        return ret

    nt_mmap_grouped = namedtuple('mmap', 'path rss anon locked')
    nt_mmap_ext = namedtuple('mmap', 'addr perms path rss anon locked')

    @wrap_exceptions
    def get_memory_maps(self):
        def toaddr(start, end):
            return '%s-%s' % (hex(start)[2:].strip('L'), hex(end)[2:].strip('L'))

        retlist = []
        rawlist = _psutil_sunos.get_process_memory_maps(self.pid)
        hit_enoent = False
        for item in rawlist:
            addr, addrsize, perm, name, rss, anon, locked = item
            addr = toaddr(addr, addrsize)
            if not name.startswith('['):
                try:
                    name = os.readlink('/proc/%s/path/%s' % (self.pid, name))
                except OSError:
                    err = sys.exc_info()[1]
                    if err.errno == errno.ENOENT:
                        # sometimes the link may not be resolved by
                        # readlink() even if it exists (ls shows it).
                        # If that's the case we just return the
                        # unresolved link path.
                        # This seems an incosistency with /proc similar
                        # to: http://goo.gl/55XgO
                        name = '/proc/%s/path/%s' % (self.pid, name)
                        hit_enoent = True
                    else:
                        raise
            retlist.append((addr, perm, name, rss, anon, locked))
        if hit_enoent:
            # raise NSP if the process disappeared on us
            os.stat('/proc/%s' % self.pid)
        return retlist

    @wrap_exceptions
    def get_num_fds(self):
       return len(os.listdir("/proc/%s/fd" % self.pid))

    @wrap_exceptions
    def get_num_ctx_switches(self):
        return nt_ctxsw(*_psutil_sunos.get_process_num_ctx_switches(self.pid))

    @wrap_exceptions
    def process_wait(self, timeout=None):
        try:
            return _psposix.wait_pid(self.pid, timeout)
        except TimeoutExpired:
            raise TimeoutExpired(self.pid, self._process_name)
