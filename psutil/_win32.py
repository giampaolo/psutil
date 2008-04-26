#/usr/bin/env python
# _win32.py

"""Common operations for Microsoft Windows processes.
Do not import this module directly, use psutil instead.
"""

import win32process
import win32pdhutil
import win32api
import win32con
import os


__all__ = ['list_processes', 'kill_process', 'kill_process_by_name',
           'get_process_path', 'get_process_name']

  
def list_processes():
    """Returns a list of PIDs for currently running processes."""
    return list(win32process.EnumProcesses())

def kill_process(pid):
    """Kill process given its PID."""
    handle = win32api.OpenProcess(win32con.PROCESS_TERMINATE, 0, pid)
    win32api.TerminateProcess(handle, 0)
    win32api.CloseHandle(handle) 
 
def kill_process_by_name(name, all=False):
    """Kill process given its name.
    EnvironmentError exception raised on unknown process name.
    
    - (str) name - the process name
    - (bool) all - whether kill all processess under that name; 
      if false the process with the lower pid will be killed. 
    """
    if name.endswith('.exe'):
        name = name[:-4]
    pids = win32pdhutil.FindPerformanceAttributesByName(name)
    pids.sort()
    if not pids:
        raise EnvironmentError('No such process "%s".' %name)
    if not all:
        kill_process(pids[0])
    else:
        for pid in pids:
            kill_process(pid)
            
def get_process_path(pid):
    """Return the process executable path."""
    handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, pid)
    return win32process.GetModuleFileNameEx(handle, 0)

def get_process_name(pid):
    """Return the process name given its PID."""
    return os.path.basename(get_process_path(pid))
