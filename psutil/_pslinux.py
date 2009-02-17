#!/usr/bin/env python
# _pslinux.py

import os
import signal
import socket


# ...from include/net/tcp_states.h
# http://students.mimuw.edu.pl/lxr/source/include/net/tcp_states.h
socket_status_table = {"01" : "ESTABLISHED",
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

class Impl(object):

    def process_exists(self, pid):
        """Checks whether or not a process exists with the given PID."""
        return pid in self.get_pid_list()

    def get_process_info(self, pid):
        """Returns a process info class."""
        # XXX - figure out why it can't be imported globally (see r54)
        import psutil

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
            path = '<unknown>'
            name = _exe

        # determine cmdline
        f = open("/proc/%s/cmdline" %pid)
        try:
            # return the args as a list
            cmdline = [x for x in f.read().split('\x00') if x]
        finally:
            f.close()

        return psutil.ProcessInfo(pid, self.get_ppid(pid), name, path, cmdline,
                                  self.get_process_uid(pid),
                                  self.get_process_gid(pid))

    def kill_process(self, pid, sig=signal.SIGKILL):
        """Terminates the process with the given PID."""
        if sig is None:
            sig = signal.SIGKILL
        os.kill(pid, sig)

    def get_pid_list(self):
        """Returns a list of PIDs currently running on the system."""
        return [int(x) for x in os.listdir('/proc') if x.isdigit()]

    def get_ppid(self, pid):
        f = open("/proc/%s/status" % pid)
        for line in f:
            if line.startswith("PPid:"):
                # PPid: nnnn
                return int(line.replace("PPid: "))

    def get_process_uid(self, pid):
        # XXX - something faster than readlines() could be used
        f = open("/proc/%s/status" %pid)
        for line in f.readlines():
            if line.startswith('Uid:'):
                # Uid line provides 4 values which stand for real,
                # effective, saved set, and file system UIDs.
                # We want to provide real UID only.
                return int(line.split()[1])

    def get_process_gid(self, pid):
        # XXX - something faster than readlines() could be used
        f = open("/proc/%s/status" %pid)
        for line in f.readlines():
            if line.startswith('Gid:'):
                # Uid line provides 4 values which stand for real,
                # effective, saved set, and file system GIDs.
                # We want to provide real GID only.
                return int(line.split()[1])

    def get_tcp_connections(self, pid):
        returning_list = []
        descriptors = []
        for name in os.listdir("/proc/%s/fd" %pid):
            try:
                fd = os.readlink("/proc/%s/fd/%s" %(pid, name))
            except OSError:
                continue
            if fd.startswith('socket:['):
                # the process is using a TCP connection
                descriptors.append(fd[8:][:-1])  # extract the fd number

        if not descriptors:
            # no TCP connections for this process
            return []

        f = open("/proc/net/tcp")
        f.readline()  # skip the first line
        for line in f:
            sl, local_address, rem_address, status, txrx_queue, trtm, retrnsmt,\
            uid, timeout, inode = line.split()[:10]
            if inode in descriptors:
                returning_list.append([_convert_address(local_address),
                                       _convert_address(rem_address),
                                       socket_status_table[status]
                                       ])
        return returning_list

    def get_udp_connections(self, pid):
        returning_list = []
        descriptors = []
        for name in os.listdir("/proc/%s/fd" %pid):
            try:
                fd = os.readlink("/proc/%s/fd/%s" %(pid, name))
            except OSError:
                continue
            if fd.startswith('socket:['):
                # the process is using a TCP connection
                descriptors.append(fd[8:][:-1])  # extract the fd number

        if not descriptors:
            # no UDP connections for this process
            return []

        f = open("/proc/net/udp")
        f.readline()  # skip the first line
        for line in f:
            sl, local_address, rem_address, status, txrx_queue, trtm, retrnsmt,\
            uid, timeout, inode = line.split()[:10]
            if inode in descriptors:
                returning_list.append([_convert_address(local_address),
                                       _convert_address(rem_address),
                                       ])
        return returning_list


def _convert_address(addr):
    """Accept an "ip:port" address as displayed in /proc/net/*
    and convert it into a human readable form.

    Example: "0500000A:0016" -> "10.0.0.5:22"

    The IP address portion is a little-endian four-byte hexadecimal
    number; that is, the least significant byte is listed first,
    so we need to reverse the order of the bytes to convert it
    to an IP address.
    The port number is a simple two-byte hexadecimal number.
    """
    ip, port = addr.split(':')
    ip = socket.inet_ntoa(ip.decode('hex')[::-1])
    port = int(port, 16)
    return "%s:%d" %(ip, port)


##print Impl().get_udp_connections(4302)
