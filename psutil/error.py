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

    def __init__(self, pid=None, msg=None):
        self.pid = pid
        self.msg = msg

    def __str__(self):
        if self.msg:
            return self.msg
        elif self.pid:
            return "no such process with pid %d" % self.pid
        else:
            return ""

class AccessDenied(Error):
    """Exception raised when permission to perform an action is denied."""

    def __init__(self, pid=None, msg=None):
        self.pid = pid
        self.msg = msg

    def __str__(self):
        return self.msg or ""


