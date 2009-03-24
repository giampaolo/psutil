# this exception get overriden by the platform specific modules if necessary
class NoSuchProcess(Exception):
    """No process was found for the given parameters."""

class AccessDenied(Exception):
    """Exception raised when permission to perform an action is denied."""

