# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Constants for psutil APIs."""

import enum

from ._common import LINUX
from ._common import WINDOWS


# Process.status()
class ProcStatus(enum.StrEnum):
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


# net_if_stats()
class NicDuplex(enum.IntEnum):
    NIC_DUPLEX_FULL = 2
    NIC_DUPLEX_HALF = 1
    NIC_DUPLEX_UNKNOWN = 0


# sensors_battery()
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

elif WINDOWS:
    from . import _psutil_windows as cext

    # psutil.Process.nice()
    class ProcPriority(enum.IntEnum):
        ABOVE_NORMAL_PRIORITY_CLASS = cext.ABOVE_NORMAL_PRIORITY_CLASS
        BELOW_NORMAL_PRIORITY_CLASS = cext.BELOW_NORMAL_PRIORITY_CLASS
        HIGH_PRIORITY_CLASS = cext.HIGH_PRIORITY_CLASS
        IDLE_PRIORITY_CLASS = cext.IDLE_PRIORITY_CLASS
        NORMAL_PRIORITY_CLASS = cext.NORMAL_PRIORITY_CLASS
        REALTIME_PRIORITY_CLASS = cext.REALTIME_PRIORITY_CLASS

    # psutil.Process.ionice(ioclass=…)
    class ProcIOPriorityClass(enum.IntEnum):
        IOPRIO_VERYLOW = 0
        IOPRIO_LOW = 1
        IOPRIO_NORMAL = 2
        IOPRIO_HIGH = 3
