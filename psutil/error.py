#!/usr/bin/env python

# Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This module is deprecated as exceptions are defined in _error.py
and are supposed to be accessed from 'psutil' namespace as in:
- psutil.NoSuchProcess
- psutil.AccessDenied
- psutil.TimeoutExpired
"""

import warnings
from psutil._error import *

warnings.warn("psutil.error module is deprecated and scheduled for removal; " \
              "use psutil namespace instead", category=DeprecationWarning,
               stacklevel=2)
