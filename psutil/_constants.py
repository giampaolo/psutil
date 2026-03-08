# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Constants for psutil APIs."""

import enum

from ._common import FREEBSD
from ._common import LINUX
from ._common import SUNOS
from ._common import WINDOWS

if WINDOWS:
    from . import _psutil_windows as cext
elif LINUX:
    from . import _psutil_linux as cext
elif FREEBSD:
    from . import _psutil_bsd as cext
else:
    cext = None

if hasattr(enum, "StrEnum"):  # Python >= 3.11
    StrEnum = enum.StrEnum
else:

    # A backport of Python 3.11 StrEnum class for >= Python 3.8
    class StrEnum(str, enum.Enum):
        def __new__(cls, *values):
            value = str(*values)
            member = str.__new__(cls, value)
            member._value_ = value
            return member

        __str__ = str.__str__

        @staticmethod
        def _generate_next_value_(name, _start, _count, _last_values):
            return name.lower()


# psutil.Process.status()
class ProcStatus(StrEnum):
    STATUS_RUNNING = "running"
    STATUS_SLEEPING = "sleeping"
    STATUS_DISK_SLEEP = "disk-sleep"
    STATUS_STOPPED = "stopped"
    STATUS_TRACING_STOP = "tracing-stop"
    STATUS_ZOMBIE = "zombie"
    STATUS_DEAD = "dead"
    STATUS_WAKE_KILL = "wake-kill"
    STATUS_WAKING = "waking"
    STATUS_IDLE = "idle"  # Linux, macOS, FreeBSD
    STATUS_LOCKED = "locked"  # FreeBSD
    STATUS_WAITING = "waiting"  # FreeBSD
    STATUS_SUSPENDED = "suspended"  # NetBSD
    STATUS_PARKED = "parked"  # Linux


# psutil.Process.net_connections() and psutil.net_connections()
class ConnStatus(StrEnum):
    CONN_ESTABLISHED = "ESTABLISHED"
    CONN_SYN_SENT = "SYN_SENT"
    CONN_SYN_RECV = "SYN_RECV"
    CONN_FIN_WAIT1 = "FIN_WAIT1"
    CONN_FIN_WAIT2 = "FIN_WAIT2"
    CONN_TIME_WAIT = "TIME_WAIT"
    CONN_CLOSE = "CLOSE"
    CONN_CLOSE_WAIT = "CLOSE_WAIT"
    CONN_LAST_ACK = "LAST_ACK"
    CONN_LISTEN = "LISTEN"
    CONN_CLOSING = "CLOSING"
    CONN_NONE = "NONE"
    if WINDOWS:
        CONN_DELETE_TCB = "DELETE_TCB"
    if SUNOS:
        CONN_IDLE = "IDLE"
        CONN_BOUND = "BOUND"


# psutil.net_if_stats()
class NicDuplex(enum.IntEnum):
    NIC_DUPLEX_FULL = 2
    NIC_DUPLEX_HALF = 1
    NIC_DUPLEX_UNKNOWN = 0


# psutil.sensors_battery()
class BatteryTime(enum.IntEnum):
    POWER_TIME_UNKNOWN = -1
    POWER_TIME_UNLIMITED = -2


if LINUX:

    # psutil.Process.ionice(ioclass=…)
    class ProcIOPriorityClass(enum.IntEnum):
        # ioprio_* constants http://linux.die.net/man/2/ioprio_get
        IOPRIO_CLASS_NONE = 0
        IOPRIO_CLASS_RT = 1
        IOPRIO_CLASS_BE = 2
        IOPRIO_CLASS_IDLE = 3


if WINDOWS:
    from . import _psutil_windows as cext

    # psutil.Process.ionice(ioclass=…)
    class ProcIOPriorityClass(enum.IntEnum):
        IOPRIO_VERYLOW = 0
        IOPRIO_LOW = 1
        IOPRIO_NORMAL = 2
        IOPRIO_HIGH = 3

    # psutil.Process.nice()
    class ProcPriority(enum.IntEnum):
        ABOVE_NORMAL_PRIORITY_CLASS = cext.ABOVE_NORMAL_PRIORITY_CLASS
        BELOW_NORMAL_PRIORITY_CLASS = cext.BELOW_NORMAL_PRIORITY_CLASS
        HIGH_PRIORITY_CLASS = cext.HIGH_PRIORITY_CLASS
        IDLE_PRIORITY_CLASS = cext.IDLE_PRIORITY_CLASS
        NORMAL_PRIORITY_CLASS = cext.NORMAL_PRIORITY_CLASS
        REALTIME_PRIORITY_CLASS = cext.REALTIME_PRIORITY_CLASS


if LINUX or FREEBSD:

    # psutil.Process.rlimit()
    ProcRlimit = enum.IntEnum(
        "ProcRlimit",
        (
            (name, getattr(cext, name))
            for name in dir(cext)
            if name.startswith("RLIM") and name.isupper()
        ),
    )
