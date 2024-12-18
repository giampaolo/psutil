# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Module which provides compatibility with older Python versions.
This is more future-compatible rather than the opposite (prefer latest
Python 3 way of doing things).
"""

import sys


# fmt: off
__all__ = [
    # constants
    "PY3",
]
# fmt: on


PY3 = sys.version_info[0] >= 3
_SENTINEL = object()
