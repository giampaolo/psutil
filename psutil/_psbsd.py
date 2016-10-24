# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""FreeBSD, OpenBSD and NetBSD platforms implementation."""

import contextlib
import errno
import functools
import os
import xml.etree.ElementTree as ET
from collections import namedtuple

from . import _common
from . import _psposix
from . import _psutil_bsd as cext
from . import _psutil_posix as cext_posix
from ._common import conn_tmap
from ._common import FREEBSD
from ._common import NETBSD
from ._common import OPENBSD
from ._common import sockfam_to_enum
from ._common import socktype_to_enum
from ._common import usage_percent
from ._compat import which

__extra__all__ = []


# =====================================================================
# --- constants
# =====================================================================


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
elif OPENBSD or NETBSD:
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
        cext.SZOMB: _common.STATUS_ZOMBIE,
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
elif NETBSD:
    PROC_STATUSES = {
        cext.SIDL: _common.STATUS_IDLE,
        cext.SACTIVE: _common.STATUS_RUNNING,
        cext.SDYING: _common.STATUS_ZOMBIE,
        cext.SSTOP: _common.STATUS_STOPPED,
        cext.SZOMB: _common.STATUS_ZOMBIE,
        cext.SDEAD: _common.STATUS_DEAD,
        cext.SSUSPENDED: _common.STATUS_SUSPENDED,  # unique to NetBSD
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

if NETBSD:
    PAGESIZE = os.sysconf("SC_PAGESIZE")
else:
    PAGESIZE = os.sysconf("SC_PAGE_SIZE")
AF_LINK = cext_posix.AF_LINK


# =====================================================================
# --- named tuples
# =====================================================================


# extend base mem ntuple with BSD-specific memory metrics
svmem = namedtuple(
    'svmem', ['total', 'available', 'percent', 'used', 'free',
              'active', 'inactive', 'buffers', 'cached', 'shared', 'wired'])
scputimes = namedtuple(
    'scputimes', ['user', 'nice', 'system', 'idle', 'irq'])
pmem = namedtuple('pmem', ['rss', 'vms', 'text', 'data', 'stack'])
pfullmem = pmem
pcputimes = namedtuple('pcputimes',
                       ['user', 'system', 'children_user', 'children_system'])
pmmap_grouped = namedtuple(
    'pmmap_grouped', 'path rss, private, ref_count, shadow_count')
pmmap_ext = namedtuple(
    'pmmap_ext', 'addr, perms path rss, private, ref_count, shadow_count')
if FREEBSD:
    sdiskio = namedtuple('sdiskio', ['read_count', 'write_count',
                                     'read_bytes', 'write_bytes',
                                     'read_time', 'write_time',
                                     'busy_time'])
else:
    sdiskio = namedtuple('sdiskio', ['read_count', 'write_count',
                                     'read_bytes', 'write_bytes'])


# =====================================================================
# --- exceptions
# =====================================================================


# these get overwritten on "import psutil" from the __init__.py file
NoSuchProcess = None
ZombieProcess = None
AccessDenied = None
TimeoutExpired = None


# =====================================================================
# --- memory
# =====================================================================


def virtual_memory():
    """System virtual memory as a namedtuple."""
    mem = cext.virtual_mem()
    total, free, active, inactive, wired, cached, buffers, shared = mem
    if NETBSD:
        # On NetBSD buffers and shared mem is determined via /proc.
        # The C ext set them to 0.
        with open('/proc/meminfo', 'rb') as f:
            for line in f:
                if line.startswith(b'Buffers:'):
                    buffers = int(line.split()[1]) * 1024
                elif line.startswith(b'MemShared:'):
                    shared = int(line.split()[1]) * 1024
    avail = inactive + cached + free
    used = active + wired + cached
    percent = usage_percent((total - avail), total, _round=1)
    return svmem(total, avail, percent, used, free,
                 active, inactive, buffers, cached, shared, wired)


def swap_memory():
    """System swap memory as (total, used, free, sin, sout) namedtuple."""
    total, used, free, sin, sout = cext.swap_mem()
    percent = usage_percent(used, total, _round=1)
    return _common.sswap(total, used, free, percent, sin, sout)


# =====================================================================
# --- CPU
# =====================================================================


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


if OPENBSD or NETBSD:
    def cpu_count_physical():
        # OpenBSD and NetBSD do not implement this.
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


def cpu_stats():
    if FREEBSD:
        # Note: the C ext is returning some metrics we are not exposing:
        # traps.
        ctxsw, intrs, soft_intrs, syscalls, traps = cext.cpu_stats()
    elif NETBSD:
        # XXX
        # Note about intrs: the C extension returns 0. intrs
        # can be determined via /proc/stat; it has the same value as
        # soft_intrs thought so the kernel is faking it (?).
        #
        # Note about syscalls: the C extension always sets it to 0 (?).
        #
        # Note: the C ext is returning some metrics we are not exposing:
        # traps, faults and forks.
        ctxsw, intrs, soft_intrs, syscalls, traps, faults, forks = \
            cext.cpu_stats()
        with open('/proc/stat', 'rb') as f:
            for line in f:
                if line.startswith(b'intr'):
                    intrs = int(line.split()[1])
    elif OPENBSD:
        # Note: the C ext is returning some metrics we are not exposing:
        # traps, faults and forks.
        ctxsw, intrs, soft_intrs, syscalls, traps, faults, forks = \
            cext.cpu_stats()
    return _common.scpustats(ctxsw, intrs, soft_intrs, syscalls)


# =====================================================================
# --- disks
# =====================================================================


def disk_partitions(all=False):
    """Return mounted disk partitions as a list of namedtuples.
    'all' argument is ignored, see:
    https://github.com/giampaolo/psutil/issues/906
    """
    retlist = []
    partitions = cext.disk_partitions()
    for partition in partitions:
        device, mountpoint, fstype, opts = partition
        ntuple = _common.sdiskpart(device, mountpoint, fstype, opts)
        retlist.append(ntuple)
    return retlist


disk_usage = _psposix.disk_usage
disk_io_counters = cext.disk_io_counters


# =====================================================================
# --- network
# =====================================================================


net_io_counters = cext.net_io_counters
net_if_addrs = cext_posix.net_if_addrs


def net_if_stats():
    """Get NIC stats (isup, duplex, speed, mtu)."""
    names = net_io_counters().keys()
    ret = {}
    for name in names:
        mtu = cext_posix.net_if_mtu(name)
        isup = cext_posix.net_if_flags(name)
        duplex, speed = cext_posix.net_if_duplex_speed(name)
        if hasattr(_common, 'NicDuplex'):
            duplex = _common.NicDuplex(duplex)
        ret[name] = _common.snicstats(isup, duplex, speed, mtu)
    return ret


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


# =====================================================================
#  --- other system functions
# =====================================================================


def boot_time():
    """The system boot time expressed in seconds since the epoch."""
    return cext.boot_time()


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


# =====================================================================
# --- processes
# =====================================================================


pids = cext.pids

if OPENBSD or NETBSD:
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


def wrap_exceptions(fun):
    """Decorator which translates bare OSError exceptions into
    NoSuchProcess and AccessDenied.
    """
    @functools.wraps(fun)
    def wrapper(self, *args, **kwargs):
        try:
            return fun(self, *args, **kwargs)
        except OSError as err:
            if self.pid == 0:
                if 0 in pids():
                    raise AccessDenied(self.pid, self._name)
                else:
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


@contextlib.contextmanager
def wrap_exceptions_procfs(inst):
    try:
        yield
    except EnvironmentError as err:
        # ENOENT (no such file or directory) gets raised on open().
        # ESRCH (no such process) can get raised on read() if
        # process is gone in meantime.
        if err.errno in (errno.ENOENT, errno.ESRCH):
            if not pid_exists(inst.pid):
                raise NoSuchProcess(inst.pid, inst._name)
            else:
                raise ZombieProcess(inst.pid, inst._name, inst._ppid)
        if err.errno in (errno.EPERM, errno.EACCES):
            raise AccessDenied(inst.pid, inst._name)
        raise


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
        elif NETBSD:
            if self.pid == 0:
                # /proc/0 dir exists but /proc/0/exe doesn't
                return ""
            with wrap_exceptions_procfs(self):
                return os.readlink("/proc/%s/exe" % self.pid)
        else:
            # OpenBSD: exe cannot be determined; references:
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
            return []  # ...else it crashes
        elif NETBSD:
            # XXX - most of the times the underlying sysctl() call on Net
            # and Open BSD returns a truncated string.
            # Also /proc/pid/cmdline behaves the same so it looks
            # like this is a kernel bug.
            try:
                return cext.proc_cmdline(self.pid)
            except OSError as err:
                if err.errno == errno.EINVAL:
                    if not pid_exists(self.pid):
                        raise NoSuchProcess(self.pid, self._name)
                    else:
                        raise ZombieProcess(self.pid, self._name, self._ppid)
                else:
                    raise
        else:
            return cext.proc_cmdline(self.pid)

    @wrap_exceptions
    def terminal(self):
        tty_nr = cext.proc_tty_nr(self.pid)
        tmap = _psposix.get_terminal_map()
        try:
            return tmap[tty_nr]
        except KeyError:
            return None

    @wrap_exceptions
    def ppid(self):
        self._ppid = cext.proc_ppid(self.pid)
        return self._ppid

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
        return _common.pcputimes(*cext.proc_cpu_times(self.pid))

    @wrap_exceptions
    def memory_info(self):
        return pmem(*cext.proc_memory_info(self.pid))

    memory_full_info = memory_info

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

        if NETBSD:
            families, types = conn_tmap[kind]
            ret = set()
            rawlist = cext.proc_connections(self.pid)
            for item in rawlist:
                fd, fam, type, laddr, raddr, status = item
                if fam in families and type in types:
                    try:
                        status = TCP_STATUSES[status]
                    except KeyError:
                        status = TCP_STATUSES[cext.PSUTIL_CONN_NONE]
                    fam = sockfam_to_enum(fam)
                    type = socktype_to_enum(type)
                    nt = _common.pconn(fd, fam, type, laddr, raddr, status)
                    ret.add(nt)
            # On NetBSD the underlying C function does not raise NSP
            # in case the process is gone (and the returned list may
            # incomplete).
            self.name()  # raise NSP if the process disappeared on us
            return list(ret)

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
        # XXX is '?' legit? (we're not supposed to return it anyway)
        return PROC_STATUSES.get(code, '?')

    @wrap_exceptions
    def io_counters(self):
        rc, wc, rb, wb = cext.proc_io_counters(self.pid)
        return _common.pio(rc, wc, rb, wb)

    @wrap_exceptions
    def cwd(self):
        """Return process current working directory."""
        # sometimes we get an empty string, in which case we turn
        # it into None
        if OPENBSD and self.pid == 0:
            return None  # ...else it would raise EINVAL
        elif NETBSD:
            with wrap_exceptions_procfs(self):
                return os.readlink("/proc/%s/cwd" % self.pid)
        elif hasattr(cext, 'proc_open_files'):
            # FreeBSD < 8 does not support functions based on
            # kinfo_getfile() and kinfo_getvmmap()
            return cext.proc_cwd(self.pid) or None
        else:
            raise NotImplementedError(
                "supported only starting from FreeBSD 8" if
                FREEBSD else "")

    nt_mmap_grouped = namedtuple(
        'mmap', 'path rss, private, ref_count, shadow_count')
    nt_mmap_ext = namedtuple(
        'mmap', 'addr, perms path rss, private, ref_count, shadow_count')

    def _not_implemented(self):
        raise NotImplementedError

    # FreeBSD < 8 does not support functions based on kinfo_getfile()
    # and kinfo_getvmmap()
    if hasattr(cext, 'proc_open_files'):
        @wrap_exceptions
        def open_files(self):
            """Return files opened by process as a list of namedtuples."""
            rawlist = cext.proc_open_files(self.pid)
            return [_common.popenfile(path, fd) for path, fd in rawlist]
    else:
        open_files = _not_implemented

    # FreeBSD < 8 does not support functions based on kinfo_getfile()
    # and kinfo_getvmmap()
    if hasattr(cext, 'proc_num_fds'):
        @wrap_exceptions
        def num_fds(self):
            """Return the number of file descriptors opened by this process."""
            ret = cext.proc_num_fds(self.pid)
            if NETBSD:
                # On NetBSD the underlying C function does not raise NSP
                # in case the process is gone.
                self.name()  # raise NSP if the process disappeared on us
            return ret
    else:
        num_fds = _not_implemented

    # --- FreeBSD only APIs

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

        @wrap_exceptions
        def memory_maps(self):
            return cext.proc_memory_maps(self.pid)
