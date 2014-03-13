#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""FreeBSD platform implementation."""

import errno
import os
import sys

from psutil import _common
from psutil import _psposix
from psutil._common import conn_tmap, usage_percent
from psutil._compat import namedtuple, wraps
import _psutil_bsd as cext
import _psutil_posix


__extra__all__ = []

# --- constants

PROC_STATUSES = {
    cext.SSTOP: _common.STATUS_STOPPED,
    cext.SSLEEP: _common.STATUS_SLEEPING,
    cext.SRUN: _common.STATUS_RUNNING,
    cext.SIDL: _common.STATUS_IDLE,
    cext.SWAIT: _common.STATUS_WAITING,
    cext.SLOCK: _common.STATUS_LOCKED,
    cext.SZOMB: _common.STATUS_ZOMBIE,
}

TCP_STATUSES = {
    cext.TCPS_ESTABLISHED: _common.CONN_ESTABLISHED,
    cext.TCPS_SYN_SENT: _common.CONN_SYN_SENT,
    cext.TCPS_SYN_RECEIVED: _common.CONN_SYN_RECV,
    cext.TCPS_FIN_WAIT_1: _common.CONN_FIN_WAIT1,
    cext.TCPS_FIN_WAIT_2: _common.CONN_FIN_WAIT2,
    cext.TCPS_TIME_WAIT: _common.CONN_TIME_WAIT,
    cext.TCPS_CLOSED: _common.CONN_CLOSE,
    cext.TCPS_CLOSE_WAIT: _common.CONN_CLOSE_WAIT,
    cext.TCPS_LAST_ACK: _common.CONN_LAST_ACK,
    cext.TCPS_LISTEN: _common.CONN_LISTEN,
    cext.TCPS_CLOSING: _common.CONN_CLOSING,
    cext.PSUTIL_CONN_NONE: _common.CONN_NONE,
}

PAGESIZE = os.sysconf("SC_PAGE_SIZE")

# extend base mem ntuple with BSD-specific memory metrics
svmem = namedtuple(
    'svmem', ['total', 'available', 'percent', 'used', 'free',
              'active', 'inactive', 'buffers', 'cached', 'shared', 'wired'])
scputimes = namedtuple(
    'scputimes', ['user', 'nice', 'system', 'idle', 'irq'])
pextmem = namedtuple('pextmem', ['rss', 'vms', 'text', 'data', 'stack'])
pmmap_grouped = namedtuple(
    'pmmap_grouped', 'path rss, private, ref_count, shadow_count')
pmmap_ext = namedtuple(
    'pmmap_ext', 'addr, perms path rss, private, ref_count, shadow_count')

# set later from __init__.py
NoSuchProcess = None
AccessDenied = None
TimeoutExpired = None


def virtual_memory():
    """System virtual memory as a namedutple."""
    mem = cext.virtual_mem()
    total, free, active, inactive, wired, cached, buffers, shared = mem
    avail = inactive + cached + free
    used = active + wired + cached
    percent = usage_percent((total - avail), total, _round=1)
    return svmem(total, avail, percent, used, free,
                 active, inactive, buffers, cached, shared, wired)


def swap_memory():
    """System swap memory as (total, used, free, sin, sout) namedtuple."""
    total, used, free, sin, sout = [x * PAGESIZE for x in cext.swap_mem()]
    percent = usage_percent(used, total, _round=1)
    return _common.sswap(total, used, free, percent, sin, sout)


def cpu_times():
    """Return system per-CPU times as a named tuple"""
    user, nice, system, idle, irq = cext.cpu_times()
    return scputimes(user, nice, system, idle, irq)


if hasattr(cext, "per_cpu_times"):
    def per_cpu_times():
        """Return system CPU times as a named tuple"""
        ret = []
        for cpu_t in cext.per_cpu_times():
            user, nice, system, idle, irq = cpu_t
            item = scputimes(user, nice, system, idle, irq)
            ret.append(item)
        return ret
else:
    # XXX
    # Ok, this is very dirty.
    # On FreeBSD < 8 we cannot gather per-cpu information, see:
    # http://code.google.com/p/psutil/issues/detail?id=226
    # If num cpus > 1, on first call we return single cpu times to avoid a
    # crash at psutil import time.
    # Next calls will fail with NotImplementedError
    def per_cpu_times():
        if cpu_count_logical() == 1:
            return [cpu_times()]
        if per_cpu_times.__called__:
            raise NotImplementedError("supported only starting from FreeBSD 8")
        per_cpu_times.__called__ = True
        return [cpu_times()]

    per_cpu_times.__called__ = False


def cpu_count_logical():
    """Return the number of logical CPUs in the system."""
    return cext.cpu_count_logical()


def cpu_count_physical():
    """Return the number of physical CPUs in the system."""
    # From the C module we'll get an XML string similar to this:
    # http://manpages.ubuntu.com/manpages/precise/man4/smp.4freebsd.html
    # We may get None in case "sysctl kern.sched.topology_spec"
    # is not supported on this BSD version, in which case we'll mimic
    # os.cpu_count() and return None.
    s = cext.cpu_count_phys()
    if s is not None:
        # get rid of padding chars appended at the end of the string
        index = s.rfind("</groups>")
        if index != -1:
            s = s[:index + 9]
            if sys.version_info >= (2, 5):
                import xml.etree.ElementTree as ET
                root = ET.fromstring(s)
                return len(root.findall('group/children/group/cpu')) or None
            else:
                s = s[s.find('<children>'):]
                return s.count("<cpu") or None


def boot_time():
    """The system boot time expressed in seconds since the epoch."""
    return cext.boot_time()


def disk_partitions(all=False):
    retlist = []
    partitions = cext.disk_partitions()
    for partition in partitions:
        device, mountpoint, fstype, opts = partition
        if device == 'none':
            device = ''
        if not all:
            if not os.path.isabs(device) or not os.path.exists(device):
                continue
        ntuple = _common.sdiskpart(device, mountpoint, fstype, opts)
        retlist.append(ntuple)
    return retlist


def users():
    retlist = []
    rawlist = cext.users()
    for item in rawlist:
        user, tty, hostname, tstamp = item
        if tty == '~':
            continue  # reboot or shutdown
        nt = _common.suser(user, tty or None, hostname, tstamp)
        retlist.append(nt)
    return retlist


def net_connections(kind):
    if kind not in _common.conn_tmap:
        raise ValueError("invalid %r kind argument; choose between %s"
                        % (kind, ', '.join([repr(x) for x in conn_tmap])))
    families, types = conn_tmap[kind]
    ret = []
    rawlist = cext.net_connections()
    for item in rawlist:
        fd, fam, type, laddr, raddr, status, pid = item
        # TODO: apply filter at C level
        if fam in families and type in types:
            status = TCP_STATUSES[status]
            nt = _common.sconn(fd, fam, type, laddr, raddr, status, pid)
            ret.append(nt)
    return ret


pids = cext.pids
pid_exists = _psposix.pid_exists
disk_usage = _psposix.disk_usage
net_io_counters = cext.net_io_counters
disk_io_counters = cext.disk_io_counters


def wrap_exceptions(fun):
    """Decorator which translates bare OSError exceptions into
    NoSuchProcess and AccessDenied.
    """
    @wraps(fun)
    def wrapper(self, *args, **kwargs):
        try:
            return fun(self, *args, **kwargs)
        except OSError:
            # support for private module import
            if NoSuchProcess is None or AccessDenied is None:
                raise
            err = sys.exc_info()[1]
            if err.errno == errno.ESRCH:
                raise NoSuchProcess(self.pid, self._name)
            if err.errno in (errno.EPERM, errno.EACCES):
                raise AccessDenied(self.pid, self._name)
            raise
    return wrapper


class Process(object):
    """Wrapper class around underlying C implementation."""

    __slots__ = ["pid", "_name"]

    def __init__(self, pid):
        self.pid = pid
        self._name = None

    @wrap_exceptions
    def name(self):
        return cext.proc_name(self.pid)

    @wrap_exceptions
    def exe(self):
        return cext.proc_exe(self.pid)

    @wrap_exceptions
    def cmdline(self):
        return cext.proc_cmdline(self.pid)

    @wrap_exceptions
    def terminal(self):
        tty_nr = cext.proc_tty_nr(self.pid)
        tmap = _psposix._get_terminal_map()
        try:
            return tmap[tty_nr]
        except KeyError:
            return None

    @wrap_exceptions
    def ppid(self):
        return cext.proc_ppid(self.pid)

    @wrap_exceptions
    def uids(self):
        real, effective, saved = cext.proc_uids(self.pid)
        return _common.puids(real, effective, saved)

    @wrap_exceptions
    def gids(self):
        real, effective, saved = cext.proc_gids(self.pid)
        return _common.pgids(real, effective, saved)

    @wrap_exceptions
    def cpu_times(self):
        user, system = cext.proc_cpu_times(self.pid)
        return _common.pcputimes(user, system)

    @wrap_exceptions
    def memory_info(self):
        rss, vms = cext.proc_memory_info(self.pid)[:2]
        return _common.pmem(rss, vms)

    @wrap_exceptions
    def memory_info_ex(self):
        return pextmem(*cext.proc_memory_info(self.pid))

    @wrap_exceptions
    def create_time(self):
        return cext.proc_create_time(self.pid)

    @wrap_exceptions
    def num_threads(self):
        return cext.proc_num_threads(self.pid)

    @wrap_exceptions
    def num_ctx_switches(self):
        return _common.pctxsw(*cext.proc_num_ctx_switches(self.pid))

    @wrap_exceptions
    def threads(self):
        rawlist = cext.proc_threads(self.pid)
        retlist = []
        for thread_id, utime, stime in rawlist:
            ntuple = _common.pthread(thread_id, utime, stime)
            retlist.append(ntuple)
        return retlist

    @wrap_exceptions
    def connections(self, kind='inet'):
        if kind not in conn_tmap:
            raise ValueError("invalid %r kind argument; choose between %s"
                             % (kind, ', '.join([repr(x) for x in conn_tmap])))
        families, types = conn_tmap[kind]
        rawlist = cext.proc_connections(self.pid, families, types)
        ret = []
        for item in rawlist:
            fd, fam, type, laddr, raddr, status = item
            status = TCP_STATUSES[status]
            nt = _common.pconn(fd, fam, type, laddr, raddr, status)
            ret.append(nt)
        return ret

    @wrap_exceptions
    def wait(self, timeout=None):
        try:
            return _psposix.wait_pid(self.pid, timeout)
        except _psposix.TimeoutExpired:
            # support for private module import
            if TimeoutExpired is None:
                raise
            raise TimeoutExpired(timeout, self.pid, self._name)

    @wrap_exceptions
    def nice_get(self):
        return _psutil_posix.getpriority(self.pid)

    @wrap_exceptions
    def nice_set(self, value):
        return _psutil_posix.setpriority(self.pid, value)

    @wrap_exceptions
    def status(self):
        code = cext.proc_status(self.pid)
        if code in PROC_STATUSES:
            return PROC_STATUSES[code]
        # XXX is this legit? will we even ever get here?
        return "?"

    @wrap_exceptions
    def io_counters(self):
        rc, wc, rb, wb = cext.proc_io_counters(self.pid)
        return _common.pio(rc, wc, rb, wb)

    nt_mmap_grouped = namedtuple(
        'mmap', 'path rss, private, ref_count, shadow_count')
    nt_mmap_ext = namedtuple(
        'mmap', 'addr, perms path rss, private, ref_count, shadow_count')

    # FreeBSD < 8 does not support functions based on kinfo_getfile()
    # and kinfo_getvmmap()
    if hasattr(cext, 'proc_open_files'):

        @wrap_exceptions
        def open_files(self):
            """Return files opened by process as a list of namedtuples."""
            rawlist = cext.proc_open_files(self.pid)
            return [_common.popenfile(path, fd) for path, fd in rawlist]

        @wrap_exceptions
        def cwd(self):
            """Return process current working directory."""
            # sometimes we get an empty string, in which case we turn
            # it into None
            return cext.proc_cwd(self.pid) or None

        @wrap_exceptions
        def memory_maps(self):
            return cext.proc_memory_maps(self.pid)

        @wrap_exceptions
        def num_fds(self):
            """Return the number of file descriptors opened by this process."""
            return cext.proc_num_fds(self.pid)

    else:
        def _not_implemented(self):
            raise NotImplementedError("supported only starting from FreeBSD 8")

        open_files = _not_implemented
        proc_cwd = _not_implemented
        memory_maps = _not_implemented
        num_fds = _not_implemented
