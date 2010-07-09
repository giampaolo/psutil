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

try:
    from collections import namedtuple
except ImportError:
    from compat import namedtuple  # python < 2.6

from psutil import AccessDenied, NoSuchProcess


def _which(program):
    """Same as UNIX which command.  Return None on command not found."""
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
        else:
            raise ValueError("invalid IP %s" %addr)
    return (ip, int(port))


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

def get_process_open_files(pid):
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
    cmd = "lsof -a -p %s -n -P -w -F0tn" %pid
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if stderr:
        if _which("lsof") is None:
            msg = "this functionnality requires lsof command line utility " \
                   "to be installed on the system"
            raise NotImplementedError(msg)
        if "permission denied" in stderr.lower():
            # "permission denied" can be found also in case of zombie
            # processes;
            p = psutil.Process(pid)
            if not p.is_running():
                raise NoSuchProcess(pid, "process no longer exists")
            raise AccessDenied(pid)
        raise RuntimeError(stderr)  # this must be considered an application bug
    if not stdout:
        p = psutil.Process(pid)
        if not p.is_running():
            raise NoSuchProcess(pid, "process no longer exists")
        return []
    files = []
    lines = stdout.split()
    del lines[0]  # first line contains the PID
    for line in lines:
        if line.startswith("tVREG\x00n"):
            file = line[7:].strip("\x00")
            files.append(file)
    return files


def get_process_connections(pid):
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
    cmd = "lsof -p %s -i -a -w -F0nPtT -n -P" % pid
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if stderr:
        if _which("lsof") is None:
            msg = "this functionnality requires lsof command line utility " \
                   "to be installed on the system"
            raise NotImplementedError(msg)
        if "permission denied" in stderr.lower():
            # "permission denied" can be found also in case of zombie
            # processes;
            p = psutil.Process(pid)
            if not p.is_running():
                raise NoSuchProcess(pid, "process no longer exists")
            raise AccessDenied(pid)
        raise RuntimeError(stderr)  # this must be considered an application bug
    if not stdout:
        p = psutil.Process(pid)
        if not p.is_running():
            raise NoSuchProcess(pid, "process no longer exists")
        return []

    socket_table = {'TCP':socket.SOCK_STREAM, 'UDP':socket.SOCK_DGRAM,
                    'IPv4':socket.AF_INET, 'IPv6':socket.AF_INET6}
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
        _type = socket_table[fields['P']]  
        family = socket_table[fields['t']]
        peers = fields['n']
        status = fields.get('TST', "")  # might not appear for UDP
        if not '->' in peers:
            local_address = _normaddress(peers, family)
            remote_address = ()
        else:
            local_address, remote_address = peers.split("->")
            local_address = _normaddress(local_address, family)
            remote_address = _normaddress(remote_address, family)

        conn = namedtuple('connection', 'family type local_address ' \
                                        'remote_address status')
        conn = conn(family, _type, local_address, remote_address, status)
        connections.append(conn)

    return connections
    

