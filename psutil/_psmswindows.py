#!/usr/bin/env python
# _psmswindows.py

import _psutil_mswindows


class Impl(object):

    def process_exists(self, pid):
        """Checks whether or not a process exists with the given PID."""
        return pid in self.get_pid_list()

    def get_process_info(self, pid):
        """Returns a tuple that can be passed to the psutil.ProcessInfo class
        constructor.
        """
        # XXX - figure out why it can't be imported globally (see r54)
        import psutil
        infoTuple = _psutil_mswindows.get_process_info(pid)
        return psutil.ProcessInfo(*infoTuple)

    def kill_process(self, pid, sig=None):
        """Terminates the process with the given PID."""
        return _psutil_mswindows.kill_process(pid)

    def get_pid_list(self):
        """Returns a list of PIDs currently running on the system."""
        return _psutil_mswindows.get_pid_list()

    def get_process_uid(self, pid):
        # UID doesn't make sense on Windows
        return -1

    def get_process_gid(self, pid):
        # GID doesn't make sense on Windows
        return -1

    def get_tcp_connections(self, pid):
        # XXX - provisonal: use netstat and parse its output
        from subprocess import Popen, PIPE

        pid = str(pid)
        p = Popen(['netstat -ano -p tcp'], shell=True, stdout=PIPE, stdin=PIPE)
        output = p.communicate()[0].strip()  # stdout w/whitespace trimmed
        p.wait()

        if pid not in output:
            return []

        returning_list = []
        for line in output.split('\r\n'):
            if line.startswith('  TCP'):
                proto, local_addr, rem_addr, status, _pid = line.split()
                if _pid == pid:
                    returning_list.append([local_addr, rem_addr, status])
        return returning_list

    def get_udp_connections(self, pid):
        # XXX - provisonal: use netstat and parse its output
        from subprocess import Popen, PIPE

        pid = str(pid)
        p = Popen(['netstat -ano -p udp'], shell=True, stdout=PIPE)
        output = p.communicate()[0].strip()  # stdout w/whitespace trimmed
        p.wait()

        if pid not in output:
            return []

        returning_list = []
        for line in output.split('\r\n'):
            if line.startswith('  UDP'):
                proto, local_addr, rem_addr, _pid = line.split()
                if _pid == pid:
                    returning_list.append([local_addr, rem_addr])
        return returning_list

