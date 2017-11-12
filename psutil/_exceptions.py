# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


class Error(Exception):
    """Base exception class. All other psutil exceptions inherit
    from this one.
    """

    def __init__(self, msg=""):
        Exception.__init__(self, msg)
        self.msg = msg

    def __repr__(self):
        ret = "psutil.%s %s" % (self.__class__.__name__, self.msg)
        return ret.strip()

    __str__ = __repr__


class NoSuchProcess(Error):
    """Exception raised when a process with a certain PID doesn't
    or no longer exists.
    """

    def __init__(self, pid, name=None, msg=None):
        Error.__init__(self, msg)
        self.pid = pid
        self.name = name
        self.msg = msg
        if msg is None:
            if name:
                details = "(pid=%s, name=%s)" % (self.pid, repr(self.name))
            else:
                details = "(pid=%s)" % self.pid
            self.msg = "process no longer exists " + details


class ZombieProcess(NoSuchProcess):
    """Exception raised when querying a zombie process. This is
    raised on OSX, BSD and Solaris only, and not always: depending
    on the query the OS may be able to succeed anyway.
    On Linux all zombie processes are querable (hence this is never
    raised). Windows doesn't have zombie processes.
    """

    def __init__(self, pid, name=None, ppid=None, msg=None):
        NoSuchProcess.__init__(self, msg)
        self.pid = pid
        self.ppid = ppid
        self.name = name
        self.msg = msg
        if msg is None:
            args = ["pid=%s" % pid]
            if name:
                args.append("name=%s" % repr(self.name))
            if ppid:
                args.append("ppid=%s" % self.ppid)
            details = "(%s)" % ", ".join(args)
            self.msg = "process still exists but it's a zombie " + details


class AccessDenied(Error):
    """Exception raised when permission to perform an action is denied."""

    def __init__(self, pid=None, name=None, msg=None):
        Error.__init__(self, msg)
        self.pid = pid
        self.name = name
        self.msg = msg
        if msg is None:
            if (pid is not None) and (name is not None):
                self.msg = "(pid=%s, name=%s)" % (pid, repr(name))
            elif (pid is not None):
                self.msg = "(pid=%s)" % self.pid
            else:
                self.msg = ""


class TimeoutExpired(Error):
    """Raised on Process.wait(timeout) if timeout expires and process
    is still alive.
    """

    def __init__(self, seconds, pid=None, name=None):
        Error.__init__(self, "timeout after %s seconds" % seconds)
        self.seconds = seconds
        self.pid = pid
        self.name = name
        if (pid is not None) and (name is not None):
            self.msg += " (pid=%s, name=%s)" % (pid, repr(name))
        elif (pid is not None):
            self.msg += " (pid=%s)" % self.pid
