#!/usr/bin/env python


class CPUTimes:
    """This class contains information about CPU times.
    This class is not used directly but it's returned as an instance by
    psutil.cpu_times() function.

    Every CPU time is accessible in form of an attribute and represents
    the time CPU has spent in the given mode.

    The attributes availability varies depending on the platform.
    Here follows a list of all available attributes:

     - user
     - system
     - idle
     - nice (UNIX)
     - iowait (Linux)
     - irq (Linux)
     - softirq (Linux)
     - interrupt (FreeBSD)
    """

    def __init__(self, **kwargs):
        self.attrs = []
        for name in kwargs:
            setattr(self, name, kwargs[name])
            self.attrs.append(name)

    def __str__(self):
        string = []
        for attr in self.attrs:
            value = getattr(self, attr)
            string.append("%s=%s" %(attr, value))
        return '; '.join(string)

    def __iter__(self):
        for attr in self.attrs:
            yield getattr(self, attr)

