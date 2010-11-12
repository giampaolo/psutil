#!/usr/bin/env python
#
# $Id$
#

"""Routines common to all posix systems."""

import os
import errno
import subprocess
import psutil
import socket
import re
import sys
import warnings

try:
    from collections import namedtuple
except ImportError:
    from psutil.compat import namedtuple  # python < 2.6

from psutil.error import AccessDenied, NoSuchProcess


def pid_exists(pid):
    """Check whether pid exists in the current process table."""
    if pid < 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError, e:
        return e.errno == errno.EPERM
    else:
        return True


class LsofParser:
    """A wrapper for lsof command line utility.
    Executes lsof in subprocess and parses its output.
    """
    socket_table = {'TCP' : socket.SOCK_STREAM,
                    'UDP' : socket.SOCK_DGRAM,
                    'IPv4' : socket.AF_INET,
                    'IPv6' : socket.AF_INET6}
    _openfile_ntuple = namedtuple('openfile', 'path fd')
    _connection_ntuple = namedtuple('connection', 'fd family type local_address '
                                                  'remote_address status')

    def __init__(self, pid, name):
        self.pid = pid
        self.process_name = name

    def get_process_open_files(self):
        """Return files opened by process by parsing lsof output."""
        # Options:
        # -i == network files only
        # -a == ANDing of all options
        # -p == process with given PID only
        # -n == do not resolve IP addresses
        # -P == do not resolve port numbers
        # -w == suppresses warnings
        # -F0nPt == (0) separate lines with "\x00"
        #           (n) file name
        #           (t) file type
        #           (f) file descriptr
        cmd = "lsof -a -p %s -n -P -F0ftn" % self.pid
        stdout = self.runcmd(cmd)
        if not stdout:
            return []
        files = []
        lines = stdout.split("\n")
        del lines[0]  # first line contains the PID
        for line in lines:
            if not line:
                continue
            line = line.strip("\x00")
            fields = {}
            for field in line.split("\x00"):
                key, value = field[0], field[1:]
                fields[key] = value
            if not 't' in fields:
                continue
            _type = fields['t']
            fd = fields['f']
            name = fields['n']
            if 'REG' in _type and fd.isdigit():
                if not os.path.isfile(os.path.realpath(name)):
                    continue
                ntuple = self._openfile_ntuple(name, int(fd))
                files.append(ntuple)
        return files

    def get_process_connections(self):
        """Return connections opened by a process by parsing lsof output."""
        # Options:
        # -i == network files only
        # -a == ANDing of all options
        # -p == process with given PID only
        # -n == do not resolve IP addresses
        # -P == do not resolve port numbers
        # -w == suppresses warnings
        # -F0nPt == (0) separate lines with "\x00"
        #           (n) and show internet addresses only
        #           (P) protocol type (TCP, UPD, Unix)
        #           (t) socket family (IPv4, IPv6)
        #           (T) connection status
        #           (f) file descriptors
        cmd = "lsof -p %s -i -a -F0nPtTf -n -P" % self.pid
        stdout = self.runcmd(cmd)
        if not stdout:
            return []
        connections = []
        lines = stdout.split()
        del lines[0]  # first line contains the PID
        for line in lines:
            line = line.strip("\x00")
            fields = {}
            for field in line.split("\x00"):
                if field.startswith('T'):
                    key, value = field.split('=')
                else:
                    key, value = field[0], field[1:]
                fields[key] = value

            # XXX - might trow execption; needs "continue on unsupported
            # family or type" (e.g. unix sockets)
            # we consider TCP and UDP sockets only
            stype = fields['P']
            if stype not in self.socket_table:
                continue
            else:
                _type = self.socket_table[fields['P']]
            family = self.socket_table[fields['t']]
            peers = fields['n']
            fd = int(fields['f'])
            if _type == socket.SOCK_STREAM:
                status = fields['TST']
                # OS X shows "CLOSED" instead of "CLOSE" so translate them
                if status == "CLOSED":
                    status = "CLOSE"
            else:
                status = ""
            if not '->' in peers:
                local_addr = self._normaddress(peers, family)
                remote_addr = ()
                # OS X processes e.g. SystemUIServer can return *:* for local
                # address, so we return 0 and move on
                if local_addr == 0:
                    continue
            else:
                local_addr, remote_addr = peers.split("->")
                local_addr = self._normaddress(local_addr, family)
                remote_addr = self._normaddress(remote_addr, family)

            conn = self._connection_ntuple(fd, family, _type, local_addr,
                                           remote_addr, status)
            connections.append(conn)

        return connections

    def runcmd(self, cmd):
        """Expects an lsof-related command line, execute it in a
        subprocess and return its output.
        If something goes bad stderr is parsed and proper exceptions
        raised as necessary.
        """
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if sys.version_info >= (3,):
            stdout, stderr = map(lambda x: x.decode(sys.stdout.encoding),
                                 (stdout, stderr))
        if stderr:
            utility = cmd.split(' ')[0]
            if self._which(utility) is None:
                msg = "this functionnality requires %s command line utility " \
                      "to be installed on the system" % utility
                raise NotImplementedError(msg)
            elif "permission denied" in stderr.lower():
                # "permission denied" can be found also in case of zombie
                # processes;
                p = psutil.Process(self.pid)
                if not p.is_running():
                    raise NoSuchProcess(self.pid, self.process_name)
                raise AccessDenied(self.pid, self.process_name)
            elif "lsof: warning:" in stderr.lower():
                # usually appears when lsof is run for the first time and
                # complains about missing cache file in user home
                warnings.warn(stderr, RuntimeWarning)
            else:
                # this must be considered an application bug
                raise RuntimeError(stderr)
        if not stdout:
            p = psutil.Process(self.pid)
            if not p.is_running():
                raise NoSuchProcess(self.pid, self.process_name)
            return ""
        return stdout

    @staticmethod
    def _which(program):
        """Same as UNIX which command. Return None on command not found."""
        def is_exe(fpath):
            return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

        fpath, fname = os.path.split(program)
        if fpath:
            if is_exe(program):
                return program
        else:
            for path in os.environ["PATH"].split(os.pathsep):
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return exe_file
        return None

    @staticmethod
    def _normaddress(addr, family):
        """Normalize an IP address."""
        assert family in (socket.AF_INET, socket.AF_INET6), "unsupported family"
        if family == socket.AF_INET:
            ip, port = addr.split(':')
        else:
            if "]" in addr:
                ip, port = re.findall('\[([^]]+)\]:([0-9]+)', addr)[0]
            else:
                ip, port = addr.split(':')
        if ip == '*':
            if family == socket.AF_INET:
                ip = "0.0.0.0"
            elif family == socket.AF_INET6:
                ip = "::"
            # OS X can have some procs e.g. SystemUIServer listening on *:*
            else:
                raise ValueError("invalid IP %s" %addr)
            if port == "*":
                return 0
        return (ip, int(port))


