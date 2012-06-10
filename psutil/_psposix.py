#!/usr/bin/env python
#
# $Id$
#
# Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Routines common to all posix systems."""

import os
import errno
import subprocess
import psutil
import socket
import re
import sys
import warnings
import time
import glob

from psutil.error import AccessDenied, NoSuchProcess, TimeoutExpired
from psutil._compat import PY3, namedtuple
from psutil._common import nt_diskinfo, usage_percent


def pid_exists(pid):
    """Check whether pid exists in the current process table."""
    if not isinstance(pid, int):
        raise TypeError('an integer is required')
    if pid < 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        e = sys.exc_info()[1]
        return e.errno == errno.EPERM
    else:
        return True

def wait_pid(pid, timeout=None):
    """Wait for process with pid 'pid' to terminate and return its
    exit status code as an integer.

    If pid is not a children of os.getpid() (current process) just
    waits until the process disappears and return None.

    If pid does not exist at all return None immediately.

    Raise TimeoutExpired on timeout expired.
    """
    def check_timeout(delay):
        if timeout is not None:
            if time.time() >= stop_at:
                raise TimeoutExpired(pid)
        time.sleep(delay)
        return min(delay * 2, 0.04)

    if timeout is not None:
        waitcall = lambda: os.waitpid(pid, os.WNOHANG)
        stop_at = time.time() + timeout
    else:
        waitcall = lambda: os.waitpid(pid, 0)

    delay = 0.0001
    while 1:
        try:
            retpid, status = waitcall()
        except OSError:
            err = sys.exc_info()[1]
            if err.errno == errno.EINTR:
                delay = check_timeout(delay)
                continue
            elif err.errno == errno.ECHILD:
                # This has two meanings:
                # - pid is not a child of os.getpid() in which case
                #   we keep polling until it's gone
                # - pid never existed in the first place
                # In both cases we'll eventually return None as we
                # can't determine its exit status code.
                while 1:
                    if pid_exists(pid):
                        delay = check_timeout(delay)
                    else:
                        return
            else:
                raise
        else:
            if retpid == 0:
                # WNOHANG was used, pid is still running
                delay = check_timeout(delay)
                continue
            # process exited due to a signal; return the integer of
            # that signal
            if os.WIFSIGNALED(status):
                return os.WTERMSIG(status)
            # process exited using exit(2) system call; return the
            # integer exit(2) system call has been called with
            elif os.WIFEXITED(status):
                return os.WEXITSTATUS(status)
            else:
                # should never happen
                raise RuntimeError("unknown process exit status")

def get_disk_usage(path):
    """Return disk usage associated with path."""
    st = os.statvfs(path)
    free = (st.f_bavail * st.f_frsize)
    total = (st.f_blocks * st.f_frsize)
    used = (st.f_blocks - st.f_bfree) * st.f_frsize
    percent = usage_percent(used, total, _round=1)
    # NB: the percentage is -5% than what shown by df due to
    # reserved blocks that we are currently not considering:
    # http://goo.gl/sWGbH
    return nt_diskinfo(total, used, free, percent)

def _get_terminal_map():
    ret = {}
    ls = glob.glob('/dev/tty*') + glob.glob('/dev/pts/*')
    for name in ls:
        assert name not in ret
        ret[os.stat(name).st_rdev] = name
    return ret


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

    # XXX - this is no longer used
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
        if PY3:
            stdout, stderr = [x.decode(sys.stdout.encoding)
                              for x in (stdout, stderr)]
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
