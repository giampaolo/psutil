# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Constants for psutil APIs."""

import enum

from ._common import LINUX
from ._common import WINDOWS

__all__ = ["NicDuplex", "BatteryTime"]


# net_if_stats()
class NicDuplex(enum.IntEnum):
    NIC_DUPLEX_FULL = 2
    NIC_DUPLEX_HALF = 1
    NIC_DUPLEX_UNKNOWN = 0


# sensors_battery()
class BatteryTime(enum.IntEnum):
    POWER_TIME_UNKNOWN = -1
    POWER_TIME_UNLIMITED = -2


if WINDOWS:
    from . import _psutil_windows as cext

    # psutil.Process.nice()
    class ProcPriority(enum.IntEnum):
        ABOVE_NORMAL_PRIORITY_CLASS = cext.ABOVE_NORMAL_PRIORITY_CLASS
        BELOW_NORMAL_PRIORITY_CLASS = cext.BELOW_NORMAL_PRIORITY_CLASS
        HIGH_PRIORITY_CLASS = cext.HIGH_PRIORITY_CLASS
        IDLE_PRIORITY_CLASS = cext.IDLE_PRIORITY_CLASS
        NORMAL_PRIORITY_CLASS = cext.NORMAL_PRIORITY_CLASS
        REALTIME_PRIORITY_CLASS = cext.REALTIME_PRIORITY_CLASS

    __all__.append("ProcPriority")


if LINUX:

    # psutil.Process.ionice()
    class ProcIOPriority(enum.IntEnum):
        # ioprio_* constants http://linux.die.net/man/2/ioprio_get
        IOPRIO_CLASS_NONE = 0
        IOPRIO_CLASS_RT = 1
        IOPRIO_CLASS_BE = 2
        IOPRIO_CLASS_IDLE = 3

    __all__.append("ProcIOPriority")
