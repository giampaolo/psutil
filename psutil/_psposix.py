#!/usr/bin/env python
#
# $Id$
#

"""Routines common to all posix systems."""

import os
import errno
import subprocess
import psutil

from psutil.error import *


def get_process_open_files(pid):
    """Return files opened by process by parsing lsof output."""
    cmd = "lsof -p %s -Ftn0" %pid
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if stderr:
        if "not found" in stderr:
            msg = "This functionnality requires lsof command line utility " \
                   "to be installed on the system"
            raise NotImplementedError(msg)
        if "permission denied" in stderr.lower():
            # "permission denied" can be found also in case of zombie
            # processes;
            p = psutil.Process(pid)
            if not p.is_running:
                raise NoSuchProcess(pid, "process no longer exists")
            raise AccessDenied(pid)
        raise RuntimeError(stderr)  # this must be considered an application bug
    if not stdout:
        p = psutil.Process(pid)
        if not p.is_running:
            raise NoSuchProcess(pid, "process no longer exists")
        return []
    files = []
    for line in stdout.split():
        if line.startswith("tVREG\x00n"):
            file = line[7:].strip("\x00")
            if os.path.isfile(file):
                files.append(file)
    return files


