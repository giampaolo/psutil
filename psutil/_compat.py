# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Module which provides compatibility with older Python versions.
This is more future-compatible rather than the opposite (prefer latest
Python 3 way of doing things).
"""

import contextlib
import sys


# fmt: off
__all__ = [
    # constants
    "PY3",
    # contextlib module
    "redirect_stderr",
]
# fmt: on


PY3 = sys.version_info[0] >= 3
_SENTINEL = object()


# --- stdlib additions


# python 3.3
try:
    from subprocess import TimeoutExpired as SubprocessTimeoutExpired
except ImportError:

    class SubprocessTimeoutExpired(Exception):
        pass


# python 3.5
try:
    from contextlib import redirect_stderr
except ImportError:

    @contextlib.contextmanager
    def redirect_stderr(new_target):
        original = sys.stderr
        try:
            sys.stderr = new_target
            yield new_target
        finally:
            sys.stderr = original
