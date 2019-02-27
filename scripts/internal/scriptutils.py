#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utils shared by all files in scripts/internal."""

from __future__ import print_function
import sys

from psutil._compat import lru_cache


__all__ = ['hilite', 'printerr', 'exit']


@lru_cache()
def _term_supports_colors(file=sys.stdout):
    try:
        import curses
        assert file.isatty()
        curses.setupterm()
        assert curses.tigetnum("colors") > 0
    except Exception:
        return False
    else:
        return True


def hilite(s, ok=True, bold=False):
    """Return an highlighted version of 'string'."""
    if not _term_supports_colors():
        return s
    attr = []
    if ok is None:  # no color
        pass
    elif ok:   # green
        attr.append('32')
    else:   # red
        attr.append('31')
    if bold:
        attr.append('1')
    return '\x1b[%sm%s\x1b[0m' % (';'.join(attr), s)


def printerr(s):
    print(hilite(s, ok=False), file=sys.stderr)


def exit(msg=""):
    if msg:
        printerr(msg)
    sys.exit(1)
