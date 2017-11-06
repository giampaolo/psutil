"""Cygwin platform implementation."""

# TODO: Large chunks of this module are copy/pasted from the Linux module;
# seek out further opportunities for refactoring

from __future__ import division

import errno
import os
import re
import sys
from collections import namedtuple

from . import _common
from . import _psposix
from . import _psutil_cygwin as cext
from . import _psutil_posix as cext_posix
from ._common import conn_tmap
from ._common import decode
from ._common import encode
from ._common import get_procfs_path
from ._common import isfile_strict
from ._common import memoize_when_activated
from ._common import open_binary
from ._common import open_text
from ._common import popenfile
from ._common import sockfam_to_enum
from ._common import socktype_to_enum
from ._common import usage_percent
from ._common import wrap_exceptions
from ._compat import PY3
from ._compat import b
from ._compat import lru_cache
from ._compat import xrange

if sys.version_info >= (3, 4):
    import enum
else:
    enum = None

__extra__all__ = ["PROCFS_PATH"]


# =====================================================================
# --- constants
# =====================================================================

_cygwin_version_re = re.compile(r'(?P<major>\d+)\.(?P<minor>\d+)\.'
                                '(?P<micro>\d+)\((?P<api_major>\d+)\.'
                                '(?P<api_minor>\d+)/(?P<shared_data>\d+)/'
                                '(?P<mount_registry>\d+)\)')
_cygwin_version = _cygwin_version_re.match(os.uname()[2]).groupdict()

CYGWIN_VERSION = (int(_cygwin_version['major']),
                  int(_cygwin_version['minor']),
                  int(_cygwin_version['micro']))

CYGWIN_VERSION_API = (int(_cygwin_version['api_major']),
                      int(_cygwin_version['api_minor']))

CYGWIN_VERSION_SHARED_DATA = int(_cygwin_version['shared_data'])

CYGWIN_VERSION_MOUNT_REGISTRY = int(_cygwin_version['mount_registry'])


if enum is None:
    AF_LINK = -1
else:
    AddressFamily = enum.IntEnum('AddressFamily', {'AF_LINK': -1})
    AF_LINK = AddressFamily.AF_LINK


# Number of clock ticks per second
CLOCK_TICKS = os.sysconf("SC_CLK_TCK")


# TODO: Update me to properly reflect Cygwin-recognized process statuses
# taken from /fs/proc/array.c
PROC_STATUSES = {
    "R": _common.STATUS_RUNNING,
    "S": _common.STATUS_SLEEPING,
    "D": _common.STATUS_DISK_SLEEP,
    "T": _common.STATUS_STOPPED,
    "t": _common.STATUS_TRACING_STOP,
    "Z": _common.STATUS_ZOMBIE,
    "X": _common.STATUS_DEAD,
    "x": _common.STATUS_DEAD,
    "K": _common.STATUS_WAKE_KILL,
    "W": _common.STATUS_WAKING
}

CONN_DELETE_TCB = "DELETE_TCB"

TCP_STATUSES = {
    cext.MIB_TCP_STATE_ESTAB: _common.CONN_ESTABLISHED,
    cext.MIB_TCP_STATE_SYN_SENT: _common.CONN_SYN_SENT,
    cext.MIB_TCP_STATE_SYN_RCVD: _common.CONN_SYN_RECV,
    cext.MIB_TCP_STATE_FIN_WAIT1: _common.CONN_FIN_WAIT1,
    cext.MIB_TCP_STATE_FIN_WAIT2: _common.CONN_FIN_WAIT2,
    cext.MIB_TCP_STATE_TIME_WAIT: _common.CONN_TIME_WAIT,
    cext.MIB_TCP_STATE_CLOSED: _common.CONN_CLOSE,
    cext.MIB_TCP_STATE_CLOSE_WAIT: _common.CONN_CLOSE_WAIT,
    cext.MIB_TCP_STATE_LAST_ACK: _common.CONN_LAST_ACK,
    cext.MIB_TCP_STATE_LISTEN: _common.CONN_LISTEN,
    cext.MIB_TCP_STATE_CLOSING: _common.CONN_CLOSING,
    cext.MIB_TCP_STATE_DELETE_TCB: CONN_DELETE_TCB,
    cext.PSUTIL_CONN_NONE: _common.CONN_NONE,
}


ACCESS_DENIED_SET = frozenset([errno.EPERM, errno.EACCES,
                               cext.ERROR_ACCESS_DENIED])

# =====================================================================
# -- exceptions
# =====================================================================


# these get overwritten on "import psutil" from the __init__.py file
NoSuchProcess = None
ZombieProcess = None
AccessDenied = None
TimeoutExpired = None


# =====================================================================
# --- utils
# =====================================================================


@lru_cache(maxsize=512)
def _win32_QueryDosDevice(s):
    return cext.win32_QueryDosDevice(s)


# TODO: Copied almost verbatim from the windows module, except don't
# us os.path.join since that uses posix sep
def convert_dos_path(s):
    # convert paths using native DOS format like:
    # "\Device\HarddiskVolume1\Windows\systemew\file.txt"
    # into: "C:\Windows\systemew\file.txt"
    if PY3 and not isinstance(s, str):
        s = s.decode('utf8')
    rawdrive = '\\'.join(s.split('\\')[:3])
    driveletter = _win32_QueryDosDevice(rawdrive)
    return '%s\\%s' % (driveletter, s[len(rawdrive):])


# =====================================================================
# --- named tuples
# =====================================================================


scputimes = namedtuple('scputimes', ['user', 'system', 'idle'])
pmem = namedtuple('pmem', ['rss', 'vms', 'shared', 'text', 'lib', 'data',
                           'dirty'])
pmem = namedtuple(
    'pmem', ['rss', 'vms',
             'num_page_faults', 'peak_wset', 'wset', 'peak_paged_pool',
             'paged_pool', 'peak_nonpaged_pool', 'nonpaged_pool',
             'pagefile', 'peak_pagefile', 'private'])
pfullmem = namedtuple('pfullmem', pmem._fields + ('uss', ))
svmem = namedtuple('svmem', ['total', 'available', 'percent', 'used', 'free'])
pmmap_grouped = namedtuple('pmmap_grouped', ['path', 'rss'])
pmmap_ext = namedtuple(
    'pmmap_ext', 'addr perms ' + ' '.join(pmmap_grouped._fields))
ntpinfo = namedtuple(
    'ntpinfo', ['num_handles', 'ctx_switches', 'user_time', 'kernel_time',
                'create_time', 'num_threads', 'io_rcount', 'io_wcount',
                'io_rbytes', 'io_wbytes'])


# =====================================================================
# --- system memory
# =====================================================================


def _get_meminfo():
    mems = {}
    with open_binary('%s/meminfo' % get_procfs_path()) as f:
        for line in f:
            fields = line.split()
            mems[fields[0].rstrip(b':')] = int(fields[1]) * 1024

    return mems


def virtual_memory():
    """Report virtual memory stats.
    This implementation matches "free" and "vmstat -s" cmdline
    utility values and procps-ng-3.3.12 source was used as a reference
    (2016-09-18):
    https://gitlab.com/procps-ng/procps/blob/
        24fd2605c51fccc375ab0287cec33aa767f06718/proc/sysinfo.c
    For reference, procps-ng-3.3.10 is the version available on Ubuntu
    16.04.

    Note about "available" memory: up until psutil 4.3 it was
    calculated as "avail = (free + buffers + cached)". Now
    "MemAvailable:" column (kernel 3.14) from /proc/meminfo is used as
    it's more accurate.
    That matches "available" column in newer versions of "free".
    """
    mems = _get_meminfo()

    # /proc doc states that the available fields in /proc/meminfo vary
    # by architecture and compile options, but these 3 values are also
    # returned by sysinfo(2); as such we assume they are always there.
    total = mems[b'MemTotal']
    free = mems[b'MemFree']

    used = total - free

    # On Windows we are treating avail and free as the same
    # TODO: Are they really though?
    avail = free

    percent = usage_percent((total - avail), total, _round=1)

    return svmem(total, avail, percent, used, free)


def swap_memory():
    mems = _get_meminfo()
    total = mems[b'SwapTotal']
    free = mems[b'SwapFree']
    used = total - free
    percent = usage_percent(used, total, _round=1)
    return _common.sswap(total, used, free, percent, 0, 0)


# =====================================================================
# --- CPUs
# =====================================================================


def cpu_times():
    """Return a named tuple representing the following system-wide
    CPU times:
    (user, nice, system, idle, iowait, irq, softirq [steal, [guest,
     [guest_nice]]])
    Last 3 fields may not be available on all Linux kernel versions.
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


def cpu_count_logical():
    """Return the number of logical CPUs in the system."""
    try:
        return os.sysconf("SC_NPROCESSORS_ONLN")
    except ValueError:
        # as a second fallback we try to parse /proc/cpuinfo
        num = 0
        with open_binary('%s/cpuinfo' % get_procfs_path()) as f:
            for line in f:
                if line.lower().startswith(b'processor'):
                    num += 1

        # unknown format (e.g. amrel/sparc architectures), see:
        # https://github.com/giampaolo/psutil/issues/200
        # try to parse /proc/stat as a last resort
        if num == 0:
            search = re.compile('cpu\d')
            with open_text('%s/stat' % get_procfs_path()) as f:
                for line in f:
                    line = line.split(' ')[0]
                    if search.match(line):
                        num += 1

        if num == 0:
            # mimic os.cpu_count()
            return None
        return num


def cpu_count_physical():
    """Return the number of physical cores in the system."""
    mapping = {}
    current_info = {}
    with open_binary('%s/cpuinfo' % get_procfs_path()) as f:
        for line in f:
            line = line.strip().lower()
            if not line:
                # new section
                if (b'physical id' in current_info and
                        b'cpu cores' in current_info):
                    mapping[current_info[b'physical id']] = \
                        current_info[b'cpu cores']
                current_info = {}
            else:
                # ongoing section
                if (line.startswith(b'physical id') or
                        line.startswith(b'cpu cores')):
                    key, value = line.split(b'\t:', 1)
                    current_info[key] = int(value)

    # mimic os.cpu_count()
    return sum(mapping.values()) or None


# TODO: Works mostly the same as on Linux, but softirq is not available;
# meanwhile the Windows module supports number of system calls, but this
# implementation does not.  There's also a question of whether we want it
# to count Cygwin "system" calls, actual Windows system calls, or what...
# It's a somewhat ill-defined field on Cygwin; may have to come back to it
# TODO: Depending on what we decide to do about syscalls, this implementation
# could be shared with the Linux implementation with some minor tweaks to the
# latter
def cpu_stats():
    with open_binary('%s/stat' % get_procfs_path()) as f:
        ctx_switches = None
        interrupts = None
        for line in f:
            if line.startswith(b'ctxt'):
                ctx_switches = int(line.split()[1])
            elif line.startswith(b'intr'):
                interrupts = int(line.split()[1])
            if ctx_switches is not None and interrupts is not None:
                break
    syscalls = 0
    soft_interrupts = 0
    return _common.scpustats(
        ctx_switches, interrupts, soft_interrupts, syscalls)


# =====================================================================
# --- network
# =====================================================================


# TODO: This might merit a little further work to get the "friendly"
# interface names instead of interface UUIDs
net_if_addrs = cext_posix.net_if_addrs


def net_connections(kind, _pid=-1):
    """Return socket connections.  If pid == -1 return system-wide
    connections (as opposed to connections opened by one process only).
    """
    if kind not in conn_tmap:
        raise ValueError("invalid %r kind argument; choose between %s"
                         % (kind, ', '.join([repr(x) for x in conn_tmap])))
    elif kind == 'unix':
        raise ValueError("invalid %r kind argument; although UNIX sockets "
                         "are supported on Cygwin it is not possible to "
                         "enumerate the UNIX sockets opened by a process"
                         % kind)

    families, types = conn_tmap[kind]
    if _pid > 0:
        _pid = cext.cygpid_to_winpid(_pid)

    # Note: This lists *all* net connections on the system, not just ones by
    # Cygwin processes; below we whittle it down just to Cygwin processes, but
    # we might consider an extra option for showing non-Cygwin processes as
    # well
    rawlist = cext.net_connections(_pid, families, types)
    ret = set()
    for item in rawlist:
        fd, fam, type, laddr, raddr, status, pid = item
        status = TCP_STATUSES[status]
        fam = sockfam_to_enum(fam)
        type = socktype_to_enum(type)
        if _pid == -1:
            try:
                pid = cext.winpid_to_cygpid(pid)
            except OSError as exc:
                if exc.errno == errno.ESRCH:
                    continue
                raise

            nt = _common.sconn(fd, fam, type, laddr, raddr, status, pid)
        else:
            nt = _common.pconn(fd, fam, type, laddr, raddr, status)
        ret.add(nt)
    return list(ret)


def net_if_stats():
    ret = {}
    if_stats = cext.net_if_stats()
    # NOTE: Cygwin does some tricky things in how getifaddrs is handled
    # which our net_if_stats does not do, such that net_if_stats does not
    # return all the same interfaces as net_if_stats, so here we artifically
    # limit the net_if_stats() results to just those interfaces returned by
    # net_if_addrs
    if_names = set(addr[0] for addr in net_if_addrs())
    for name, items in if_stats.items():
        if name not in if_names:
            continue
        name = encode(name)
        isup, duplex, speed, mtu = items
        if hasattr(_common, 'NicDuplex'):
            duplex = _common.NicDuplex(duplex)
        ret[name] = _common.snicstats(isup, duplex, speed, mtu)
    return ret


def net_io_counters():
    ret = cext.net_io_counters()
    return dict([(encode(k), v) for k, v in ret.items()])


# =====================================================================
# --- sensors
# =====================================================================


# TODO: Copied verbatim from the Windows module
def sensors_battery():
    """Return battery information."""
    # For constants meaning see:
    # https://msdn.microsoft.com/en-us/library/windows/desktop/
    #     aa373232(v=vs.85).aspx
    acline_status, flags, percent, secsleft = cext.sensors_battery()
    power_plugged = acline_status == 1
    no_battery = bool(flags & 128)
    charging = bool(flags & 8)

    if no_battery:
        return None
    if power_plugged or charging:
        secsleft = _common.POWER_TIME_UNLIMITED
    elif secsleft == -1:
        secsleft = _common.POWER_TIME_UNKNOWN

    return _common.sbattery(percent, secsleft, power_plugged)


# =====================================================================
# --- disks
# =====================================================================


disk_io_counters = cext.disk_io_counters


disk_usage = _psposix.disk_usage


# TODO: Copied verbatim from the Linux module; refactor
def disk_partitions(all=False):
    """Return mounted disk partitions as a list of namedtuples"""
    fstypes = set()
    with open_text("%s/filesystems" % get_procfs_path()) as f:
        for line in f:
            line = line.strip()
            if not line.startswith("nodev"):
                fstypes.add(line.strip())
            else:
                # ignore all lines starting with "nodev" except "nodev zfs"
                fstype = line.split("\t")[1]
                if fstype == "zfs":
                    fstypes.add("zfs")

    retlist = []
    partitions = cext.disk_partitions()
    for partition in partitions:
        device, mountpoint, fstype, opts = partition
        if device == 'none':
            device = ''
        if not all:
            if device == '' or fstype not in fstypes:
                continue
        ntuple = _common.sdiskpart(device, mountpoint, fstype, opts)
        retlist.append(ntuple)
    return retlist


# =====================================================================
# --- other system functions
# =====================================================================


def boot_time():
    """The system boot time expressed in seconds since the epoch."""
    return cext.boot_time()


# TODO: Copied verbatim from the Linux module
def users():
    """Return currently connected users as a list of namedtuples."""
    retlist = []
    rawlist = cext.users()
    for item in rawlist:
        user, tty, hostname, tstamp, user_process = item
        # note: the underlying C function includes entries about
        # system boot, run level and others.  We might want
        # to use them in the future.
        if not user_process:
            continue
        if hostname == ':0.0' or hostname == ':0':
            hostname = 'localhost'
        nt = _common.suser(user, tty or None, hostname, tstamp)
        retlist.append(nt)
    return retlist


# =====================================================================
# --- processes
# =====================================================================


def pids():
    """Returns a list of PIDs currently running on the system."""
    return [int(x) for x in os.listdir(b(get_procfs_path())) if x.isdigit()]


def pid_exists(pid):
    """Check For the existence of a unix pid."""
    return _psposix.pid_exists(pid)


class Process(object):
    """Cygwin process implementation."""

    __slots__ = ["pid", "_name", "_ppid", "_procfs_path", "_winpid"]

    @wrap_exceptions
    def __init__(self, pid):
        self.pid = pid
        self._name = None
        self._ppid = None
        self._procfs_path = get_procfs_path()
        self._winpid = cext.cygpid_to_winpid(pid)

    @memoize_when_activated
    def _parse_stat_file(self):
        """Parse /proc/{pid}/stat file. Return a list of fields where
        process name is in position 0.
        Using "man proc" as a reference: where "man proc" refers to
        position N, always subscract 2 (e.g starttime pos 22 in
        'man proc' == pos 20 in the list returned here).
        """

        stat_filename = "%s/%s/stat" % (self._procfs_path, self.pid)

        # NOTE: On Cygwin, if the stat file exists but reading it raises an
        # EINVAL, this indicates that we are probably looking at a zombie
        # process (this doesn't happen in all cases--seems to be a bug in
        # Cygwin)
        try:
            with open_binary(stat_filename) as f:
                data = f.read()
        except IOError as err:
            if (err.errno == errno.EINVAL and
                    os.path.exists(err.filename)):
                raise ZombieProcess(self.pid, self._name, self._ppid)

            raise
        # Process name is between parentheses. It can contain spaces and
        # other parentheses. This is taken into account by looking for
        # the first occurrence of "(" and the last occurence of ")".
        rpar = data.rfind(b')')
        name = data[data.find(b'(') + 1:rpar]
        fields_after_name = data[rpar + 2:].split()
        return [name] + fields_after_name

    @memoize_when_activated
    def _read_status_file(self):
        with open_binary("%s/%s/status" % (self._procfs_path, self.pid)) as f:
            return f.read()

    @memoize_when_activated
    def oneshot_info(self):
        """Return multiple information about this process as a
        raw tuple.
        """
        return cext.proc_info(self._winpid)

    def oneshot_enter(self):
        self._parse_stat_file.cache_activate()
        self._read_status_file.cache_activate()
        self.oneshot_info.cache_activate()

    def oneshot_exit(self):
        self._parse_stat_file.cache_deactivate()
        self._read_status_file.cache_deactivate()
        self.oneshot_info.cache_deactivate()

    @wrap_exceptions
    def name(self):
        name = self._parse_stat_file()[0]
        if PY3:
            name = decode(name)
        # XXX - gets changed later and probably needs refactoring
        return name

    def exe(self):
        try:
            return os.readlink("%s/%s/exe" % (self._procfs_path, self.pid))
        except OSError as err:
            if err.errno in (errno.ENOENT, errno.ESRCH):
                # no such file error; might be raised also if the
                # path actually exists for system processes with
                # low pids (about 0-20)
                if os.path.lexists("%s/%s" % (self._procfs_path, self.pid)):
                    return ""
                else:
                    if not _psposix.pid_exists(self.pid):
                        raise NoSuchProcess(self.pid, self._name)
                    else:
                        raise ZombieProcess(self.pid, self._name, self._ppid)
            if err.errno in (errno.EPERM, errno.EACCES):
                raise AccessDenied(self.pid, self._name)
            raise

    @wrap_exceptions
    def cmdline(self):
        with open_text("%s/%s/cmdline" % (self._procfs_path, self.pid)) as f:
            data = f.read()
        if not data:
            # may happen in case of zombie process
            return []
        if data.endswith('\x00'):
            data = data[:-1]
        return [x for x in data.split('\x00')]

    # TODO: /proc/<pid>/environ will be available in newer versions of
    # Cygwin--do a version check and provide it if available.

    @wrap_exceptions
    def terminal(self):
        tty_nr = int(self._parse_stat_file()[5])
        tmap = _psposix.get_terminal_map()
        try:
            return tmap[tty_nr]
        except KeyError:
            return None

    @wrap_exceptions
    def io_counters(self):
        try:
            ret = cext.proc_io_counters(self._winpid)
        except OSError as err:
            if err.errno in ACCESS_DENIED_SET:
                nt = ntpinfo(*self.oneshot_info())
                ret = (nt.io_rcount, nt.io_wcount, nt.io_rbytes, nt.io_wbytes)
            else:
                raise
        return _common.pio(*ret)

    @wrap_exceptions
    def cpu_times(self):
        values = self._parse_stat_file()
        utime = float(values[12]) / CLOCK_TICKS
        stime = float(values[13]) / CLOCK_TICKS
        children_utime = float(values[14]) / CLOCK_TICKS
        children_stime = float(values[15]) / CLOCK_TICKS
        return _common.pcputimes(utime, stime, children_utime, children_stime)

    @wrap_exceptions
    def wait(self, timeout=None):
        try:
            return _psposix.wait_pid(self.pid, timeout)
        except _psposix.TimeoutExpired:
            raise TimeoutExpired(timeout, self.pid, self._name)

    @wrap_exceptions
    def create_time(self):
        try:
            return cext.proc_create_time(self._winpid)
        except OSError as err:
            if err.errno in ACCESS_DENIED_SET:
                return ntpinfo(*self.oneshot_info()).create_time
            raise

    def _get_raw_meminfo(self):
        try:
            return cext.proc_memory_info(self._winpid)
        except OSError as err:
            if err.errno in ACCESS_DENIED_SET:
                # TODO: the C ext can probably be refactored in order
                # to get this from cext.proc_info()
                return cext.proc_memory_info_2(self._winpid)
            raise

    @wrap_exceptions
    def memory_info(self):
        # on Windows RSS == WorkingSetSize and VMS == PagefileUsage.
        # Underlying C function returns fields of PROCESS_MEMORY_COUNTERS
        # struct.
        t = self._get_raw_meminfo()
        rss = t[2]  # wset
        vms = t[7]  # pagefile
        return pmem(*(rss, vms, ) + t)

    @wrap_exceptions
    def memory_full_info(self):
        basic_mem = self.memory_info()
        uss = cext.proc_memory_uss(self._winpid)
        return pfullmem(*basic_mem + (uss, ))

    def memory_maps(self):
        try:
            raw = cext.proc_memory_maps(self._winpid)
        except OSError as err:
            # XXX - can't use wrap_exceptions decorator as we're
            # returning a generator; probably needs refactoring.
            if err.errno in ACCESS_DENIED_SET:
                raise AccessDenied(self.pid, self._name)
            if err.errno == errno.ESRCH:
                raise NoSuchProcess(self.pid, self._name)
            raise
        else:
            for addr, perm, path, rss in raw:
                path = cext.winpath_to_cygpath(convert_dos_path(path))
                addr = hex(addr)
                yield (addr, perm, path, rss)

    @wrap_exceptions
    def cwd(self):
        return os.readlink("%s/%s/cwd" % (self._procfs_path, self.pid))

    @wrap_exceptions
    def num_ctx_switches(self):
        ctx_switches = ntpinfo(*self.oneshot_info()).ctx_switches
        # only voluntary ctx switches are supported
        return _common.pctxsw(ctx_switches, 0)

    @wrap_exceptions
    def num_threads(self):
        return ntpinfo(*self.oneshot_info()).num_threads

    @wrap_exceptions
    def threads(self):
        rawlist = cext.proc_threads(self._winpid)
        retlist = []
        for thread_id, utime, stime in rawlist:
            ntuple = _common.pthread(thread_id, utime, stime)
            retlist.append(ntuple)
        return retlist

    @wrap_exceptions
    def nice_get(self):
        # Use C implementation
        return cext_posix.getpriority(self.pid)

    @wrap_exceptions
    def nice_set(self, value):
        return cext_posix.setpriority(self.pid, value)

    @wrap_exceptions
    def cpu_affinity_get(self):
        def from_bitmask(x):
            return [i for i in xrange(64) if (1 << i) & x]
        bitmask = cext.proc_cpu_affinity_get(self._winpid)
        return from_bitmask(bitmask)

    @wrap_exceptions
    def cpu_affinity_set(self, value):
        def to_bitmask(l):
            if not l:
                raise ValueError("invalid argument %r" % l)
            out = 0
            for bit in l:
                out |= 2 ** bit
            return out

        # SetProcessAffinityMask() states that ERROR_INVALID_PARAMETER
        # is returned for an invalid CPU but this seems not to be true,
        # therefore we check CPUs validy beforehand.
        allcpus = list(range(len(per_cpu_times())))
        for cpu in value:
            if cpu not in allcpus:
                if not isinstance(cpu, (int, long)):
                    raise TypeError(
                        "invalid CPU %r; an integer is required" % cpu)
                else:
                    raise ValueError("invalid CPU %r" % cpu)

        bitmask = to_bitmask(value)
        try:
            cext.proc_cpu_affinity_set(self._winpid, bitmask)
        except OSError as exc:
            if exc.errno == errno.EIO:
                raise AccessDenied(self.pid, self._name)

    @wrap_exceptions
    def status(self):
        letter = self._parse_stat_file()[1]
        if PY3:
            letter = letter.decode()
        # XXX is '?' legit? (we're not supposed to return it anyway)
        return PROC_STATUSES.get(letter, '?')

    @wrap_exceptions
    def open_files(self):
        retlist = []
        files = os.listdir("%s/%s/fd" % (self._procfs_path, self.pid))
        hit_enoent = False
        for fd in files:
            file = "%s/%s/fd/%s" % (self._procfs_path, self.pid, fd)
            try:
                path = os.readlink(file)
            except OSError as err:
                # ENOENT == file which is gone in the meantime
                if err.errno in (errno.ENOENT, errno.ESRCH):
                    hit_enoent = True
                    continue
                elif err.errno == errno.EINVAL:
                    # not a link
                    continue
                else:
                    raise
            else:
                # If path is not an absolute there's no way to tell
                # whether it's a regular file or not, so we skip it.
                # A regular file is always supposed to be have an
                # absolute path though.
                if path.startswith('/') and isfile_strict(path):
                    ntuple = popenfile(path, int(fd))
                    retlist.append(ntuple)
        if hit_enoent:
            # raise NSP if the process disappeared on us
            os.stat('%s/%s' % (self._procfs_path, self.pid))
        return retlist

    @wrap_exceptions
    def connections(self, kind='inet'):
        return net_connections(kind, _pid=self.pid)

    @wrap_exceptions
    def num_fds(self):
        return len(os.listdir("%s/%s/fd" % (self._procfs_path, self.pid)))

    @wrap_exceptions
    def ppid(self):
        return int(self._parse_stat_file()[2])

    @wrap_exceptions
    def uids(self, _uids_re=re.compile(b'Uid:\t(\d+)')):
        # More or less the same as on Linux, but the fields are separated by
        # spaces instead of tabs; and anyways there is no difference on Cygwin
        # between real, effective, and saved uids.
        # TODO: We could use the same regexp on both Linux and Cygwin by just
        # changing the Linux regexp to treat whitespace more flexibly
        data = self._read_status_file()
        real = _uids_re.findall(data)[0]
        return _common.puids(int(real), int(real), int(real))

    @wrap_exceptions
    def gids(self, _gids_re=re.compile(b'Gid:\t(\d+)')):
        # See note in uids
        data = self._read_status_file()
        real = _gids_re.findall(data)[0]
        return _common.pgids(int(real), int(real), int(real))
