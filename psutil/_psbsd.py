# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""FreeBSD and OpenBSD platforms implementation."""

import errno
import functools
import os
import sys
import xml.etree.ElementTree as ET
from collections import namedtuple

from . import _common
from . import _psposix
from . import _psutil_bsd as cext
from . import _psutil_posix as cext_posix
from ._common import conn_tmap
from ._common import sockfam_to_enum
from ._common import socktype_to_enum
from ._common import usage_percent
from ._compat import which


__extra__all__ = []

# --- constants

FREEBSD = sys.platform.startswith("freebsd")
OPENBSD = sys.platform.startswith("openbsd")

if FREEBSD:
    PROC_STATUSES = {
        cext.SIDL: _common.STATUS_IDLE,
        cext.SRUN: _common.STATUS_RUNNING,
        cext.SSLEEP: _common.STATUS_SLEEPING,
        cext.SSTOP: _common.STATUS_STOPPED,
        cext.SZOMB: _common.STATUS_ZOMBIE,
        cext.SWAIT: _common.STATUS_WAITING,
        cext.SLOCK: _common.STATUS_LOCKED,
    }
elif OPENBSD:
    PROC_STATUSES = {
        cext.SIDL: _common.STATUS_IDLE,
        cext.SSLEEP: _common.STATUS_SLEEPING,
        cext.SSTOP: _common.STATUS_STOPPED,
        # According to /usr/include/sys/proc.h SZOMB is unused.
        # test_zombie_process() shows that SDEAD is the right
        # equivalent. Also it appears there's no equivalent of
        # psutil.STATUS_DEAD. SDEAD really means STATUS_ZOMBIE.
        # cext.SZOMB: _common.STATUS_ZOMBIE,
        cext.SDEAD: _common.STATUS_ZOMBIE,
        # From http://www.eecs.harvard.edu/~margo/cs161/videos/proc.h.txt
        # OpenBSD has SRUN and SONPROC: SRUN indicates that a process
        # is runnable but *not* yet running, i.e. is on a run queue.
        # SONPROC indicates that the process is actually executing on
        # a CPU, i.e. it is no longer on a run queue.
        # As such we'll map SRUN to STATUS_WAKING and SONPROC to
        # STATUS_RUNNING
        cext.SRUN: _common.STATUS_WAKING,
        cext.SONPROC: _common.STATUS_RUNNING,
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
AF_LINK = cext_posix.AF_LINK

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
ZombieProcess = None
AccessDenied = None
TimeoutExpired = None


def virtual_memory():
    """System virtual memory as a namedtuple."""
    mem = cext.virtual_mem()
    total, free, active, inactive, wired, cached, buffers, shared = mem
    avail = inactive + cached + free
    used = active + wired + cached
    percent = usage_percent((total - avail), total, _round=1)
    return svmem(total, avail, percent, used, free,
                 active, inactive, buffers, cached, shared, wired)


def swap_memory():
    """System swap memory as (total, used, free, sin, sout) namedtuple."""
    pagesize = 1 if OPENBSD else PAGESIZE
    total, used, free, sin, sout = [x * pagesize for x in cext.swap_mem()]
    percent = usage_percent(used, total, _round=1)
    return _common.sswap(total, used, free, percent, sin, sout)


def cpu_times():
    """Return system per-CPU times as a namedtuple"""
    user, nice, system, idle, irq = cext.cpu_times()
    return scputimes(user, nice, system, idle, irq)


if hasattr(cext, "per_cpu_times"):
    def per_cpu_times():
        """Return system CPU times as a namedtuple"""
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
    # https://github.com/giampaolo/psutil/issues/226
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


if OPENBSD:
    def cpu_count_physical():
        # OpenBSD does not implement this.
        return 1 if cpu_count_logical() == 1 else None
else:
    def cpu_count_physical():
        """Return the number of physical CPUs in the system."""
        # From the C module we'll get an XML string similar to this:
        # http://manpages.ubuntu.com/manpages/precise/man4/smp.4freebsd.html
        # We may get None in case "sysctl kern.sched.topology_spec"
        # is not supported on this BSD version, in which case we'll mimic
        # os.cpu_count() and return None.
        ret = None
        s = cext.cpu_count_phys()
        if s is not None:
            # get rid of padding chars appended at the end of the string
            index = s.rfind("</groups>")
            if index != -1:
                s = s[:index + 9]
                root = ET.fromstring(s)
                try:
                    ret = len(root.findall('group/children/group/cpu')) or None
                finally:
                    # needed otherwise it will memleak
                    root.clear()
        if not ret:
            # If logical CPUs are 1 it's obvious we'll have only 1
            # physical CPU.
            if cpu_count_logical() == 1:
                return 1
        return ret


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
    if OPENBSD:
        ret = []
        for pid in pids():
            try:
                cons = Process(pid).connections(kind)
            except (NoSuchProcess, ZombieProcess):
                continue
            else:
                for conn in cons:
                    conn = list(conn)
                    conn.append(pid)
                    ret.append(_common.sconn(*conn))
        return ret

    if kind not in _common.conn_tmap:
        raise ValueError("invalid %r kind argument; choose between %s"
                         % (kind, ', '.join([repr(x) for x in conn_tmap])))
    families, types = conn_tmap[kind]
    ret = set()
    rawlist = cext.net_connections()
    for item in rawlist:
        fd, fam, type, laddr, raddr, status, pid = item
        # TODO: apply filter at C level
        if fam in families and type in types:
            try:
                status = TCP_STATUSES[status]
            except KeyError:
                # XXX: Not sure why this happens. I saw this occurring
                # with IPv6 sockets opened by 'vim'. Those sockets
                # have a very short lifetime so maybe the kernel
                # can't initialize their status?
                status = TCP_STATUSES[cext.PSUTIL_CONN_NONE]
            fam = sockfam_to_enum(fam)
            type = socktype_to_enum(type)
            nt = _common.sconn(fd, fam, type, laddr, raddr, status, pid)
            ret.add(nt)
    return list(ret)


def net_if_stats():
    """Get NIC stats (isup, duplex, speed, mtu)."""
    names = net_io_counters().keys()
    ret = {}
    for name in names:
        isup, duplex, speed, mtu = cext_posix.net_if_stats(name)
        if hasattr(_common, 'NicDuplex'):
            duplex = _common.NicDuplex(duplex)
        ret[name] = _common.snicstats(isup, duplex, speed, mtu)
    return ret


if OPENBSD:
    def pid_exists(pid):
        exists = _psposix.pid_exists(pid)
        if not exists:
            # We do this because _psposix.pid_exists() lies in case of
            # zombie processes.
            return pid in pids()
        else:
            return True
else:
    pid_exists = _psposix.pid_exists


pids = cext.pids
disk_usage = _psposix.disk_usage
net_io_counters = cext.net_io_counters
disk_io_counters = cext.disk_io_counters
net_if_addrs = cext_posix.net_if_addrs


def wrap_exceptions(fun):
    """Decorator which translates bare OSError exceptions into
    NoSuchProcess and AccessDenied.
    """
    @functools.wraps(fun)
    def wrapper(self, *args, **kwargs):
        try:
            return fun(self, *args, **kwargs)
        except OSError as err:
            # support for private module import
            if (NoSuchProcess is None or AccessDenied is None or
                    ZombieProcess is None):
                raise
            if err.errno == errno.ESRCH:
                if not pid_exists(self.pid):
                    raise NoSuchProcess(self.pid, self._name)
                else:
                    raise ZombieProcess(self.pid, self._name, self._ppid)
            if err.errno in (errno.EPERM, errno.EACCES):
                raise AccessDenied(self.pid, self._name)
            raise
    return wrapper


class Process(object):
    """Wrapper class around underlying C implementation."""

    __slots__ = ["pid", "_name", "_ppid"]

    def __init__(self, pid):
        self.pid = pid
        self._name = None
        self._ppid = None

    @wrap_exceptions
    def name(self):
        return cext.proc_name(self.pid)

    @wrap_exceptions
    def exe(self):
        if FREEBSD:
            return cext.proc_exe(self.pid)
        else:
            # exe cannot be determined on OpenBSD; references:
            # https://chromium.googlesource.com/chromium/src/base/+/
            #     master/base_paths_posix.cc
            # We try our best guess by using which against the first
            # cmdline arg (may return None).
            cmdline = self.cmdline()
            if cmdline:
                return which(cmdline[0])
            else:
                return ""

    @wrap_exceptions
    def cmdline(self):
        if OPENBSD and self.pid == 0:
            return None  # ...else it crashes
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
        if hasattr(cext, "proc_num_threads"):
            # FreeBSD
            return cext.proc_num_threads(self.pid)
        else:
            return len(self.threads())

    @wrap_exceptions
    def num_ctx_switches(self):
        return _common.pctxsw(*cext.proc_num_ctx_switches(self.pid))

    @wrap_exceptions
    def threads(self):
        # Note: on OpenSBD this (/dev/mem) requires root access.
        rawlist = cext.proc_threads(self.pid)
        retlist = []
        for thread_id, utime, stime in rawlist:
            ntuple = _common.pthread(thread_id, utime, stime)
            retlist.append(ntuple)
        if OPENBSD:
            # On OpenBSD the underlying C function does not raise NSP
            # in case the process is gone (and the returned list may
            # incomplete).
            self.name()  # raise NSP if the process disappeared on us
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
            fam = sockfam_to_enum(fam)
            type = socktype_to_enum(type)
            status = TCP_STATUSES[status]
            nt = _common.pconn(fd, fam, type, laddr, raddr, status)
            ret.append(nt)
        if OPENBSD:
            # On OpenBSD the underlying C function does not raise NSP
            # in case the process is gone (and the returned list may
            # incomplete).
            self.name()  # raise NSP if the process disappeared on us
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
        return cext_posix.getpriority(self.pid)

    @wrap_exceptions
    def nice_set(self, value):
        return cext_posix.setpriority(self.pid, value)

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
            if OPENBSD and self.pid == 0:
                return None  # ...else raises EINVAL
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

    if FREEBSD:
        @wrap_exceptions
        def cpu_affinity_get(self):
            return cext.proc_cpu_affinity_get(self.pid)

        @wrap_exceptions
        def cpu_affinity_set(self, cpus):
            # Pre-emptively check if CPUs are valid because the C
            # function has a weird behavior in case of invalid CPUs,
            # see: https://github.com/giampaolo/psutil/issues/586
            allcpus = tuple(range(len(per_cpu_times())))
            for cpu in cpus:
                if cpu not in allcpus:
                    raise ValueError("invalid CPU #%i (choose between %s)"
                                     % (cpu, allcpus))
            try:
                cext.proc_cpu_affinity_set(self.pid, cpus)
            except OSError as err:
                # 'man cpuset_setaffinity' about EDEADLK:
                # <<the call would leave a thread without a valid CPU to run
                # on because the set does not overlap with the thread's
                # anonymous mask>>
                if err.errno in (errno.EINVAL, errno.EDEADLK):
                    for cpu in cpus:
                        if cpu not in allcpus:
                            raise ValueError(
                                "invalid CPU #%i (choose between %s)" % (
                                    cpu, allcpus))
                raise
