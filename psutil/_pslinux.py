# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Linux platform implementation."""

from __future__ import division

import base64
import errno
import functools
import os
import re
import socket
import struct
import sys
import warnings
from collections import defaultdict
from collections import namedtuple

from . import _common
from . import _psposix
from . import _psutil_linux as cext
from . import _psutil_posix as cext_posix
from ._common import isfile_strict
from ._common import NIC_DUPLEX_FULL
from ._common import NIC_DUPLEX_HALF
from ._common import NIC_DUPLEX_UNKNOWN
from ._common import supports_ipv6
from ._common import usage_percent
from ._compat import b
from ._compat import long
from ._compat import PY3

if sys.version_info >= (3, 4):
    import enum
else:
    enum = None


__extra__all__ = [
    #
    'PROCFS_PATH',
    # io prio constants
    "IOPRIO_CLASS_NONE", "IOPRIO_CLASS_RT", "IOPRIO_CLASS_BE",
    "IOPRIO_CLASS_IDLE",
    # connection status constants
    "CONN_ESTABLISHED", "CONN_SYN_SENT", "CONN_SYN_RECV", "CONN_FIN_WAIT1",
    "CONN_FIN_WAIT2", "CONN_TIME_WAIT", "CONN_CLOSE", "CONN_CLOSE_WAIT",
    "CONN_LAST_ACK", "CONN_LISTEN", "CONN_CLOSING", ]

# --- constants

HAS_PRLIMIT = hasattr(cext, "linux_prlimit")

# RLIMIT_* constants, not guaranteed to be present on all kernels
if HAS_PRLIMIT:
    for name in dir(cext):
        if name.startswith('RLIM'):
            __extra__all__.append(name)

# Number of clock ticks per second
CLOCK_TICKS = os.sysconf("SC_CLK_TCK")
PAGESIZE = os.sysconf("SC_PAGE_SIZE")
BOOT_TIME = None  # set later
if PY3:
    FS_ENCODING = sys.getfilesystemencoding()
if enum is None:
    AF_LINK = socket.AF_PACKET
else:
    AddressFamily = enum.IntEnum('AddressFamily',
                                 {'AF_LINK': socket.AF_PACKET})
    AF_LINK = AddressFamily.AF_LINK

# ioprio_* constants http://linux.die.net/man/2/ioprio_get
if enum is None:
    IOPRIO_CLASS_NONE = 0
    IOPRIO_CLASS_RT = 1
    IOPRIO_CLASS_BE = 2
    IOPRIO_CLASS_IDLE = 3
else:
    class IOPriority(enum.IntEnum):
        IOPRIO_CLASS_NONE = 0
        IOPRIO_CLASS_RT = 1
        IOPRIO_CLASS_BE = 2
        IOPRIO_CLASS_IDLE = 3

    globals().update(IOPriority.__members__)

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

# http://students.mimuw.edu.pl/lxr/source/include/net/tcp_states.h
TCP_STATUSES = {
    "01": _common.CONN_ESTABLISHED,
    "02": _common.CONN_SYN_SENT,
    "03": _common.CONN_SYN_RECV,
    "04": _common.CONN_FIN_WAIT1,
    "05": _common.CONN_FIN_WAIT2,
    "06": _common.CONN_TIME_WAIT,
    "07": _common.CONN_CLOSE,
    "08": _common.CONN_CLOSE_WAIT,
    "09": _common.CONN_LAST_ACK,
    "0A": _common.CONN_LISTEN,
    "0B": _common.CONN_CLOSING
}

# set later from __init__.py
NoSuchProcess = None
ZombieProcess = None
AccessDenied = None
TimeoutExpired = None


# --- utils

def open_text(fname):
    """On Python 3 opens a file in text mode by using fs encoding.
    On Python 2 this is just an alias for open(name, 'rt').
    """
    kw = dict(encoding=FS_ENCODING) if PY3 else dict()
    return open(fname, "rt", **kw)


def get_procfs_path():
    return sys.modules['psutil'].PROCFS_PATH


# --- named tuples

def set_scputimes_ntuple(procfs_path):
    """Return a namedtuple of variable fields depending on the
    CPU times available on this Linux kernel version which may be:
    (user, nice, system, idle, iowait, irq, softirq, [steal, [guest,
     [guest_nice]]])
    """
    global scputimes
    with open('%s/stat' % procfs_path, 'rb') as f:
        values = f.readline().split()[1:]
    fields = ['user', 'nice', 'system', 'idle', 'iowait', 'irq', 'softirq']
    vlen = len(values)
    if vlen >= 8:
        # Linux >= 2.6.11
        fields.append('steal')
    if vlen >= 9:
        # Linux >= 2.6.24
        fields.append('guest')
    if vlen >= 10:
        # Linux >= 3.2.0
        fields.append('guest_nice')
    scputimes = namedtuple('scputimes', fields)
    return scputimes


scputimes = set_scputimes_ntuple('/proc')

svmem = namedtuple(
    'svmem', ['total', 'available', 'percent', 'used', 'free',
              'active', 'inactive', 'buffers', 'cached'])

pextmem = namedtuple('pextmem', 'rss vms shared text lib data dirty')

pmmap_grouped = namedtuple(
    'pmmap_grouped', ['path', 'rss', 'size', 'pss', 'shared_clean',
                      'shared_dirty', 'private_clean', 'private_dirty',
                      'referenced', 'anonymous', 'swap'])

pmmap_ext = namedtuple(
    'pmmap_ext', 'addr perms ' + ' '.join(pmmap_grouped._fields))


# --- system memory

def virtual_memory():
    total, free, buffers, shared, _, _ = cext.linux_sysinfo()
    cached = active = inactive = None
    with open('%s/meminfo' % get_procfs_path(), 'rb') as f:
        for line in f:
            if line.startswith(b"Cached:"):
                cached = int(line.split()[1]) * 1024
            elif line.startswith(b"Active:"):
                active = int(line.split()[1]) * 1024
            elif line.startswith(b"Inactive:"):
                inactive = int(line.split()[1]) * 1024
            if (cached is not None and
                    active is not None and
                    inactive is not None):
                break
        else:
            # we might get here when dealing with exotic Linux flavors, see:
            # https://github.com/giampaolo/psutil/issues/313
            msg = "'cached', 'active' and 'inactive' memory stats couldn't " \
                  "be determined and were set to 0"
            warnings.warn(msg, RuntimeWarning)
            cached = active = inactive = 0
    avail = free + buffers + cached
    used = total - free
    percent = usage_percent((total - avail), total, _round=1)
    return svmem(total, avail, percent, used, free,
                 active, inactive, buffers, cached)


def swap_memory():
    _, _, _, _, total, free = cext.linux_sysinfo()
    used = total - free
    percent = usage_percent(used, total, _round=1)
    # get pgin/pgouts
    with open("%s/vmstat" % get_procfs_path(), "rb") as f:
        sin = sout = None
        for line in f:
            # values are expressed in 4 kilo bytes, we want bytes instead
            if line.startswith(b'pswpin'):
                sin = int(line.split(b' ')[1]) * 4 * 1024
            elif line.startswith(b'pswpout'):
                sout = int(line.split(b' ')[1]) * 4 * 1024
            if sin is not None and sout is not None:
                break
        else:
            # we might get here when dealing with exotic Linux flavors, see:
            # https://github.com/giampaolo/psutil/issues/313
            msg = "'sin' and 'sout' swap memory stats couldn't " \
                  "be determined and were set to 0"
            warnings.warn(msg, RuntimeWarning)
            sin = sout = 0
    return _common.sswap(total, used, free, percent, sin, sout)


# --- CPUs

def cpu_times():
    """Return a named tuple representing the following system-wide
    CPU times:
    (user, nice, system, idle, iowait, irq, softirq [steal, [guest,
     [guest_nice]]])
    Last 3 fields may not be available on all Linux kernel versions.
    """
    procfs_path = get_procfs_path()
    set_scputimes_ntuple(procfs_path)
    with open('%s/stat' % procfs_path, 'rb') as f:
        values = f.readline().split()
    fields = values[1:len(scputimes._fields) + 1]
    fields = [float(x) / CLOCK_TICKS for x in fields]
    return scputimes(*fields)


def per_cpu_times():
    """Return a list of namedtuple representing the CPU times
    for every CPU available on the system.
    """
    procfs_path = get_procfs_path()
    set_scputimes_ntuple(procfs_path)
    cpus = []
    with open('%s/stat' % procfs_path, 'rb') as f:
        # get rid of the first line which refers to system wide CPU stats
        f.readline()
        for line in f:
            if line.startswith(b'cpu'):
                values = line.split()
                fields = values[1:len(scputimes._fields) + 1]
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
        with open('%s/cpuinfo' % get_procfs_path(), 'rb') as f:
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
    with open('%s/cpuinfo' % get_procfs_path(), 'rb') as f:
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


# --- other system functions

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


def boot_time():
    """Return the system boot time expressed in seconds since the epoch."""
    global BOOT_TIME
    with open('%s/stat' % get_procfs_path(), 'rb') as f:
        for line in f:
            if line.startswith(b'btime'):
                ret = float(line.strip().split()[1])
                BOOT_TIME = ret
                return ret
        raise RuntimeError(
            "line 'btime' not found in %s/stat" % get_procfs_path())


# --- processes

def pids():
    """Returns a list of PIDs currently running on the system."""
    return [int(x) for x in os.listdir(b(get_procfs_path())) if x.isdigit()]


def pid_exists(pid):
    """Check For the existence of a unix pid."""
    return _psposix.pid_exists(pid)


# --- network

class _Ipv6UnsupportedError(Exception):
    pass


class Connections:
    """A wrapper on top of /proc/net/* files, retrieving per-process
    and system-wide open connections (TCP, UDP, UNIX) similarly to
    "netstat -an".

    Note: in case of UNIX sockets we're only able to determine the
    local endpoint/path, not the one it's connected to.
    According to [1] it would be possible but not easily.

    [1] http://serverfault.com/a/417946
    """

    def __init__(self):
        tcp4 = ("tcp", socket.AF_INET, socket.SOCK_STREAM)
        tcp6 = ("tcp6", socket.AF_INET6, socket.SOCK_STREAM)
        udp4 = ("udp", socket.AF_INET, socket.SOCK_DGRAM)
        udp6 = ("udp6", socket.AF_INET6, socket.SOCK_DGRAM)
        unix = ("unix", socket.AF_UNIX, None)
        self.tmap = {
            "all": (tcp4, tcp6, udp4, udp6, unix),
            "tcp": (tcp4, tcp6),
            "tcp4": (tcp4,),
            "tcp6": (tcp6,),
            "udp": (udp4, udp6),
            "udp4": (udp4,),
            "udp6": (udp6,),
            "unix": (unix,),
            "inet": (tcp4, tcp6, udp4, udp6),
            "inet4": (tcp4, udp4),
            "inet6": (tcp6, udp6),
        }
        self._procfs_path = None

    def get_proc_inodes(self, pid):
        inodes = defaultdict(list)
        for fd in os.listdir("%s/%s/fd" % (self._procfs_path, pid)):
            try:
                inode = os.readlink("%s/%s/fd/%s" % (
                    self._procfs_path, pid, fd))
            except OSError as err:
                # ENOENT == file which is gone in the meantime;
                # os.stat('/proc/%s' % self.pid) will be done later
                # to force NSP (if it's the case)
                if err.errno in (errno.ENOENT, errno.ESRCH):
                    continue
                elif err.errno == errno.EINVAL:
                    # not a link
                    continue
                else:
                    raise
            else:
                if inode.startswith('socket:['):
                    # the process is using a socket
                    inode = inode[8:][:-1]
                    inodes[inode].append((pid, int(fd)))
        return inodes

    def get_all_inodes(self):
        inodes = {}
        for pid in pids():
            try:
                inodes.update(self.get_proc_inodes(pid))
            except OSError as err:
                # os.listdir() is gonna raise a lot of access denied
                # exceptions in case of unprivileged user; that's fine
                # as we'll just end up returning a connection with PID
                # and fd set to None anyway.
                # Both netstat -an and lsof does the same so it's
                # unlikely we can do any better.
                # ENOENT just means a PID disappeared on us.
                if err.errno not in (
                        errno.ENOENT, errno.ESRCH, errno.EPERM, errno.EACCES):
                    raise
        return inodes

    def decode_address(self, addr, family):
        """Accept an "ip:port" address as displayed in /proc/net/*
        and convert it into a human readable form, like:

        "0500000A:0016" -> ("10.0.0.5", 22)
        "0000000000000000FFFF00000100007F:9E49" -> ("::ffff:127.0.0.1", 40521)

        The IP address portion is a little or big endian four-byte
        hexadecimal number; that is, the least significant byte is listed
        first, so we need to reverse the order of the bytes to convert it
        to an IP address.
        The port is represented as a two-byte hexadecimal number.

        Reference:
        http://linuxdevcenter.com/pub/a/linux/2000/11/16/LinuxAdmin.html
        """
        ip, port = addr.split(':')
        port = int(port, 16)
        # this usually refers to a local socket in listen mode with
        # no end-points connected
        if not port:
            return ()
        if PY3:
            ip = ip.encode('ascii')
        if family == socket.AF_INET:
            # see: https://github.com/giampaolo/psutil/issues/201
            if sys.byteorder == 'little':
                ip = socket.inet_ntop(family, base64.b16decode(ip)[::-1])
            else:
                ip = socket.inet_ntop(family, base64.b16decode(ip))
        else:  # IPv6
            # old version - let's keep it, just in case...
            # ip = ip.decode('hex')
            # return socket.inet_ntop(socket.AF_INET6,
            #          ''.join(ip[i:i+4][::-1] for i in xrange(0, 16, 4)))
            ip = base64.b16decode(ip)
            try:
                # see: https://github.com/giampaolo/psutil/issues/201
                if sys.byteorder == 'little':
                    ip = socket.inet_ntop(
                        socket.AF_INET6,
                        struct.pack('>4I', *struct.unpack('<4I', ip)))
                else:
                    ip = socket.inet_ntop(
                        socket.AF_INET6,
                        struct.pack('<4I', *struct.unpack('<4I', ip)))
            except ValueError:
                # see: https://github.com/giampaolo/psutil/issues/623
                if not supports_ipv6():
                    raise _Ipv6UnsupportedError
                else:
                    raise
        return (ip, port)

    def process_inet(self, file, family, type_, inodes, filter_pid=None):
        """Parse /proc/net/tcp* and /proc/net/udp* files."""
        if file.endswith('6') and not os.path.exists(file):
            # IPv6 not supported
            return
        with open_text(file) as f:
            f.readline()  # skip the first line
            for line in f:
                try:
                    _, laddr, raddr, status, _, _, _, _, _, inode = \
                        line.split()[:10]
                except ValueError:
                    raise RuntimeError(
                        "error while parsing %s; malformed line %r" % (
                            file, line))
                if inode in inodes:
                    # # We assume inet sockets are unique, so we error
                    # # out if there are multiple references to the
                    # # same inode. We won't do this for UNIX sockets.
                    # if len(inodes[inode]) > 1 and family != socket.AF_UNIX:
                    #     raise ValueError("ambiguos inode with multiple "
                    #                      "PIDs references")
                    pid, fd = inodes[inode][0]
                else:
                    pid, fd = None, -1
                if filter_pid is not None and filter_pid != pid:
                    continue
                else:
                    if type_ == socket.SOCK_STREAM:
                        status = TCP_STATUSES[status]
                    else:
                        status = _common.CONN_NONE
                    try:
                        laddr = self.decode_address(laddr, family)
                        raddr = self.decode_address(raddr, family)
                    except _Ipv6UnsupportedError:
                        continue
                    yield (fd, family, type_, laddr, raddr, status, pid)

    def process_unix(self, file, family, inodes, filter_pid=None):
        """Parse /proc/net/unix files."""
        # see: https://github.com/giampaolo/psutil/issues/675
        kw = dict(encoding=FS_ENCODING, errors='replace') if PY3 else dict()
        with open(file, 'rt', **kw) as f:
            f.readline()  # skip the first line
            for line in f:
                tokens = line.split()
                try:
                    _, _, _, _, type_, _, inode = tokens[0:7]
                except ValueError:
                    raise RuntimeError(
                        "error while parsing %s; malformed line %r" % (
                            file, line))
                if inode in inodes:
                    # With UNIX sockets we can have a single inode
                    # referencing many file descriptors.
                    pairs = inodes[inode]
                else:
                    pairs = [(None, -1)]
                for pid, fd in pairs:
                    if filter_pid is not None and filter_pid != pid:
                        continue
                    else:
                        if len(tokens) == 8:
                            path = tokens[-1]
                        else:
                            path = ""
                        type_ = int(type_)
                        raddr = None
                        status = _common.CONN_NONE
                        yield (fd, family, type_, path, raddr, status, pid)

    def retrieve(self, kind, pid=None):
        if kind not in self.tmap:
            raise ValueError("invalid %r kind argument; choose between %s"
                             % (kind, ', '.join([repr(x) for x in self.tmap])))
        self._procfs_path = get_procfs_path()
        if pid is not None:
            inodes = self.get_proc_inodes(pid)
            if not inodes:
                # no connections for this process
                return []
        else:
            inodes = self.get_all_inodes()
        ret = set()
        for f, family, type_ in self.tmap[kind]:
            if family in (socket.AF_INET, socket.AF_INET6):
                ls = self.process_inet(
                    "%s/net/%s" % (self._procfs_path, f),
                    family, type_, inodes, filter_pid=pid)
            else:
                ls = self.process_unix(
                    "%s/net/%s" % (self._procfs_path, f),
                    family, inodes, filter_pid=pid)
            for fd, family, type_, laddr, raddr, status, bound_pid in ls:
                if pid:
                    conn = _common.pconn(fd, family, type_, laddr, raddr,
                                         status)
                else:
                    conn = _common.sconn(fd, family, type_, laddr, raddr,
                                         status, bound_pid)
                ret.add(conn)
        return list(ret)


_connections = Connections()


def net_connections(kind='inet'):
    """Return system-wide open connections."""
    return _connections.retrieve(kind)


def net_io_counters():
    """Return network I/O statistics for every network interface
    installed on the system as a dict of raw tuples.
    """
    with open_text("%s/net/dev" % get_procfs_path()) as f:
        lines = f.readlines()
    retdict = {}
    for line in lines[2:]:
        colon = line.rfind(':')
        assert colon > 0, repr(line)
        name = line[:colon].strip()
        fields = line[colon + 1:].strip().split()
        bytes_recv = int(fields[0])
        packets_recv = int(fields[1])
        errin = int(fields[2])
        dropin = int(fields[3])
        bytes_sent = int(fields[8])
        packets_sent = int(fields[9])
        errout = int(fields[10])
        dropout = int(fields[11])
        retdict[name] = (bytes_sent, bytes_recv, packets_sent, packets_recv,
                         errin, errout, dropin, dropout)
    return retdict


def net_if_stats():
    """Get NIC stats (isup, duplex, speed, mtu)."""
    duplex_map = {cext.DUPLEX_FULL: NIC_DUPLEX_FULL,
                  cext.DUPLEX_HALF: NIC_DUPLEX_HALF,
                  cext.DUPLEX_UNKNOWN: NIC_DUPLEX_UNKNOWN}
    names = net_io_counters().keys()
    ret = {}
    for name in names:
        isup, duplex, speed, mtu = cext.net_if_stats(name)
        duplex = duplex_map[duplex]
        ret[name] = _common.snicstats(isup, duplex, speed, mtu)
    return ret


net_if_addrs = cext_posix.net_if_addrs


# --- disks

def disk_io_counters():
    """Return disk I/O statistics for every disk installed on the
    system as a dict of raw tuples.
    """
    # man iostat states that sectors are equivalent with blocks and
    # have a size of 512 bytes since 2.4 kernels. This value is
    # needed to calculate the amount of disk I/O in bytes.
    SECTOR_SIZE = 512

    # determine partitions we want to look for
    partitions = []
    with open_text("%s/partitions" % get_procfs_path()) as f:
        lines = f.readlines()[2:]
    for line in reversed(lines):
        _, _, _, name = line.split()
        if name[-1].isdigit():
            # we're dealing with a partition (e.g. 'sda1'); 'sda' will
            # also be around but we want to omit it
            partitions.append(name)
        else:
            if not partitions or not partitions[-1].startswith(name):
                # we're dealing with a disk entity for which no
                # partitions have been defined (e.g. 'sda' but
                # 'sda1' was not around), see:
                # https://github.com/giampaolo/psutil/issues/338
                partitions.append(name)
    #
    retdict = {}
    with open_text("%s/diskstats" % get_procfs_path()) as f:
        lines = f.readlines()
    for line in lines:
        # http://www.mjmwired.net/kernel/Documentation/iostats.txt
        fields = line.split()
        if len(fields) > 7:
            _, _, name, reads, _, rbytes, rtime, writes, _, wbytes, wtime = \
                fields[:11]
        else:
            # from kernel 2.6.0 to 2.6.25
            _, _, name, reads, rbytes, writes, wbytes = fields
            rtime, wtime = 0, 0
        if name in partitions:
            rbytes = int(rbytes) * SECTOR_SIZE
            wbytes = int(wbytes) * SECTOR_SIZE
            reads = int(reads)
            writes = int(writes)
            rtime = int(rtime)
            wtime = int(wtime)
            retdict[name] = (reads, writes, rbytes, wbytes, rtime, wtime)
    return retdict


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


disk_usage = _psposix.disk_usage


# --- decorators

def wrap_exceptions(fun):
    """Decorator which translates bare OSError and IOError exceptions
    into NoSuchProcess and AccessDenied.
    """
    @functools.wraps(fun)
    def wrapper(self, *args, **kwargs):
        try:
            return fun(self, *args, **kwargs)
        except EnvironmentError as err:
            # support for private module import
            if NoSuchProcess is None or AccessDenied is None:
                raise
            # ENOENT (no such file or directory) gets raised on open().
            # ESRCH (no such process) can get raised on read() if
            # process is gone in meantime.
            if err.errno in (errno.ENOENT, errno.ESRCH):
                raise NoSuchProcess(self.pid, self._name)
            if err.errno in (errno.EPERM, errno.EACCES):
                raise AccessDenied(self.pid, self._name)
            raise
    return wrapper


def wrap_exceptions_w_zombie(fun):
    """Same as above but also handles zombies."""
    @functools.wraps(fun)
    def wrapper(self, *args, **kwargs):
        try:
            return wrap_exceptions(fun)(self)
        except NoSuchProcess:
            if not pid_exists(self.pid):
                raise
            else:
                raise ZombieProcess(self.pid, self._name, self._ppid)
    return wrapper


class Process(object):
    """Linux process implementation."""

    __slots__ = ["pid", "_name", "_ppid", "_procfs_path"]

    def __init__(self, pid):
        self.pid = pid
        self._name = None
        self._ppid = None
        self._procfs_path = get_procfs_path()

    @wrap_exceptions
    def name(self):
        with open_text("%s/%s/stat" % (self._procfs_path, self.pid)) as f:
            data = f.read()
        # XXX - gets changed later and probably needs refactoring
        return data[data.find('(') + 1:data.rfind(')')]

    def exe(self):
        try:
            exe = os.readlink("%s/%s/exe" % (self._procfs_path, self.pid))
        except OSError as err:
            if err.errno in (errno.ENOENT, errno.ESRCH):
                # no such file error; might be raised also if the
                # path actually exists for system processes with
                # low pids (about 0-20)
                if os.path.lexists("%s/%s" % (self._procfs_path, self.pid)):
                    return ""
                else:
                    if not pid_exists(self.pid):
                        raise NoSuchProcess(self.pid, self._name)
                    else:
                        raise ZombieProcess(self.pid, self._name, self._ppid)
            if err.errno in (errno.EPERM, errno.EACCES):
                raise AccessDenied(self.pid, self._name)
            raise

        # readlink() might return paths containing null bytes ('\x00').
        # Certain names have ' (deleted)' appended. Usually this is
        # bogus as the file actually exists. Either way that's not
        # important as we don't want to discriminate executables which
        # have been deleted.
        exe = exe.split('\x00')[0]
        if exe.endswith(' (deleted)') and not os.path.exists(exe):
            exe = exe[:-10]
        return exe

    @wrap_exceptions
    def cmdline(self):
        with open_text("%s/%s/cmdline" % (self._procfs_path, self.pid)) as f:
            data = f.read()
        if data.endswith('\x00'):
            data = data[:-1]
        return [x for x in data.split('\x00')]

    @wrap_exceptions
    def terminal(self):
        tmap = _psposix._get_terminal_map()
        with open("%s/%s/stat" % (self._procfs_path, self.pid), 'rb') as f:
            tty_nr = int(f.read().split(b' ')[6])
        try:
            return tmap[tty_nr]
        except KeyError:
            return None

    if os.path.exists('/proc/%s/io' % os.getpid()):
        @wrap_exceptions
        def io_counters(self):
            fname = "%s/%s/io" % (self._procfs_path, self.pid)
            with open(fname, 'rb') as f:
                rcount = wcount = rbytes = wbytes = None
                for line in f:
                    if rcount is None and line.startswith(b"syscr"):
                        rcount = int(line.split()[1])
                    elif wcount is None and line.startswith(b"syscw"):
                        wcount = int(line.split()[1])
                    elif rbytes is None and line.startswith(b"read_bytes"):
                        rbytes = int(line.split()[1])
                    elif wbytes is None and line.startswith(b"write_bytes"):
                        wbytes = int(line.split()[1])
                for x in (rcount, wcount, rbytes, wbytes):
                    if x is None:
                        raise NotImplementedError(
                            "couldn't read all necessary info from %r" % fname)
                return _common.pio(rcount, wcount, rbytes, wbytes)
    else:
        def io_counters(self):
            raise NotImplementedError("couldn't find /proc/%s/io (kernel "
                                      "too old?)" % self.pid)

    @wrap_exceptions
    def cpu_times(self):
        with open("%s/%s/stat" % (self._procfs_path, self.pid), 'rb') as f:
            st = f.read().strip()
        # ignore the first two values ("pid (exe)")
        st = st[st.find(b')') + 2:]
        values = st.split(b' ')
        utime = float(values[11]) / CLOCK_TICKS
        stime = float(values[12]) / CLOCK_TICKS
        return _common.pcputimes(utime, stime)

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
    def create_time(self):
        with open("%s/%s/stat" % (self._procfs_path, self.pid), 'rb') as f:
            st = f.read().strip()
        # ignore the first two values ("pid (exe)")
        st = st[st.rfind(b')') + 2:]
        values = st.split(b' ')
        # According to documentation, starttime is in field 21 and the
        # unit is jiffies (clock ticks).
        # We first divide it for clock ticks and then add uptime returning
        # seconds since the epoch, in UTC.
        # Also use cached value if available.
        bt = BOOT_TIME or boot_time()
        return (float(values[19]) / CLOCK_TICKS) + bt

    @wrap_exceptions
    def memory_info(self):
        with open("%s/%s/statm" % (self._procfs_path, self.pid), 'rb') as f:
            vms, rss = f.readline().split()[:2]
            return _common.pmem(int(rss) * PAGESIZE,
                                int(vms) * PAGESIZE)

    @wrap_exceptions
    def memory_info_ex(self):
        #  ============================================================
        # | FIELD  | DESCRIPTION                         | AKA  | TOP  |
        #  ============================================================
        # | rss    | resident set size                   |      | RES  |
        # | vms    | total program size                  | size | VIRT |
        # | shared | shared pages (from shared mappings) |      | SHR  |
        # | text   | text ('code')                       | trs  | CODE |
        # | lib    | library (unused in Linux 2.6)       | lrs  |      |
        # | data   | data + stack                        | drs  | DATA |
        # | dirty  | dirty pages (unused in Linux 2.6)   | dt   |      |
        #  ============================================================
        with open("%s/%s/statm" % (self._procfs_path, self.pid), "rb") as f:
            vms, rss, shared, text, lib, data, dirty = \
                [int(x) * PAGESIZE for x in f.readline().split()[:7]]
        return pextmem(rss, vms, shared, text, lib, data, dirty)

    if os.path.exists('/proc/%s/smaps' % os.getpid()):

        @wrap_exceptions
        def memory_maps(self):
            """Return process's mapped memory regions as a list of named tuples.
            Fields are explained in 'man proc'; here is an updated (Apr 2012)
            version: http://goo.gl/fmebo
            """
            with open_text("%s/%s/smaps" % (self._procfs_path, self.pid)) as f:
                first_line = f.readline()
                current_block = [first_line]

                def get_blocks():
                    data = {}
                    for line in f:
                        fields = line.split(None, 5)
                        if not fields[0].endswith(':'):
                            # new block section
                            yield (current_block.pop(), data)
                            current_block.append(line)
                        else:
                            try:
                                data[fields[0]] = int(fields[1]) * 1024
                            except ValueError:
                                if fields[0].startswith('VmFlags:'):
                                    # see issue #369
                                    continue
                                else:
                                    raise ValueError("don't know how to inte"
                                                     "rpret line %r" % line)
                    yield (current_block.pop(), data)

                ls = []
                if first_line:  # smaps file can be empty
                    for header, data in get_blocks():
                        hfields = header.split(None, 5)
                        try:
                            addr, perms, offset, dev, inode, path = hfields
                        except ValueError:
                            addr, perms, offset, dev, inode, path = \
                                hfields + ['']
                        if not path:
                            path = '[anon]'
                        else:
                            path = path.strip()
                        ls.append((
                            addr, perms, path,
                            data['Rss:'],
                            data.get('Size:', 0),
                            data.get('Pss:', 0),
                            data.get('Shared_Clean:', 0),
                            data.get('Shared_Dirty:', 0),
                            data.get('Private_Clean:', 0),
                            data.get('Private_Dirty:', 0),
                            data.get('Referenced:', 0),
                            data.get('Anonymous:', 0),
                            data.get('Swap:', 0)
                        ))
            return ls

    else:
        def memory_maps(self):
            msg = "couldn't find /proc/%s/smaps; kernel < 2.6.14 or "  \
                  "CONFIG_MMU kernel configuration option is not enabled" \
                  % self.pid
            raise NotImplementedError(msg)

    @wrap_exceptions_w_zombie
    def cwd(self):
        # readlink() might return paths containing null bytes causing
        # problems when used with other fs-related functions (os.*,
        # open(), ...)
        path = os.readlink("%s/%s/cwd" % (self._procfs_path, self.pid))
        return path.replace('\x00', '')

    @wrap_exceptions
    def num_ctx_switches(self):
        vol = unvol = None
        with open("%s/%s/status" % (self._procfs_path, self.pid), "rb") as f:
            for line in f:
                if line.startswith(b"voluntary_ctxt_switches"):
                    vol = int(line.split()[1])
                elif line.startswith(b"nonvoluntary_ctxt_switches"):
                    unvol = int(line.split()[1])
                if vol is not None and unvol is not None:
                    return _common.pctxsw(vol, unvol)
            raise NotImplementedError(
                "'voluntary_ctxt_switches' and 'nonvoluntary_ctxt_switches'"
                "fields were not found in /proc/%s/status; the kernel is "
                "probably older than 2.6.23" % self.pid)

    @wrap_exceptions
    def num_threads(self):
        with open("%s/%s/status" % (self._procfs_path, self.pid), "rb") as f:
            for line in f:
                if line.startswith(b"Threads:"):
                    return int(line.split()[1])
            raise NotImplementedError("line not found")

    @wrap_exceptions
    def threads(self):
        thread_ids = os.listdir("%s/%s/task" % (self._procfs_path, self.pid))
        thread_ids.sort()
        retlist = []
        hit_enoent = False
        for thread_id in thread_ids:
            fname = "%s/%s/task/%s/stat" % (
                self._procfs_path, self.pid, thread_id)
            try:
                with open(fname, 'rb') as f:
                    st = f.read().strip()
            except IOError as err:
                if err.errno == errno.ENOENT:
                    # no such file or directory; it means thread
                    # disappeared on us
                    hit_enoent = True
                    continue
                raise
            # ignore the first two values ("pid (exe)")
            st = st[st.find(b')') + 2:]
            values = st.split(b' ')
            utime = float(values[11]) / CLOCK_TICKS
            stime = float(values[12]) / CLOCK_TICKS
            ntuple = _common.pthread(int(thread_id), utime, stime)
            retlist.append(ntuple)
        if hit_enoent:
            # raise NSP if the process disappeared on us
            os.stat('%s/%s' % (self._procfs_path, self.pid))
        return retlist

    @wrap_exceptions
    def nice_get(self):
        # with open_text('%s/%s/stat' % (self._procfs_path, self.pid)) as f:
        #   data = f.read()
        #   return int(data.split()[18])

        # Use C implementation
        return cext_posix.getpriority(self.pid)

    @wrap_exceptions
    def nice_set(self, value):
        return cext_posix.setpriority(self.pid, value)

    @wrap_exceptions
    def cpu_affinity_get(self):
        return cext.proc_cpu_affinity_get(self.pid)

    @wrap_exceptions
    def cpu_affinity_set(self, cpus):
        try:
            cext.proc_cpu_affinity_set(self.pid, cpus)
        except OSError as err:
            if err.errno == errno.EINVAL:
                allcpus = tuple(range(len(per_cpu_times())))
                for cpu in cpus:
                    if cpu not in allcpus:
                        raise ValueError("invalid CPU #%i (choose between %s)"
                                         % (cpu, allcpus))
            raise

    # only starting from kernel 2.6.13
    if hasattr(cext, "proc_ioprio_get"):

        @wrap_exceptions
        def ionice_get(self):
            ioclass, value = cext.proc_ioprio_get(self.pid)
            if enum is not None:
                ioclass = IOPriority(ioclass)
            return _common.pionice(ioclass, value)

        @wrap_exceptions
        def ionice_set(self, ioclass, value):
            if value is not None:
                if not PY3 and not isinstance(value, (int, long)):
                    msg = "value argument is not an integer (gor %r)" % value
                    raise TypeError(msg)
                if not 0 <= value <= 7:
                    raise ValueError(
                        "value argument range expected is between 0 and 7")

            if ioclass in (IOPRIO_CLASS_NONE, None):
                if value:
                    msg = "can't specify value with IOPRIO_CLASS_NONE " \
                          "(got %r)" % value
                    raise ValueError(msg)
                ioclass = IOPRIO_CLASS_NONE
                value = 0
            elif ioclass == IOPRIO_CLASS_IDLE:
                if value:
                    msg = "can't specify value with IOPRIO_CLASS_IDLE " \
                          "(got %r)" % value
                    raise ValueError(msg)
                value = 0
            elif ioclass in (IOPRIO_CLASS_RT, IOPRIO_CLASS_BE):
                if value is None:
                    # TODO: add comment explaining why this is 4 (?)
                    value = 4
            else:
                # otherwise we would get OSError(EVINAL)
                raise ValueError("invalid ioclass argument %r" % ioclass)

            return cext.proc_ioprio_set(self.pid, ioclass, value)

    if HAS_PRLIMIT:
        @wrap_exceptions
        def rlimit(self, resource, limits=None):
            # If pid is 0 prlimit() applies to the calling process and
            # we don't want that. We should never get here though as
            # PID 0 is not supported on Linux.
            if self.pid == 0:
                raise ValueError("can't use prlimit() against PID 0 process")
            try:
                if limits is None:
                    # get
                    return cext.linux_prlimit(self.pid, resource)
                else:
                    # set
                    if len(limits) != 2:
                        raise ValueError(
                            "second argument must be a (soft, hard) tuple, "
                            "got %s" % repr(limits))
                    soft, hard = limits
                    cext.linux_prlimit(self.pid, resource, soft, hard)
            except OSError as err:
                if err.errno == errno.ENOSYS and pid_exists(self.pid):
                    # I saw this happening on Travis:
                    # https://travis-ci.org/giampaolo/psutil/jobs/51368273
                    raise ZombieProcess(self.pid, self._name, self._ppid)
                else:
                    raise

    @wrap_exceptions
    def status(self):
        with open("%s/%s/status" % (self._procfs_path, self.pid), 'rb') as f:
            for line in f:
                if line.startswith(b"State:"):
                    letter = line.split()[1]
                    if PY3:
                        letter = letter.decode()
                    # XXX is '?' legit? (we're not supposed to return
                    # it anyway)
                    return PROC_STATUSES.get(letter, '?')

    @wrap_exceptions
    def open_files(self):
        retlist = []
        files = os.listdir("%s/%s/fd" % (self._procfs_path, self.pid))
        hit_enoent = False
        for fd in files:
            file = "%s/%s/fd/%s" % (self._procfs_path, self.pid, fd)
            try:
                file = os.readlink(file)
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
                # If file is not an absolute path there's no way
                # to tell whether it's a regular file or not,
                # so we skip it. A regular file is always supposed
                # to be absolutized though.
                if file.startswith('/') and isfile_strict(file):
                    ntuple = _common.popenfile(file, int(fd))
                    retlist.append(ntuple)
        if hit_enoent:
            # raise NSP if the process disappeared on us
            os.stat('%s/%s' % (self._procfs_path, self.pid))
        return retlist

    @wrap_exceptions
    def connections(self, kind='inet'):
        ret = _connections.retrieve(kind, self.pid)
        # raise NSP if the process disappeared on us
        os.stat('%s/%s' % (self._procfs_path, self.pid))
        return ret

    @wrap_exceptions
    def num_fds(self):
        return len(os.listdir("%s/%s/fd" % (self._procfs_path, self.pid)))

    @wrap_exceptions
    def ppid(self):
        fpath = "%s/%s/status" % (self._procfs_path, self.pid)
        with open(fpath, 'rb') as f:
            for line in f:
                if line.startswith(b"PPid:"):
                    # PPid: nnnn
                    return int(line.split()[1])
            raise NotImplementedError("line 'PPid' not found in %s" % fpath)

    @wrap_exceptions
    def uids(self):
        fpath = "%s/%s/status" % (self._procfs_path, self.pid)
        with open(fpath, 'rb') as f:
            for line in f:
                if line.startswith(b'Uid:'):
                    _, real, effective, saved, fs = line.split()
                    return _common.puids(int(real), int(effective), int(saved))
            raise NotImplementedError("line 'Uid' not found in %s" % fpath)

    @wrap_exceptions
    def gids(self):
        fpath = "%s/%s/status" % (self._procfs_path, self.pid)
        with open(fpath, 'rb') as f:
            for line in f:
                if line.startswith(b'Gid:'):
                    _, real, effective, saved, fs = line.split()
                    return _common.pgids(int(real), int(effective), int(saved))
            raise NotImplementedError("line 'Gid' not found in %s" % fpath)
