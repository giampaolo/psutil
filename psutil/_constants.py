# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Constants for psutil APIs."""

import enum

from ._common import LINUX

__all__ = ['NicDuplex', 'BatteryTime', 'Priority', 'IOPriority']


# net_if_stats()
class NicDuplex(enum.IntEnum):
    NIC_DUPLEX_FULL = 2
    NIC_DUPLEX_HALF = 1
    NIC_DUPLEX_UNKNOWN = 0


# sensors_battery()
class BatteryTime(enum.IntEnum):
    POWER_TIME_UNKNOWN = -1
    POWER_TIME_UNLIMITED = -2


# Process priority (Windows)
try:
    from ._psutil_windows import ABOVE_NORMAL_PRIORITY_CLASS
    from ._psutil_windows import BELOW_NORMAL_PRIORITY_CLASS
    from ._psutil_windows import HIGH_PRIORITY_CLASS
    from ._psutil_windows import IDLE_PRIORITY_CLASS
    from ._psutil_windows import NORMAL_PRIORITY_CLASS
    from ._psutil_windows import REALTIME_PRIORITY_CLASS

    class Priority(enum.IntEnum):
        ABOVE_NORMAL_PRIORITY_CLASS = ABOVE_NORMAL_PRIORITY_CLASS
        BELOW_NORMAL_PRIORITY_CLASS = BELOW_NORMAL_PRIORITY_CLASS
        HIGH_PRIORITY_CLASS = HIGH_PRIORITY_CLASS
        IDLE_PRIORITY_CLASS = IDLE_PRIORITY_CLASS
        NORMAL_PRIORITY_CLASS = NORMAL_PRIORITY_CLASS
        REALTIME_PRIORITY_CLASS = REALTIME_PRIORITY_CLASS

except ImportError:
    # Not on Windows
    Priority = None


if LINUX:

    # ioprio_* constants http://linux.die.net/man/2/ioprio_get
    class IOPriority(enum.IntEnum):
        IOPRIO_CLASS_NONE = 0
        IOPRIO_CLASS_RT = 1
        IOPRIO_CLASS_BE = 2
        IOPRIO_CLASS_IDLE = 3
