import _psutil_mswindows

class Impl(object):
    def process_exists(self, pid):
        """Checks whether or not a process exists with the given PID"""
        return pid in self.get_pid_list()
        
    def get_process_info(self, pid):
        import psutil
        """Returns a tuple that can be passed to the psutil.ProcessInfo class
        constructor"""

        infoTuple = _psutil_mswindows.get_process_info(pid)
        ret = psutil.ProcessInfo(infoTuple[0:1] + (self.get_cmdline(pid),))
        #psutil.ProcessInfo(*infoTuple) 
        return ret 
        
    def kill_process(self, pid, sig=None):
        """Terminates the process with the given PID"""
        return _psutil_mswindows.kill_process(pid)
        
    def get_pid_list(self):
        """Returns a list of PIDs currently running on the system"""
        return _psutil_mswindows.get_pid_list()

    def get_cmdline(self, pid):
        """Return the cmdline for a process with a given PID"""
        from subprocess import Popen,PIPE
        wmic_cmd = "WMIC PROCESS WHERE ProcessId=\'%s\' GET CommandLine /FORMAT:csv" % (pid)
        #print 'wmic_cmd:', wmic_cmd
        #wmic_output = "foo"
        p = Popen([wmic_cmd], shell=True, stdout=PIPE, stdin=PIPE)
        wmic_output = p.communicate()[0].strip()
        wmic_output = wmic_output.splitlines()[-1]
        wmic_output = wmic_output.split(',')[1]
        #print wmic_output
        return wmic_output
        
