import _psutil_mswindows

class Impl(object):
    def process_exists(self, pid):
        """Checks whether or not a process exists with the given PID"""
        return pid in self.get_pid_list()
        
    def get_process_info(self, pid):
        """Returns a process info class for the given PID"""
        raise _psutil_mswindows.get_process_info(pid)
        
    def kill_process(self, pid):
        """Terminates the process with the given PID"""
        raise NotImplementedError
        
    def get_pid_list(self):
        """Returns a list of PIDs currently running on the system"""
        return _psutil_mswindows.get_pid_list()
