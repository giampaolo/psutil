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
    def __init__(self, pid, name=None, path=None):
        self.pid = pid
        self.name = name
        self.path = path


class Process(object):
    """Represents an OS process"""
    def __init__(self, pid):
        self._procinfo = ProcessInfo(pid)
        self.is_proxy = True
        
    def deproxy(self):
        if self.is_proxy:
            self._procinfo = _platform_impl.get_process_info(self._procinfo.pid)
            self.is_proxy = False
    
    def get_pid(self):
        return self._procinfo.pid
    
    def get_name(self):
        self.deproxy()
        return self._procinfo.name
    
    def get_path(self):
        self.deproxy()
        return self._procinfo.path
    
    def __str__(self):
        return "psutil.Process [PID: %s; NAME: ''; PATH: '']" % self.pid  
    
    pid = property(get_pid)
    name = property(get_name)
    path = property(get_path)
    


def get_process_list():
    """returns a list of all running processes on the 
    local machine"""
    pidList = _platform_impl.get_pid_list();
    
    #for each PID, create a proxyied Process object
    #it will lazy init it's name and path later if required
    retProcesses = []
    for pid in pidList:
        retProcesses.append(Process(pid))
        
    return retProcesses


if __name__ == "__main__":
    processes = get_process_list()
    
    for proc in processes:
        print proc
