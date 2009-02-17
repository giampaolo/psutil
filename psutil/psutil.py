#!/usr/bin/env python
# psutil.py

"""psutil is a module providing convenience functions for managing
processes in a portable way by using Python.
"""

import sys
import os


# the linux implementation has the majority of it's functionality
# implemented in python via /proc
if sys.platform.lower().startswith("linux"):
    import _pslinux
    _platform_impl = _pslinux.Impl()

# the windows implementation requires the _psutil_mswindows C module
elif sys.platform.lower().startswith("win32"):
    import _psmswindows
    _platform_impl = _psmswindows.Impl()

# OS X implementation requires _psutil_osx C module
elif sys.platform.lower().startswith("darwin"):
    import _psosx
    _platform_impl = _psosx.Impl()
else:
    raise ImportError('no os specific module found')


class ProcessInfo(object):
    """Class that allows the process information to be passed
    between external code and psutil.  Used directly by the
    Process class.
    """

    def __init__(self, pid, ppid=None, name=None, path=None, cmdline=None, uid=None, gid=None):
        self.pid = pid
        self.ppid = ppid
        self.name = name
        self.path = path
        self.cmdline = cmdline
        # if we have the cmdline but not the path, figure it out from argv[0]
        if cmdline and (path == "<unknown>"):
            self.path = os.path.dirname(cmdline[0])
        self.uid = uid
        self.gid = gid


class Process(object):
    """Represents an OS process."""

    def __init__(self, pid):
        self._procinfo = ProcessInfo(pid)
        self.is_proxy = True

    def deproxy(self):
        if self.is_proxy:
            self._procinfo = _platform_impl.get_process_info(self._procinfo.pid)
            self.is_proxy = False

    @property
    def pid(self):
        "The process pid."
        return self._procinfo.pid
   
    @property
    def ppid(self):
        "The process parent pid."
        self.deproxy()
        return self._procinfo.ppid

    @property
    def parent(self):
        """Return the parent process as a Process object. If no ppid is known
        then return None."""
        self.deproxy()
        if self.ppid is not None:
            return Process(self.ppid) 
        return None

    @property
    def name(self):
        """The process name."""
        self.deproxy()
        return self._procinfo.name

    @property
    def path(self):
        """The process path."""
        self.deproxy()
        return self._procinfo.path

    @property
    def cmdline(self):
        """The command line process has been called with."""
        self.deproxy()
        return self._procinfo.cmdline

    @property
    def uid(self):
        """The real user id of the current process."""
        self.deproxy()
        return self._procinfo.uid

    @property
    def gid(self):
        """The real group id of the current process."""
        self.deproxy()
        return self._procinfo.gid

    def kill(self, sig=None):
        """Kill the current process by using signal sig (defaults to SIGKILL).
        """
        _platform_impl.kill_process(self.pid, sig)

    def __str__(self):
        return "psutil.Process <PID:%s; PPID:%s; NAME:'%s'; PATH:'%s'; CMDLINE:%s; UID:%s; GID:%s;>" \
            %(self.pid, self.ppid, self.name, self.path, self.cmdline, self.uid, self.gid)


def get_process_list():
    """Return a list of Process class instances for all running
    processes on the local machine.
    """
    pidList = _platform_impl.get_pid_list();
    # for each PID, create a proxyied Process object
    # it will lazy init it's name and path later if required
    retProcesses = []
    for pid in pidList:
        retProcesses.append(Process(pid))
    return retProcesses

def test():
    processes = get_process_list()
    print "%-5s  %-5s %-15s %-25s %-20s %-5s %-5s" %("PID", "PPID", "NAME", "PATH", "COMMAND LINE", "UID", "GID")
    for proc in processes:
        print "%-5s  %-5s %-15s %-25s %-20s %-5s %-5s" %(proc.pid, proc.ppid, proc.name, proc.path or \
                                        "<unknown>", ' '.join(proc.cmdline) or \
                                        "<unknown>", proc.uid, proc.gid,
                                        )

if __name__ == "__main__":
    test()

