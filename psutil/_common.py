#/usr/bin/env python
#
#$Id$
#

"""Common objects shared by all _ps* modules."""

from psutil._compat import namedtuple

def usage_percent(used, total, _round=None):
    """Calculate percentage usage of 'used' against 'total'."""
    try:
        ret = (float(used) / total) * 100
    except ZeroDivisionError:
        ret = 0
    if _round is not None:
        return round(ret, _round)
    else:
        return ret


class constant(int):
    """A constant type; overrides base int to provide a useful name on str()."""

    def __new__(cls, value, name, doc=None):
        inst = super(constant, cls).__new__(cls, value)
        inst._name = name
        if doc is not None:
            inst.__doc__ = doc
        return inst

    def __str__(self):
        return self._name

STATUS_RUNNING = constant(0, "running")
STATUS_SLEEPING = constant(1, "sleeping")
STATUS_DISK_SLEEP = constant(2, "disk sleep")
STATUS_STOPPED = constant(3, "stopped")
STATUS_TRACING_STOP = constant(4, "tracing stop")
STATUS_ZOMBIE = constant(5, "zombie")
STATUS_DEAD = constant(6, "dead")
STATUS_WAKE_KILL = constant(7, "wake kill")
STATUS_WAKING = constant(8, "waking")
STATUS_IDLE = constant(9, "idle")  # BSD
STATUS_LOCKED = constant(10, "locked")  # BSD
STATUS_WAITING = constant(11, "waiting")  # BSD


# system
ntuple_sys_cputimes = namedtuple('cputimes', 'user nice system idle iowait irq softirq')
ntuple_sysmeminfo = namedtuple('usage', 'total used free percent')
ntuple_diskinfo = namedtuple('usage', 'total used free percent')
ntuple_partition = namedtuple('partition',  'device mountpoint fstype')

# processes
ntuple_meminfo = namedtuple('meminfo', 'rss vms')
ntuple_cputimes = namedtuple('cputimes', 'user system')
ntuple_openfile = namedtuple('openfile', 'path fd')
ntuple_connection = namedtuple('connection', 'fd family type local_address remote_address status')
ntuple_thread = namedtuple('thread', 'id user_time system_time')
ntuple_uids = namedtuple('user', 'real effective saved')
ntuple_gids = namedtuple('group', 'real effective saved')
ntuple_io = namedtuple('io', 'read_count write_count read_bytes write_bytes')
ntuple_ionice = namedtuple('ionice', 'ioclass value')
ntuple_netiostat = namedtuple('iostat', 'interface bytes_sent bytes_rcvd packets_sent packets_rcvd')
ntuple_tot_netiostat = namedtuple('iostat', 'bytes_sent bytes_rcvd packets_sent packets_rcvd')
