import _psutil_mswindows

class Impl:
    def process_exists(self, pid):
        """Checks whether or not a process exists with the given PID"""
        pass
        
    def get_process_info(self, pid):
        """Returns a process info class for the given PID"""
        pass
        
    def kill_process(self, pid):
        """Terminates the process with the given PID"""
        pass
        
    def get_pid_list(self):
        """Returns a list of PIDs currently running on the system"""
        for id in _psutil_mswindows.get_pid_list():
            print id
