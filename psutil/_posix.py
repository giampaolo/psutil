#/usr/bin/env python
# _posix.py

"""Common operations for posix processes.
Do not import this module directly, use psutil instead.
"""

__all__ = ['list_processes', 'kill_process', 'kill_process_by_name',
           'get_process_path', 'get_process_name']


def list_processes():
    """Returns a list of PIDs for currently running processes."""
    raise NotImplemented

def kill_process(pid):
    """Kill process given its PID."""
    raise NotImplemented 
 
def kill_process_by_name(name, all=False):
    """Kill process given its name.
    EnvironmentError exception raised on unknown process name.
    
    - (str) name - the process name
    - (bool) all - whether kill all processess under that name; 
      if false the process with the lower pid will be killed. 
    """
    raise NotImplemented
            
def get_process_path(pid):
    """Return the process executable path."""
    raise NotImplemented

def get_process_name(pid):
    """Return the process name given its PID."""
    raise NotImplemented
