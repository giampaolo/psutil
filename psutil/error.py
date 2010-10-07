#!/usr/bin/env python
#
# $Id$
#

"""psutil exception classes"""


class Error(Exception):
    """Base exception class. All other psutil exceptions inherit
    from this one.
    """

class NoSuchProcess(Error):
    """Exception raised when a process with a certain PID doesn't
    or no longer exists (zombie).
    """

    def __init__(self, pid, name, msg=None):
        self.pid = pid
        self.name = name
        self.msg = msg

    def __str__(self):
        if self.msg:
            return self.msg
        else:
            if self.name:
                details = "(pid=%s, name=%s)" % (self.pid, repr(self.name))
            else:
                details = "(pid=%s)" % self.pid
            return "process no longer exists " + details

class AccessDenied(Error):
    """Exception raised when permission to perform an action is denied."""

    def __init__(self, pid=None, name=None, msg=None):
        self.pid = pid
        self.name = name
        self.msg = msg

    def __str__(self):
        if self.msg:
            return self.msg
        else:
            if self.pid and self.name:
                return "(pid=%s, name=%s)" % (self.pid, repr(self.name))
            elif self.pid:
                return "(pid=%s)" % self.pid
            else:
                return ""

