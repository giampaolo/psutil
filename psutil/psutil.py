#psutil is a module providing convenience functions for managing 
#processes in a portable way by using Python.

import sys

_platform_impl = None

#the linux implementation has the majority of it's functionality
#implemented in python via /proc
if sys.platform.lower().startswith("linux"):
    import _pslinux
    _platform_impl = _pslinux.Impl()


def get_process_list():
    """returns a list of all running processes on the 
    local machine"""
    #get the pid list and then fill in the process info for
    #each process
    pidList = _platform_impl.get_pid_list();
    pass
