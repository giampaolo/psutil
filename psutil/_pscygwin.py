"""Cygwin platform implementation."""

from __future__ import division

import errno
import os
import sys
from collections import namedtuple

from . import _common
from . import _pslinux
from . import _psposix
from . import _psutil_cygwin as cext  # NOQA
from ._common import get_procfs_path
from ._common import memoize_when_activated
from ._common import NoSuchProcess
from ._common import open_binary
from ._common import TimeoutExpired
from ._common import usage_percent
from ._pslinux import wrap_exceptions

if sys.version_info >= (3, 4):
    import enum
else:
    enum = None


__extra__all__ = ["PROCFS_PATH"]


# =====================================================================
# --- globals
# =====================================================================


CLOCK_TICKS = _pslinux.CLOCK_TICKS


AF_LINK = _pslinux.AF_LINK


# =====================================================================
# --- named tuples
# =====================================================================

# psutil.virtual_memory()
svmem = namedtuple('svmem', ['total', 'available', 'percent', 'used', 'free'])

scputimes = namedtuple('scputimes', ['user', 'system', 'idle'])

pmem = pfullmem = _pslinux.pmem

# psutil.Process.cpu_times()
pcputimes = namedtuple('pcputimes',
                       ['user', 'system', 'children_user', 'children_system'])


# =====================================================================
# --- other system functions
# =====================================================================


boot_time = _pslinux.boot_time


# =====================================================================
# --- system memory
# =====================================================================


def virtual_memory():
    """Report virtual memory stats.

    This is implemented similarly as on Linux by reading /proc/meminfo;
    however the level of detail available in Cygwin's /proc/meminfo is
    significantly less than on Linux and the memory manager is still
    that of the NT kernel so it does not make sense to try to use memory
    calculations for Linux.

    The resulting virtual memory stats are the same as those that would
    be obtained with the Windows support module.
    """
    mems = {}
    with open_binary('%s/meminfo' % get_procfs_path()) as f:
        for line in f:
            fields = [n.rstrip(b': ') for n in line.split()]
            mems[fields[0]] = int(fields[1]) * 1024

    total = mems[b'MemTotal']
    avail = free = mems[b'MemFree']
    used = total - free
    percent = usage_percent(used, total, round_=1)
    return svmem(total, avail, percent, used, free)


def swap_memory():
    """Return swap memory metrics."""
    raise NotImplementedError("swap_memory not implemented on Cygwin")


# =====================================================================
# --- CPUs
# =====================================================================


def cpu_times():
    """Return a named tuple representing the following system-wide
    CPU times:
    (user, system, idle)
    """
    procfs_path = get_procfs_path()
    with open_binary('%s/stat' % procfs_path) as f:
        values = f.readline().split()
    fields = values[1:2] + values[3:len(scputimes._fields) + 2]
    fields = [float(x) / CLOCK_TICKS for x in fields]
    return scputimes(*fields)


def per_cpu_times():
    """Return a list of namedtuple representing the CPU times
    for every CPU available on the system.
    """
    procfs_path = get_procfs_path()
    cpus = []
    with open_binary('%s/stat' % procfs_path) as f:
        # get rid of the first line which refers to system wide CPU stats
        f.readline()
        for line in f:
            if line.startswith(b'cpu'):
                values = line.split()
                fields = values[1:2] + values[3:len(scputimes._fields) + 2]
                fields = [float(x) / CLOCK_TICKS for x in fields]
                entry = scputimes(*fields)
                cpus.append(entry)
        return cpus


cpu_count_logical = _pslinux.cpu_count_logical
cpu_count_physical = _pslinux.cpu_count_physical
cpu_stats = _pslinux.cpu_stats


# =====================================================================
# --- network
# =====================================================================


def net_if_addrs():
    """Return the addresses associated to each NIC (network interface
    card) installed on the system.
    """
    raise NotImplementedError("net_if_addrs not implemented on Cygwin")


def net_connections(kind='inet'):
    """Return system-wide open connections."""
    raise NotImplementedError("net_connections not implemented on Cygwin")


def net_io_counters():
    """Return network I/O statistics for every network interface
    installed on the system as a dict of raw tuples.
    """
    raise NotImplementedError("net_io_counters not implemented on Cygwin")


def net_if_stats():
    """Return information about each NIC (network interface card)
    installed on the system.
    """
    raise NotImplementedError("net_if_stats not implemented on Cygwin")


# =====================================================================
# --- disks
# =====================================================================


def disk_usage(path):
    """Return disk usage statistics about the given *path* as a
    namedtuple including total, used and free space expressed in bytes
    plus the percentage usage.
    """
    raise NotImplementedError("disk_usage not implemented on Cygwin")


def disk_io_counters(perdisk=False):
    """Return disk I/O statistics for every disk installed on the
    system as a dict of raw tuples.
    """
    # Note: Currently not implemented on Cygwin, but rather than raise
    # a NotImplementedError we can return an empty dict here.
    return {}


def disk_partitions(all=False):
    """Return mounted disk partitions as a list of namedtuples."""
    raise NotImplementedError("disk_partitions not implemented on Cygwin")


# =====================================================================
# --- other system functions
# =====================================================================


def users():
    """Return currently connected users as a list of namedtuples."""
    raise NotImplementedError("users not implemented on Cygwin")


# =====================================================================
# --- processes
# =====================================================================


pid_exists = _psposix.pid_exists
pids = _pslinux.pids


def ppid_map():
    """Obtain a {pid: ppid, ...} dict for all running processes in
    one shot. Used to speed up Process.children().

    Note: Although the psutil._pslinux.ppid_map implementation also
    works on Cygwin, it is very slow, as reading the full /proc/[pid]/stat
    file is slow on Cygwin.  Instead, Cygwin supplies a /proc/[pid]/ppid file
    as a faster way to get a process's PPID.
    """
    ret = {}
    procfs_path = get_procfs_path()
    for pid in pids():
        try:
            with open_binary("%s/%s/ppid" % (procfs_path, pid)) as f:
                data = f.read()
        except EnvironmentError as err:
            # Note: we should be able to access /stat for all processes
            # aka it's unlikely we'll bump into EPERM, which is good.
            if err.errno not in (errno.ENOENT, errno.ESRCH):
                raise
        else:
            ret[pid] = int(data.strip())
    return ret


class Process(object):
    """Cygwin process implementation.

    Note: This reuses a signficant amount of functionality from
    ``_pslinux.Process`` but should avoid subclassing it, as it also contains
    functionality that does not make sense on Cygwin.  Instead we borrow from
    it piecemeal.
    """

    __slots__ = ["pid", "_name", "_ppid", "_procfs_path", "_cache"]

    def __init__(self, pid):
        self.pid = pid
        self._name = None
        self._ppid = None
        self._procfs_path = get_procfs_path()

    _assert_alive = _pslinux.Process._assert_alive

    _stat_map = _pslinux.Process._stat_map.copy()

    @memoize_when_activated
    def _parse_stat_file(self):
        try:
            stats = _pslinux.Process._parse_stat_file(self)
        except IOError as err:
            # NOTE: On Cygwin, if the stat file exists but reading it raises
            # an EINVAL, this indicates that we are probably looking at a
            # zombie process (this doesn't happen in all cases--seems it might
            # be a bug in Cygwin)
            #
            # In some cases there is also a race condition where reading the
            # file "succeeds" but it is empty.  In this case an IndexError is
            # raised.
            #
            # In this case we return some default values based on what Cygwin
            # would return if not for this bug
            if not (err.errno == errno.EINVAL and
                    os.path.exists(err.filename)):
                raise

            stats = {}

        if stats:
            # Might be empty if the stat file was found to be empty while
            # trying to read a zombie process
            return stats

        # Fallback implementation for broken zombie processes
        stats = {
            'name': b'<defunct>',
            'status': b'Z',
            'ttynr': 0,
            'utime': 0,
            'stime': 0,
            'children_utime': 0,
            'children_stime': 0,
            'create_time': 0,
            'cpu_num': 0
        }

        # It is still possible to read the ppid, pgid, sid, and ctty
        for field in ['ppid', 'pgid', 'sid', 'ctty']:
            fname = os.path.join(self._procfs_path, str(self.pid), field)
            with open_binary(fname) as f:
                val = f.read().strip()
                try:
                    val = int(val)
                except ValueError:
                    pass
                stats[field] = val
        return stats

    @memoize_when_activated
    def _read_status_file(self):
        """Read /proc/{pid}/status file and return its content.
        The return value is cached in case oneshot() ctx manager is
        in use.
        """

        # Plagued by the same problem with zombie processes as _parse_stat_file
        # In this case we just return an empty string, and any method which
        # calls this method should be responsible for providing sensible
        # fallbacks in that case
        try:
            return _pslinux.Process._read_status_file(self)
        except IOError as err:
            if not (err.errno == errno.EINVAL and
                    os.path.exists(err.filename)):
                raise

        return b''

    def oneshot_enter(self):
        self._parse_stat_file.cache_activate(self)
        self._read_status_file.cache_activate(self)

    def oneshot_exit(self):
        self._parse_stat_file.cache_deactivate(self)
        self._read_status_file.cache_deactivate(self)

    name = _pslinux.Process.name
    exe = _pslinux.Process.exe
    cmdline = _pslinux.Process.cmdline

    def terminal(self):
        raise NotImplementedError("terminal not implemented on Cygwin")

    @wrap_exceptions
    def cpu_times(self):
        values = self._parse_stat_file()
        utime = float(values['utime']) / CLOCK_TICKS
        stime = float(values['stime']) / CLOCK_TICKS
        children_utime = float(values['children_utime']) / CLOCK_TICKS
        children_stime = float(values['children_stime']) / CLOCK_TICKS
        return pcputimes(utime, stime, children_utime, children_stime)

    @wrap_exceptions
    def wait(self, timeout=None):
        try:
            return _psposix.wait_pid(self.pid, timeout)
        except TimeoutExpired:
            raise TimeoutExpired(timeout, self.pid, self._name)

    _create_time_map = {}

    def create_time(self):
        # On Cygwin there is a rounding bug in process creation time
        # calculation, such that the same process's process creation time
        # can be reported differently from time to time (within a delta of
        # 1 second).
        # Therefore we use a hack: The first time create_time() is called
        # for a process we map that process's pid to its creation time
        # in _create_time_map above.  If another Process with the same pid
        # is created it first checks that pid's entry in the map, and if the
        # cached creation time is within 1 second it reuses the cached time.
        # We can assume that two procs with the same pid and creation time
        # within 1 second are the same process.  Cygwin will not reuse pids for
        # subsequently created processes, so it is is almost impossible to have
        # two different processes with the same pid within 1 second
        create_time = _pslinux.Process.create_time(self)
        cached = self._create_time_map.setdefault(self.pid, create_time)
        if abs(create_time - cached) <= 1:
            return cached
        else:
            # This would occur if the same PID has been reused some time
            # much later (at least more than a second) since we last saw
            # a process with this PID.
            self._create_time_map[self.pid] = create_time
            return create_time

    def memory_info(self):
        # This can, in rare cases, be impacted by the same zombie process bug
        # as _parse_stat_file
        try:
            return _pslinux.Process.memory_info(self)
        except (IOError, IndexError) as err:
            if not (isinstance(err, IndexError) or
                    (err.errno == errno.EINVAL and
                        os.path.exists(err.filename))):
                raise

        # Dummy result
        return pmem(*[0 for _ in range(len(pmem._fields))])

    # For now memory_full_info is just the same as memory_info on Cygwin We
    # could obtain info like USS, but it might require Windows system calls
    def memory_full_info(self):
        return self.memory_info()

    cwd = _pslinux.Process.cwd

    def num_ctx_switches(self):
        raise NotImplementedError("num_ctx_switches not implemented on Cygwin")

    def num_threads(self):
        raise NotImplementedError("num_threads not implemented on Cygwin")

    # Add wrapper around nice_get from _pslinux, except that it is allowed to
    # fail for zombie processes
    def nice_get(self):
        try:
            return _pslinux.Process.nice_get(self)
        except NoSuchProcess:
            if self.status() == _common.STATUS_ZOMBIE:
                return None

            raise

    nice_set = _pslinux.Process.nice_set
    status = _pslinux.Process.status

    def open_files(self):
        raise NotImplementedError("open_files not implemented on Cygwin")

    def connections(self, kind='inet'):
        raise NotImplementedError("connections not implemented on Cygwin")

    def num_fds(self):
        raise NotImplementedError("num_fds not implemented on Cygwin")

    @wrap_exceptions
    def ppid(self):
        with open_binary("%s/%s/ppid" % (self._procfs_path, self.pid)) as f:
            return int(f.read().strip())

    uids = _pslinux.Process.uids
    gids = _pslinux.Process.gids
