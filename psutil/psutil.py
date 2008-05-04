#psutil is a module providing convenience functions for managing 
#processes in a portable way by using Python.

import sys

_platform_impl = None

#the linux implementation has the majority of it's functionality
#implemented in python via /proc
if sys.platform.lower().startswith("linux"):
    import _pslinux
    _platform_impl = _pslinux.Impl()

#the windows implementation requires the _psutil_mswindows c module
elif sys.platform.lower().startswith("win32"):
    import _psmswindows
    _platform_impl = _psmswindows.Impl()


class ProcessInfo(object):
    """Class that allows the process information to be passed
    between external code and psutil.  Used directly by the
    Process class"""
    def __init__(self, pid, name, path):
        self.pid = pid
        self.name = name
        self.path = path


def get_process_list():
    """returns a list of all running processes on the 
    local machine"""
    #get the pid list and then fill in the process info for
    #each process
    pidList = _platform_impl.get_pid_list();
    pass

get_process_list()