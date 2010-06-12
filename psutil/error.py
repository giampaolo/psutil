# $Id

# this exception get overriden by the platform specific modules if necessary

class Error(Exception):
    pass

class NoSuchProcess(Error):
    """No process was found for the given parameters."""

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


