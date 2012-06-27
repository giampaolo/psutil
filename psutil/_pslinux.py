#!/usr/bin/env python
#
# $Id$
#
# Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Linux platform implementation."""

from __future__ import division

import os
import errno
import socket
import struct
import sys
import base64
import re

import _psutil_posix
import _psutil_linux
from psutil import _psposix
from psutil.error import AccessDenied, NoSuchProcess, TimeoutExpired
from psutil._common import *
from psutil._compat import PY3, xrange, long

__extra__all__ = [
    "IOPRIO_CLASS_NONE", "IOPRIO_CLASS_RT", "IOPRIO_CLASS_BE",
    "IOPRIO_CLASS_IDLE",
    "phymem_buffers", "cached_phymem"]


def _get_boot_time():
    """Return system boot time (epoch in seconds)"""
    f = open('/proc/stat', 'r')
    try:
        for line in f:
            if line.startswith('btime'):
                return float(line.strip().split()[1])
        raise RuntimeError("line not found")
    finally:
        f.close()

def _get_num_cpus():
    """Return the number of CPUs on the system"""
    # we try to determine num CPUs by using different approaches.
    # SC_NPROCESSORS_ONLN seems to be the safer and it is also
    # used by multiprocessing module
    try:
        return os.sysconf("SC_NPROCESSORS_ONLN")
    except ValueError:
        # as a second fallback we try to parse /proc/cpuinfo
        num = 0
        f = open('/proc/cpuinfo', 'r')
        try:
            lines = f.readlines()
        finally:
            f.close()
        for line in lines:
            if line.lower().startswith('processor'):
                num += 1

    # unknown format (e.g. amrel/sparc architectures), see:
    # http://code.google.com/p/psutil/issues/detail?id=200
    # try to parse /proc/stat as a last resort
    if num == 0:
        f = open('/proc/stat', 'r')
        try:
            lines = f.readlines()
        finally:
            f.close()
        search = re.compile('cpu\d')
        for line in lines:
            line = line.split(' ')[0]
            if search.match(line):
                num += 1

    if num == 0:
        raise RuntimeError("can't determine number of CPUs")
    return num


# Number of clock ticks per second
_CLOCK_TICKS = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
_PAGESIZE = os.sysconf("SC_PAGE_SIZE")
_TERMINAL_MAP = _psposix._get_terminal_map()
BOOT_TIME = _get_boot_time()
NUM_CPUS = _get_num_cpus()
# ioprio_* constants http://linux.die.net/man/2/ioprio_get
IOPRIO_CLASS_NONE = 0
IOPRIO_CLASS_RT = 1
IOPRIO_CLASS_BE = 2
IOPRIO_CLASS_IDLE = 3

# http://students.mimuw.edu.pl/lxr/source/include/net/tcp_states.h
_TCP_STATES_TABLE = {"01" : "ESTABLISHED",
                     "02" : "SYN_SENT",
                     "03" : "SYN_RECV",
                     "04" : "FIN_WAIT1",
                     "05" : "FIN_WAIT2",
                     "06" : "TIME_WAIT",
                     "07" : "CLOSE",
                     "08" : "CLOSE_WAIT",
                     "09" : "LAST_ACK",
                     "0A" : "LISTEN",
                     "0B" : "CLOSING"
                     }

# --- system memory functions

def cached_phymem():
    """Return the amount of cached memory on the system, in bytes.
    This reflects the "cached" column of free command line utility.
    """
    f = open('/proc/meminfo', 'r')
    try:
        for line in f:
            if line.startswith('Cached:'):
                return int(line.split()[1]) * 1024
        raise RuntimeError("line not found")
    finally:
        f.close()

def phymem_buffers():
    """Return the amount of physical memory buffers used by the
    kernel in bytes.
    This reflects the "buffers" column of free command line utility.
    """
    total, free, buffers = _psutil_linux.get_physmem()
    return buffers

def phymem_usage():
    """Return physical memory usage statistics as a namedutple including
    tota, used, free and percent usage.
    """
    # total, used and free values are matched against free cmdline utility
    # the percentage matches top/htop and gnome-system-monitor
    total, free, buffers = _psutil_linux.get_physmem()
    cached = cached_phymem()
    used = total - free
    percent = usage_percent(total - (free + buffers + cached), total, _round=1)
    return nt_sysmeminfo(total, used, free, percent)


def virtmem_usage():
    f = open('/proc/meminfo', 'r')
    try:
        total = free = None
        for line in f:
            if line.startswith('SwapTotal:'):
                total = int(line.split()[1]) * 1024
            elif line.startswith('SwapFree:'):
                free = int(line.split()[1]) * 1024
            if total is not None and free is not None:
                break
        assert total is not None and free is not None
        used = total - free
        percent = usage_percent(used, total, _round=1)
        return nt_sysmeminfo(total, used, free, percent)
    finally:
        f.close()


# --- system CPU functions

def get_system_cpu_times():
    """Return a named tuple representing the following CPU times:
    user, nice, system, idle, iowait, irq, softirq.
    """
    f = open('/proc/stat', 'r')
    try:
        values = f.readline().split()
    finally:
        f.close()

    values = values[1:8]
    values = tuple([float(x) / _CLOCK_TICKS for x in values])
    return nt_sys_cputimes(*values[:7])

def get_system_per_cpu_times():
    """Return a list of namedtuple representing the CPU times
    for every CPU available on the system.
    """
    cpus = []
    f = open('/proc/stat', 'r')
    # get rid of the first line who refers to system wide CPU stats
    try:
        f.readline()
        for line in f.readlines():
            if line.startswith('cpu'):
                values = line.split()[1:8]
                values = tuple([float(x) / _CLOCK_TICKS for x in values])
                entry = nt_sys_cputimes(*values[:7])
                cpus.append(entry)
        return cpus
    finally:
        f.close()


# --- system disk functions

def disk_partitions(all=False):
    """Return mounted disk partitions as a list of nameduples"""
    phydevs = []
    f = open("/proc/filesystems", "r")
    try:
        for line in f:
            if not line.startswith("nodev"):
                phydevs.append(line.strip())
    finally:
        f.close()

    retlist = []
    partitions = _psutil_linux.get_disk_partitions()
    for partition in partitions:
        device, mountpoint, fstype, opts = partition
        if device == 'none':
            device = ''
        if not all:
            if device == '' or fstype not in phydevs:
                continue
        ntuple = nt_partition(device, mountpoint, fstype, opts)
        retlist.append(ntuple)
    return retlist

get_disk_usage = _psposix.get_disk_usage


# --- other sysetm functions

def get_system_users():
    """Return currently connected users as a list of namedtuples."""
    retlist = []
    rawlist = _psutil_linux.get_system_users()
    for item in rawlist:
        user, tty, hostname, tstamp, user_process = item
        # XXX the underlying C function includes entries about
        # system boot, run level and others.  We might want
        # to use them in the future.
        if not user_process:
            continue
        if hostname == ':0.0':
            hostname = 'localhost'
        nt = nt_user(user, tty or None, hostname, tstamp)
        retlist.append(nt)
    return retlist

# --- process functions

def get_pid_list():
    """Returns a list of PIDs currently running on the system."""
    pids = [int(x) for x in os.listdir('/proc') if x.isdigit()]
    return pids

def pid_exists(pid):
    """Check For the existence of a unix pid."""
    return _psposix.pid_exists(pid)

def network_io_counters():
    """Return network I/O statistics for every network interface
    installed on the system as a dict of raw tuples.
    """
    f = open("/proc/net/dev", "r")
    try:
        lines = f.readlines()
    finally:
        f.close()

    retdict = {}
    for line in lines[2:]:
        colon = line.find(':')
        assert colon > 0, line
        name = line[:colon].strip()
        fields = line[colon+1:].strip().split()
        bytes_recv = int(fields[0])
        packets_recv = int(fields[1])
        bytes_sent = int(fields[8])
        packets_sent = int(fields[9])
        retdict[name] = (bytes_sent, bytes_recv, packets_sent, packets_recv)
    return retdict

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
    f = open("/proc/partitions", "r")
    try:
        lines = f.readlines()[2:]
    finally:
        f.close()
    for line in lines:
        _, _, _, name = line.split()
        if name[-1].isdigit():
            partitions.append(name)
    #
    retdict = {}
    f = open("/proc/diskstats", "r")
    try:
        lines = f.readlines()
    finally:
        f.close()
    for line in lines:
        _, _, name, reads, _, rbytes, rtime, writes, _, wbytes, wtime = \
            line.split()[:11]
        if name in partitions:
            rbytes = int(rbytes) * SECTOR_SIZE
            wbytes = int(wbytes) * SECTOR_SIZE
            reads = int(reads)
            writes = int(writes)
            # TODO: times are expressed in milliseconds while OSX/BSD has
            # these expressed in nanoseconds; figure this out.
            rtime = int(rtime)
            wtime = int(wtime)
            retdict[name] = (reads, writes, rbytes, wbytes, rtime, wtime)
    return retdict


# taken from /fs/proc/array.c
_status_map = {"R" : STATUS_RUNNING,
               "S" : STATUS_SLEEPING,
               "D" : STATUS_DISK_SLEEP,
               "T" : STATUS_STOPPED,
               "t" : STATUS_TRACING_STOP,
               "Z" : STATUS_ZOMBIE,
               "X" : STATUS_DEAD,
               "x" : STATUS_DEAD,
               "K" : STATUS_WAKE_KILL,
               "W" : STATUS_WAKING}

# --- decorators

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


class Process(object):
    """Linux process implementation."""

    __slots__ = ["pid", "_process_name"]

    def __init__(self, pid):
        if not isinstance(pid, int):
            raise TypeError('pid must be an integer')
        self.pid = pid
        self._process_name = None

    @wrap_exceptions
    def get_process_name(self):
        f = open("/proc/%s/stat" % self.pid)
        try:
            name = f.read().split(' ')[1].replace('(', '').replace(')', '')
        finally:
            f.close()
        # XXX - gets changed later and probably needs refactoring
        return name

    def get_process_exe(self):
        if self.pid in (0, 2):
            raise AccessDenied(self.pid, self._process_name)
        try:
            exe = os.readlink("/proc/%s/exe" % self.pid)
        except (OSError, IOError):
            err = sys.exc_info()[1]
            if err.errno == errno.ENOENT:
                # no such file error; might be raised also if the
                # path actually exists for system processes with
                # low pids (about 0-20)
                if os.path.lexists("/proc/%s/exe" % self.pid):
                    return ""
                else:
                    # ok, it is a process which has gone away
                    raise NoSuchProcess(self.pid, self._process_name)
            if err.errno in (errno.EPERM, errno.EACCES):
                raise AccessDenied(self.pid, self._process_name)
            raise

        # readlink() might return paths containing null bytes causing
        # problems when used with other fs-related functions (os.*,
        # open(), ...)
        exe = exe.replace('\x00', '')
        # It seems symlinks can point to a deleted/invalid location
        # (this usually  happens with "pulseaudio" process).
        # However, if we had permissions to execute readlink() it's
        # likely that we'll be able to figure out exe from argv[0]
        # later on.
        if exe.endswith(" (deleted)") and not os.path.isfile(exe):
            return ""
        return exe

    @wrap_exceptions
    def get_process_cmdline(self):
        f = open("/proc/%s/cmdline" % self.pid)
        try:
            # return the args as a list
            return [x for x in f.read().split('\x00') if x]
        finally:
            f.close()

    @wrap_exceptions
    def get_process_terminal(self):
        f = open("/proc/%s/stat" % self.pid)
        try:
            tty_nr = int(f.read().split(' ')[6])
        finally:
            f.close()
        try:
            return _TERMINAL_MAP[tty_nr]
        except KeyError:
            return None

    @wrap_exceptions
    def get_process_io_counters(self):
        f = open("/proc/%s/io" % self.pid)
        try:
            for line in f:
                if line.startswith("rchar"):
                    read_count = int(line.split()[1])
                elif line.startswith("wchar"):
                    write_count = int(line.split()[1])
                elif line.startswith("read_bytes"):
                    read_bytes = int(line.split()[1])
                elif line.startswith("write_bytes"):
                    write_bytes = int(line.split()[1])
            return nt_io(read_count, write_count, read_bytes, write_bytes)
        finally:
            f.close()

    if not os.path.exists('/proc/%s/io' % os.getpid()):
        def get_process_io_counters(self):
            raise NotImplementedError('/proc/PID/io is not available')

    @wrap_exceptions
    def get_cpu_times(self):
        f = open("/proc/%s/stat" % self.pid)
        try:
            st = f.read().strip()
        finally:
            f.close()
        # ignore the first two values ("pid (exe)")
        st = st[st.find(')') + 2:]
        values = st.split(' ')
        utime = float(values[11]) / _CLOCK_TICKS
        stime = float(values[12]) / _CLOCK_TICKS
        return nt_cputimes(utime, stime)

    @wrap_exceptions
    def process_wait(self, timeout=None):
        try:
            return _psposix.wait_pid(self.pid, timeout)
        except TimeoutExpired:
            raise TimeoutExpired(self.pid, self._process_name)

    @wrap_exceptions
    def get_process_create_time(self):
        f = open("/proc/%s/stat" % self.pid)
        try:
            st = f.read().strip()
        finally:
            f.close()
        # ignore the first two values ("pid (exe)")
        st = st[st.rfind(')') + 2:]
        values = st.split(' ')
        # According to documentation, starttime is in field 21 and the
        # unit is jiffies (clock ticks).
        # We first divide it for clock ticks and then add uptime returning
        # seconds since the epoch, in UTC.
        starttime = (float(values[19]) / _CLOCK_TICKS) + BOOT_TIME
        return starttime

    @wrap_exceptions
    def get_memory_info(self):
        f = open("/proc/%s/statm" % self.pid)
        try:
            vms, rss = f.readline().split()[:2]
            return nt_meminfo(int(rss) * _PAGESIZE,
                              int(vms) * _PAGESIZE)
        finally:
            f.close()

    _mmap_base_fields = ['path', 'rss', 'size', 'pss', 'shared_clean',
                         'shared_dirty', 'private_clean', 'private_dirty',
                         'referenced', 'anonymous', 'swap',]
    nt_mmap_grouped = namedtuple('mmap', ' '.join(_mmap_base_fields))
    nt_mmap_ext = namedtuple('mmap', 'addr perms ' + ' '.join(_mmap_base_fields))

    def get_memory_maps(self):
        """Return process's mapped memory regions as a list of nameduples.
        Fields are explained in 'man proc'; here is an updated (Apr 2012)
        version: http://goo.gl/fmebo
        """
        f = None
        try:
            f = open("/proc/%s/smaps" % self.pid)
            first_line = f.readline()
            current_block = [first_line]

            def get_blocks():
                data = {}
                for line in f:
                    fields = line.split(None, 5)
                    if len(fields) >= 5:
                        yield (current_block.pop(), data)
                        current_block.append(line)
                    else:
                        data[fields[0]] = int(fields[1]) * 1024
                yield (current_block.pop(), data)

            if first_line:  # smaps file can be empty
                for header, data in get_blocks():
                    hfields = header.split(None, 5)
                    try:
                        addr, perms, offset, dev, inode, path = hfields
                    except ValueError:
                        addr, perms, offset, dev, inode, path = hfields + ['']
                    if not path:
                        path = '[anon]'
                    else:
                        path = path.strip()
                    yield (addr, perms, path,
                           data['Rss:'],
                           data['Size:'],
                           data.get('Pss:', 0),
                           data['Shared_Clean:'], data['Shared_Clean:'],
                           data['Private_Clean:'], data['Private_Dirty:'],
                           data['Referenced:'],
                           data['Anonymous:'],
                           data['Swap:'])
            f.close()
        except EnvironmentError:
            # XXX - Can't use wrap_exceptions decorator as we're
            # returning a generator;  this probably needs some
            # refactoring in order to avoid this code duplication.
            if f is not None:
                f.close()
            err = sys.exc_info()[1]
            if err.errno in (errno.ENOENT, errno.ESRCH):
                raise NoSuchProcess(self.pid, self._process_name)
            if err.errno in (errno.EPERM, errno.EACCES):
                raise AccessDenied(self.pid, self._process_name)
            raise
        except:
            if f is not None:
                f.close()
            raise

    if not os.path.exists('/proc/%s/smaps' % os.getpid()):
        def get_shared_libs(self, ext):
            msg = "this Linux version does not support /proc/PID/smaps " \
                  "(kernel < 2.6.14 or CONFIG_MMU kernel configuration " \
                  "option is not enabled)"
            raise NotImplementedError(msg)

    @wrap_exceptions
    def get_process_cwd(self):
        # readlink() might return paths containing null bytes causing
        # problems when used with other fs-related functions (os.*,
        # open(), ...)
        path = os.readlink("/proc/%s/cwd" % self.pid)
        return path.replace('\x00', '')

    @wrap_exceptions
    def get_process_num_threads(self):
        f = open("/proc/%s/status" % self.pid)
        try:
            for line in f:
                if line.startswith("Threads:"):
                    return int(line.split()[1])
            raise RuntimeError("line not found")
        finally:
            f.close()

    @wrap_exceptions
    def get_process_threads(self):
        thread_ids = os.listdir("/proc/%s/task" % self.pid)
        thread_ids.sort()
        retlist = []
        for thread_id in thread_ids:
            try:
                f = open("/proc/%s/task/%s/stat" % (self.pid, thread_id))
            except EnvironmentError:
                err = sys.exc_info()[1]
                if err.errno == errno.ENOENT:
                    # no such file or directory; it means thread
                    # disappeared on us
                    continue
                raise
            try:
                st = f.read().strip()
            finally:
                f.close()
            # ignore the first two values ("pid (exe)")
            st = st[st.find(')') + 2:]
            values = st.split(' ')
            utime = float(values[11]) / _CLOCK_TICKS
            stime = float(values[12]) / _CLOCK_TICKS
            ntuple = nt_thread(int(thread_id), utime, stime)
            retlist.append(ntuple)
        return retlist

    @wrap_exceptions
    def get_process_nice(self):
        #f = open('/proc/%s/stat' % self.pid, 'r')
        #try:
        #   data = f.read()
        #   return int(data.split()[18])
        #finally:
        #   f.close()

        # Use C implementation
        return _psutil_posix.getpriority(self.pid)

    @wrap_exceptions
    def set_process_nice(self, value):
        return _psutil_posix.setpriority(self.pid, value)

    @wrap_exceptions
    def get_process_cpu_affinity(self):
        from_bitmask = lambda x: [i for i in xrange(64) if (1 << i) & x]
        bitmask = _psutil_linux.get_process_cpu_affinity(self.pid)
        return from_bitmask(bitmask)

    @wrap_exceptions
    def set_process_cpu_affinity(self, value):
        def to_bitmask(l):
            if not l:
                raise ValueError("invalid argument %r" % l)
            out = 0
            for b in l:
                if not isinstance(b, (int, long)) or b < 0:
                    raise ValueError("invalid argument %r" % b)
                out |= 2**b
            return out

        bitmask = to_bitmask(value)
        try:
            _psutil_linux.set_process_cpu_affinity(self.pid, bitmask)
        except OSError:
            err = sys.exc_info()[1]
            if err.errno == errno.EINVAL:
                allcpus = list(range(len(get_system_per_cpu_times())))
                for cpu in value:
                    if cpu not in allcpus:
                        raise ValueError("invalid CPU %i" % cpu)
            raise

    # only starting from kernel 2.6.13
    if hasattr(_psutil_linux, "ioprio_get"):

        @wrap_exceptions
        def get_process_ionice(self):
            ioclass, value = _psutil_linux.ioprio_get(self.pid)
            return nt_ionice(ioclass, value)

        @wrap_exceptions
        def set_process_ionice(self, ioclass, value):
            if ioclass in (IOPRIO_CLASS_NONE, None):
                if value:
                    raise ValueError("can't specify value with IOPRIO_CLASS_NONE")
                ioclass = IOPRIO_CLASS_NONE
                value = 0
            if ioclass in (IOPRIO_CLASS_RT, IOPRIO_CLASS_BE):
                if value is None:
                    value = 4
            elif ioclass == IOPRIO_CLASS_IDLE:
                if value:
                    raise ValueError("can't specify value with IOPRIO_CLASS_IDLE")
                value = 0
            else:
                value = 0
            if not 0 <= value <= 8:
                raise ValueError("value argument range expected is between 0 and 8")
            return _psutil_linux.ioprio_set(self.pid, ioclass, value)

    @wrap_exceptions
    def get_process_status(self):
        f = open("/proc/%s/status" % self.pid)
        try:
            for line in f:
                if line.startswith("State:"):
                    letter = line.split()[1]
                    if letter in _status_map:
                        return _status_map[letter]
                    return constant(-1, '?')
        finally:
            f.close()

    @wrap_exceptions
    def get_open_files(self):
        retlist = []
        files = os.listdir("/proc/%s/fd" % self.pid)
        for fd in files:
            file = "/proc/%s/fd/%s" % (self.pid, fd)
            if os.path.islink(file):
                try:
                    file = os.readlink(file)
                except OSError:
                    # ENOENT == file which is gone in the meantime
                    err = sys.exc_info()[1]
                    if err.errno != errno.ENOENT:
                        raise
                else:
                    # If file is not an absolute path there's no way
                    # to tell whether it's a regular file or not,
                    # so we skip it. A regular file is always supposed
                    # to be absolutized though.
                    if file.startswith('/') and os.path.isfile(file):
                        ntuple = nt_openfile(file, int(fd))
                        retlist.append(ntuple)
        return retlist

    @wrap_exceptions
    def get_connections(self, kind='inet'):
        """Return connections opened by process as a list of namedtuples.
        The kind parameter filters for connections that fit the following
        criteria:

        Kind Value      Number of connections using
        inet            IPv4 and IPv6
        inet4           IPv4
        inet6           IPv6
        tcp             TCP
        tcp4            TCP over IPv4
        tcp6            TCP over IPv6
        udp             UDP
        udp4            UDP over IPv4
        udp6            UDP over IPv6
        all             the sum of all the possible families and protocols
        """
        inodes = {}
        # os.listdir() is gonna raise a lot of access denied
        # exceptions in case of unprivileged user; that's fine:
        # lsof does the same so it's unlikely that we can to better.
        for fd in os.listdir("/proc/%s/fd" % self.pid):
            try:
                inode = os.readlink("/proc/%s/fd/%s" % (self.pid, fd))
            except OSError:
                continue
            if inode.startswith('socket:['):
                # the process is using a socket
                inode = inode[8:][:-1]
                inodes[inode] = fd

        if not inodes:
            # no connections for this process
            return []

        def process(file, family, type_):
            retlist = []
            try:
                f = open(file, 'r')
            except IOError:
                # IPv6 not supported on this platform
                err = sys.exc_info()[1]
                if err.errno == errno.ENOENT and file.endswith('6'):
                    return []
                else:
                    raise
            try:
                f.readline()  # skip the first line
                for line in f:
                    # IPv4 / IPv6
                    if family in (socket.AF_INET, socket.AF_INET6):
                        _, laddr, raddr, status, _, _, _, _, _, inode = \
                                                                line.split()[:10]
                        if inode in inodes:
                            laddr = self._decode_address(laddr, family)
                            raddr = self._decode_address(raddr, family)
                            if type_ == socket.SOCK_STREAM:
                                status = _TCP_STATES_TABLE[status]
                            else:
                                status = ""
                            fd = int(inodes[inode])
                            conn = nt_connection(fd, family, type_, laddr,
                                                 raddr, status)
                            retlist.append(conn)
                    else:
                        raise ValueError(family)
                return retlist
            finally:
                f.close()

        tcp4 = ("tcp" , socket.AF_INET , socket.SOCK_STREAM)
        tcp6 = ("tcp6", socket.AF_INET6, socket.SOCK_STREAM)
        udp4 = ("udp" , socket.AF_INET , socket.SOCK_DGRAM)
        udp6 = ("udp6", socket.AF_INET6, socket.SOCK_DGRAM)

        tmap = {
            "all"  : (tcp4, tcp6, udp4, udp6),
            "tcp"  : (tcp4, tcp6),
            "tcp4" : (tcp4,),
            "tcp6" : (tcp6,),
            "udp"  : (udp4, udp6),
            "udp4" : (udp4,),
            "udp6" : (udp6,),
            "inet" : (tcp4, tcp6, udp4, udp6),
            "inet4": (tcp4, udp4),
            "inet6": (tcp6, udp6),
        }
        if kind not in tmap:
            raise ValueError("invalid %r kind argument; choose between %s"
                             % (kind, ', '.join([repr(x) for x in tmap])))
        ret = []
        for f, family, type_ in tmap[kind]:
            ret += process("/proc/net/%s" % f, family, type_)
        return ret


#    --- lsof implementation
#
#    def get_connections(self):
#        lsof = _psposix.LsofParser(self.pid, self._process_name)
#        return lsof.get_process_connections()

    @wrap_exceptions
    def get_num_fds(self):
       return len(os.listdir("/proc/%s/fd" % self.pid))

    @wrap_exceptions
    def get_process_ppid(self):
        f = open("/proc/%s/status" % self.pid)
        try:
            for line in f:
                if line.startswith("PPid:"):
                    # PPid: nnnn
                    return int(line.split()[1])
            raise RuntimeError("line not found")
        finally:
            f.close()

    @wrap_exceptions
    def get_process_uids(self):
        f = open("/proc/%s/status" % self.pid)
        try:
            for line in f:
                if line.startswith('Uid:'):
                    _, real, effective, saved, fs = line.split()
                    return nt_uids(int(real), int(effective), int(saved))
            raise RuntimeError("line not found")
        finally:
            f.close()

    @wrap_exceptions
    def get_process_gids(self):
        f = open("/proc/%s/status" % self.pid)
        try:
            for line in f:
                if line.startswith('Gid:'):
                    _, real, effective, saved, fs = line.split()
                    return nt_gids(int(real), int(effective), int(saved))
            raise RuntimeError("line not found")
        finally:
            f.close()

    @staticmethod
    def _decode_address(addr, family):
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
        if PY3:
            ip = ip.encode('ascii')
        # this usually refers to a local socket in listen mode with
        # no end-points connected
        if not port:
            return ()
        if family == socket.AF_INET:
            # see: http://code.google.com/p/psutil/issues/detail?id=201
            if sys.byteorder == 'little':
                ip = socket.inet_ntop(family, base64.b16decode(ip)[::-1])
            else:
                ip = socket.inet_ntop(family, base64.b16decode(ip))
        else:  # IPv6
            # old version - let's keep it, just in case...
            #ip = ip.decode('hex')
            #return socket.inet_ntop(socket.AF_INET6,
            #          ''.join(ip[i:i+4][::-1] for i in xrange(0, 16, 4)))
            ip = base64.b16decode(ip)
            # see: http://code.google.com/p/psutil/issues/detail?id=201
            if sys.byteorder == 'little':
                ip = socket.inet_ntop(socket.AF_INET6,
                                struct.pack('>4I', *struct.unpack('<4I', ip)))
            else:
                ip = socket.inet_ntop(socket.AF_INET6,
                                struct.pack('<4I', *struct.unpack('<4I', ip)))
        return (ip, port)
