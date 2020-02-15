#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Fix some flake8 errors by rewriting files for which flake8 emitted
an error/warning. Usage (from the root dir):

    $ python3 -m flake8 --exit-zero | python3 scripts/fix_flake8.py
"""

import sys
import tempfile
import shutil
from collections import defaultdict
from collections import namedtuple
from pprint import pprint as pp  # NOQA


ntentry = namedtuple('ntentry', 'msg, issue, lineno, pos, descr')


# =====================================================================
# utils
# =====================================================================


def enter_pdb():
    from pdb import set_trace as st  # trick GIT commit hook
    sys.stdin = open('/dev/tty')
    st()


def read_lines(fname):
    with open(fname, 'rt') as f:
        return f.readlines()


def read_line(fname, lineno):
    with open(fname, 'rt') as f:
        for i, line in enumerate(f, 1):
            if i == lineno:
                return line
    raise ValueError("lineno too big")


def write_file(fname, newlines):
    with tempfile.NamedTemporaryFile('wt', delete=False) as f:
        for line in newlines:
            f.write(line)
    shutil.move(f.name, fname)


# =====================================================================
# handlers
# =====================================================================


def handle_f401(fname, lineno):
    """ This is 'module imported but not used'
    Able to handle this case:
        import os

    ...but not this:
        from os import listdir
    """
    line = read_line(fname, lineno).strip()
    if line.startswith('import '):
        return True
    else:
        mods = line.partition(' import ')[2]  # everything after import
        return ',' not in mods


# =====================================================================
# converters
# =====================================================================


def remove_lines(fname, entries):
    """Check if we should remove lines, then do it.
    Return the numner of lines removed.
    """
    to_remove = []
    for entry in entries:
        msg, issue, lineno, pos, descr = entry
        # 'module imported but not used'
        if issue == 'F401' and handle_f401(fname, lineno):
            to_remove.append(lineno)
        # 'blank line(s) at end of file'
        elif issue == 'W391':
            lines = read_lines(fname)
            i = len(lines) - 1
            while lines[i] == '\n':
                to_remove.append(i + 1)
                i -= 1
        # 'too many blank lines'
        elif issue == 'E303':
            howmany = descr.replace('(', '').replace(')', '')
            howmany = int(howmany[-1])
            for x in range(lineno - howmany, lineno):
                to_remove.append(x)

    if to_remove:
        newlines = []
        for i, line in enumerate(read_lines(fname), 1):
            if i not in to_remove:
                newlines.append(line)
        print("removing line(s) from %s" % fname)
        write_file(fname, newlines)

    return len(to_remove)


def add_lines(fname, entries):
    """Check if we should remove lines, then do it.
    Return the numner of lines removed.
    """
    EXPECTED_BLANK_LINES = (
        'E302',  # 'expected 2 blank limes, found 1'
        'E305')  # ìexpected 2 blank lines after class or fun definition'
    to_add = {}
    for entry in entries:
        msg, issue, lineno, pos, descr = entry
        if issue in EXPECTED_BLANK_LINES:
            howmany = 2 if descr.endswith('0') else 1
            to_add[lineno] = howmany

    if to_add:
        newlines = []
        for i, line in enumerate(read_lines(fname), 1):
            if i in to_add:
                newlines.append('\n' * to_add[i])
            newlines.append(line)
        print("adding line(s) to %s" % fname)
        write_file(fname, newlines)

    return len(to_add)


# =====================================================================
# main
# =====================================================================


def build_table():
    table = defaultdict(list)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            break
        fields = line.split(':')
        fname, lineno, pos = fields[:3]
        issue = fields[3].split()[0]
        descr = fields[3].strip().partition(' ')[2]
        lineno, pos = int(lineno), int(pos)
        table[fname].append(ntentry(line, issue, lineno, pos, descr))
    return table


def main():
    table = build_table()

    # remove lines (unused imports)
    removed = 0
    for fname, entries in table.items():
        removed += remove_lines(fname, entries)
    if removed:
        print("%s lines were removed from some file(s); please re-run" %
              removed)
        return

    # add lines (missing \n between functions/classes)
    added = 0
    for fname, entries in table.items():
        added += add_lines(fname, entries)
    if added:
        print("%s lines were added from some file(s); please re-run" %
              added)
        return


main()
