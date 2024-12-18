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
    # shutil module
    "get_terminal_size",
    # contextlib module
    "redirect_stderr",
]
# fmt: on


PY3 = sys.version_info[0] >= 3
_SENTINEL = object()


# --- stdlib additions


# python 3.3
try:
    from shutil import get_terminal_size
except ImportError:

    def get_terminal_size(fallback=(80, 24)):
        try:
            import fcntl
            import struct
            import termios
        except ImportError:
            return fallback
        else:
            try:
                # This should work on Linux.
                res = struct.unpack(
                    'hh', fcntl.ioctl(1, termios.TIOCGWINSZ, '1234')
                )
                return (res[1], res[0])
            except Exception:  # noqa: BLE001
                return fallback


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
