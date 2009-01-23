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
        infoTuple = infoTuple[0:-1] + (self.get_cmdline(pid),)
        return psutil.ProcessInfo(*infoTuple) 
        
    def kill_process(self, pid, sig=None):
        """Terminates the process with the given PID"""
        return _psutil_mswindows.kill_process(pid)
        
    def get_pid_list(self):
        """Returns a list of PIDs currently running on the system"""
        return _psutil_mswindows.get_pid_list()

    def get_cmdline(self, pid):
        """Return the cmdline for a process with a given PID"""
        import csv
        from subprocess import Popen,PIPE

        wmic_cmd = "WMIC PROCESS WHERE ProcessId=\'%s\' GET CommandLine /FORMAT:csv" % (pid)
        p = Popen([wmic_cmd], shell=True, stdout=PIPE, stdin=PIPE)
        #TODO: fix this ugly parsing mess
        wmic_output = p.communicate()[0].strip()
        wmic_output = wmic_output.splitlines()[-1]
        wmic_output = wmic_output.split(',')[1]
        arg_list = []
        if wmic_output:
            arg_list = csv.reader([wmic_output], delimiter=" ").next()
        return arg_list


