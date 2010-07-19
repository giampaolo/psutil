#!/usr/bin/env python
#
# $Id$
#

import os
import signal
import errno
import pwd
import grp
import socket
import struct
import sys
import base64

try:
    from collections import namedtuple
except ImportError:
    from compat import namedtuple  # python < 2.6

import _psposix
from psutil.error import *


def _get_uptime():
    """Return system boot time (epoch in seconds)"""
    f = open('/proc/stat', 'r')
    for line in f:
        if line.startswith('btime'):
            f.close()
            return float(line.strip().split()[1])

def _get_num_cpus():
    """Return the number of CPUs on the system"""
    num = 0
    f = open('/proc/cpuinfo', 'r')
    for line in f:
        if line.startswith('processor'):
            num += 1
    f.close()
    return num

def _get_total_phymem():
    """Return the total amount of physical memory, in bytes"""
    f = open('/proc/meminfo', 'r')
    for line in f:
        if line.startswith('MemTotal:'):
            f.close()
            return int(line.split()[1]) * 1024


# Number of clock ticks per second
_CLOCK_TICKS = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
_UPTIME = _get_uptime()
NUM_CPUS = _get_num_cpus()
TOTAL_PHYMEM = _get_total_phymem()

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

def avail_phymem():
    """Return the amount of physical memory available, in bytes."""
    f = open('/proc/meminfo', 'r')
    free = None
    _flag = False
    for line in f:
        if line.startswith('MemFree:'):
            free = int(line.split()[1]) * 1024
            break
    f.close()
    return free

def used_phymem():
    """"Return the amount of physical memory used, in bytes."""
    return (TOTAL_PHYMEM - avail_phymem())

def total_virtmem():
    """"Return the total amount of virtual memory, in bytes."""
    f = open('/proc/meminfo', 'r')
    for line in f:
        if line.startswith('SwapTotal:'):
            f.close()
            return int(line.split()[1]) * 1024

def avail_virtmem():
    """Return the amount of virtual memory currently in use on the system, in bytes."""
    f = open('/proc/meminfo', 'r')
    for line in f:
        if line.startswith('SwapFree:'):
            f.close()
            return int(line.split()[1]) * 1024

def used_virtmem():
    """Return the amount of used memory currently in use on the system, in bytes."""
    return total_virtmem() - avail_virtmem()

def cached_mem():
    """Return the amount of cached memory on the system, in bytes."""
    f = open('/proc/meminfo', 'r')
    for line in f:
        if line.startswith('Cached:'):
            f.close()
            return int(line.split()[1]) * 1024

def cached_swap():
    """Return the amount of cached swap on the system, in bytes."""
    f = open('/proc/meminfo', 'r')
    for line in f:
        if line.startswith('SwapCached:'):
            f.close()
            return int(line.split()[1]) * 1024

def get_system_cpu_times():
    """Return a dict representing the following CPU times:
    user, nice, system, idle, iowait, irq, softirq.
    """
    f = open('/proc/stat', 'r')
    values = f.readline().split()
    f.close()

    values = values[1:8]
    values = tuple([float(x) / _CLOCK_TICKS for x in values])

    return dict(user=values[0], nice=values[1], system=values[2], idle=values[3],
                iowait=values[4], irq=values[5], softirq=values[6])


# --- decorators

def wrap_exceptions(callable):
    """Call callable into a try/except clause and translate ENOENT,
    EACCES and EPERM in NoSuchProcess or AccessDenied exceptions.
    """
    def wrapper(self, pid, *args, **kwargs):
        try:
            return callable(self, pid, *args, **kwargs)
        except (OSError, IOError), err:
            if err.errno == errno.ENOENT:  # no such file or directory
                raise NoSuchProcess(pid, "process no longer exists")
            if err.errno in (errno.EPERM, errno.EACCES):
                raise AccessDenied(pid)
            raise
    return wrapper


class Impl(object):

    @wrap_exceptions
    def get_process_info(self, pid):
        """Returns a process info class."""
        if pid == 0:
            # special case for 0 (kernel process) PID
            return (pid, 0, 'sched', '', [], 0, 0)

        # determine executable
        try:
            _exe = os.readlink("/proc/%s/exe" %pid)
        except OSError:
            f = open("/proc/%s/stat" %pid)
            try:
                _exe = f.read().split(' ')[1].replace('(', '').replace(')', '')
            finally:
                f.close()

        # determine name and path
        if os.path.isabs(_exe):
            path, name = os.path.split(_exe)
        else:
            path = ''
            name = _exe

        # determine cmdline
        f = open("/proc/%s/cmdline" %pid)
        try:
            # return the args as a list
            cmdline = [x for x in f.read().split('\x00') if x]
        finally:
            f.close()

        return (pid, self._get_ppid(pid), name, path, cmdline,
                                  self._get_process_uid(pid),
                                  self._get_process_gid(pid))

    def get_pid_list(self):
        """Returns a list of PIDs currently running on the system."""
        pids = [int(x) for x in os.listdir('/proc') if x.isdigit()]
        # special case for 0 (kernel process) PID
        pids.insert(0, 0)
        return pids

    def pid_exists(self, pid):
        """Check For the existence of a unix pid."""
        return _psposix.pid_exists(pid)

    @wrap_exceptions
    def get_cpu_times(self, pid):
        # special case for 0 (kernel process) PID
        if pid == 0:
            return (0.0, 0.0)
        f = open("/proc/%s/stat" %pid)
        st = f.read().strip()
        f.close()
        # ignore the first two values ("pid (exe)")
        st = st[st.find(')') + 2:]
        values = st.split(' ')
        utime = float(values[11]) / _CLOCK_TICKS
        stime = float(values[12]) / _CLOCK_TICKS
        cputimes = namedtuple('cpuinfo', 'user system')
        return cputimes(utime, stime)

    @wrap_exceptions
    def get_process_create_time(self, pid):
        # special case for 0 (kernel processes) PID; return system uptime
        if pid == 0:
            return _UPTIME
        f = open("/proc/%s/stat" %pid)
        st = f.read().strip()
        f.close()
        # ignore the first two values ("pid (exe)")
        st = st[st.find(')') + 2:]
        values = st.split(' ')
        # According to documentation, starttime is in field 21 and the
        # unit is jiffies (clock ticks).
        # We first divide it for clock ticks and then add uptime returning
        # seconds since the epoch, in UTC.
        starttime = (float(values[19]) / _CLOCK_TICKS) + _UPTIME
        return starttime

    @wrap_exceptions
    def get_memory_info(self, pid):
        # special case for 0 (kernel processes) PID
        if pid == 0:
            return (0, 0)
        f = open("/proc/%s/status" % pid)
        virtual_size = 0
        resident_size = 0
        _flag = False
        for line in f:
            if (not _flag) and line.startswith("VmSize:"):
                virtual_size = int(line.split()[1])
                _flag = True
            elif line.startswith("VmRSS"):
                resident_size = int(line.split()[1])
                break
        f.close()
        meminfo = namedtuple('meminfo', 'rss vms')
        return meminfo(resident_size * 1024, virtual_size * 1024)

    @wrap_exceptions
    def get_process_cwd(self, pid):
        if pid == 0:
            return ''
        return os.readlink("/proc/%s/cwd" %pid)

    @wrap_exceptions
    def get_open_files(self, pid):
        retlist = []
        files = os.listdir("/proc/%s/fd" %pid)
        for link in files:
            file = "/proc/%s/fd/%s" %(pid, link)
            if os.path.islink(file):
                file = os.readlink(file)
                if file.startswith("socket:["):
                    continue
                if file.startswith("pipe:["):
                    continue
                if file == "[]":
                    continue
                if os.path.isfile(file) and not file in retlist:
                    retlist.append(file)
        return retlist

    @wrap_exceptions
    def get_connections(self, pid):
        if pid == 0:
            return []
        descriptors = []
        # os.listdir() is gonna raise a lot of access denied 
        # exceptions in case of unprivileged user; that's fine: 
        # lsof does the same so it's unlikely that we can to better.
        for name in os.listdir("/proc/%s/fd" %pid):
            try:
                fd = os.readlink("/proc/%s/fd/%s" %(pid, name))
            except OSError:
                continue
            if fd.startswith('socket:['):
                # the process is using a TCP connection
                descriptors.append(fd[8:][:-1])  # extract the fd number

        if not descriptors:
            # no connections for this process
            return []

        def process(file, family, _type):
            retlist = []
            f = open(file)
            f.readline()  # skip the first line
            for line in f:
                _, laddr, raddr, status, _, _, _, _, _, inode = line.split()[:10]
                if inode in descriptors:
                    laddr = self._decode_address(laddr, family)
                    raddr = self._decode_address(raddr, family)
                    # XXX - note: we're using TCP table also for UDP; 
                    # there should be one specific for UDP somewhere.
                    # Unfortunately I couldn't find it.
                    status = _TCP_STATES_TABLE[status]
                    conn = conntuple(family, _type, laddr, raddr, status)
                    retlist.append(conn)
            return retlist

        conntuple = namedtuple('connection', 'family type local_address ' \
                                             'remote_address status')
        tcp4 = process("/proc/net/tcp", socket.AF_INET, socket.SOCK_STREAM)
        tcp6 = process("/proc/net/tcp6", socket.AF_INET6, socket.SOCK_STREAM)
        udp4 = process("/proc/net/udp", socket.AF_INET, socket.SOCK_DGRAM)
        udp6 = process("/proc/net/udp6", socket.AF_INET6, socket.SOCK_DGRAM)
        return tcp4 + tcp6 + udp4 + udp6

#    --- lsof implementation
#
#    def get_connections(self, pid):
#        return _psposix.get_process_connections(pid)

    def _get_ppid(self, pid):
        f = open("/proc/%s/status" % pid)
        for line in f:
            if line.startswith("PPid:"):
                # PPid: nnnn
                f.close()
                return int(line.split()[1])

    def _get_process_uid(self, pid):
        f = open("/proc/%s/status" %pid)
        for line in f:
            if line.startswith('Uid:'):
                # Uid line provides 4 values which stand for real,
                # effective, saved set, and file system UIDs.
                # We want to provide real UID only.
                f.close()
                return int(line.split()[1])

    def _get_process_gid(self, pid):
        f = open("/proc/%s/status" %pid)
        for line in f:
            if line.startswith('Gid:'):
                # Uid line provides 4 values which stand for real,
                # effective, saved set, and file system GIDs.
                # We want to provide real GID only.
                f.close()
                return int(line.split()[1])

    def _decode_address(self, addr, family):
        """Accept an "ip:port" address as displayed in /proc/net/*
        and convert it into a human readable form, like:

        "0500000A:0016" -> ("10.0.0.5", 22)
        "0000000000000000FFFF00000100007F:9E49" -> ("::ffff:127.0.0.1", 40521)

        The IPv4 address portion is a little-endian four-byte hexadecimal
        number; that is, the least significant byte is listed first,
        so we need to reverse the order of the bytes to convert it
        to an IP address.
        The port is represented as a two-byte hexadecimal number.

        Reference: 
        http://linuxdevcenter.com/pub/a/linux/2000/11/16/LinuxAdmin.html
        """
        ip, port = addr.split(':')
        port = int(port, 16)
        if sys.version_info >= (3,):
            ip = ip.encode('ascii')
        # this usually refers to a local socket in listen mode with 
        # no end-points connected       
        if not port:
            return ()
        if family == socket.AF_INET:
            ip = socket.inet_ntop(family, base64.b16decode(ip)[::-1])
        else:  # IPv6
            # old version - let's keep it, just in case...
            #ip = ip.decode('hex')
            #return socket.inet_ntop(socket.AF_INET6, 
            #          ''.join(ip[i:i+4][::-1] for i in xrange(0, 16, 4)))
            ip = base64.b16decode(ip)
            ip = socket.inet_ntop(socket.AF_INET6, 
                                struct.pack('>4I', *struct.unpack('<4I', ip)))
        return (ip, port)


