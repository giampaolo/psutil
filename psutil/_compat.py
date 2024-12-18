# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Module which provides compatibility with older Python versions.
This is more future-compatible rather than the opposite (prefer latest
Python 3 way of doing things).
"""

import contextlib
import os
import sys


# fmt: off
__all__ = [
    # constants
    "PY3",
    # builtins
    "super",
    # shutil module
    "which", "get_terminal_size",
    # contextlib module
    "redirect_stderr",
]
# fmt: on


PY3 = sys.version_info[0] >= 3
_SENTINEL = object()


# --- stdlib additions


# python 3.3
try:
    from shutil import which
except ImportError:

    def which(cmd, mode=os.F_OK | os.X_OK, path=None):
        """Given a command, mode, and a PATH string, return the path which
        conforms to the given mode on the PATH, or None if there is no such
        file.

        `mode` defaults to os.F_OK | os.X_OK. `path` defaults to the result
        of os.environ.get("PATH"), or can be overridden with a custom search
        path.
        """

        def _access_check(fn, mode):
            return (
                os.path.exists(fn)
                and os.access(fn, mode)
                and not os.path.isdir(fn)
            )

        if os.path.dirname(cmd):
            if _access_check(cmd, mode):
                return cmd
            return None

        if path is None:
            path = os.environ.get("PATH", os.defpath)
        if not path:
            return None
        path = path.split(os.pathsep)

        if sys.platform == "win32":
            if os.curdir not in path:
                path.insert(0, os.curdir)

            pathext = os.environ.get("PATHEXT", "").split(os.pathsep)
            if any(cmd.lower().endswith(ext.lower()) for ext in pathext):
                files = [cmd]
            else:
                files = [cmd + ext for ext in pathext]
        else:
            files = [cmd]

        seen = set()
        for dir in path:
            normdir = os.path.normcase(dir)
            if normdir not in seen:
                seen.add(normdir)
                for thefile in files:
                    name = os.path.join(dir, thefile)
                    if _access_check(name, mode):
                        return name
        return None


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
