#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Prints release announce based on docs/changelog.rst file content.
See: https://pip.pypa.io/en/stable/reference/pip_install/#hash-checking-mode.

"""

import os
import re
import subprocess
import sys

from psutil import __version__

HERE = os.path.abspath(os.path.dirname(__file__))
ROOT = os.path.realpath(os.path.join(HERE, '..', '..'))
CHANGELOG = os.path.join(ROOT, 'docs', 'changelog.rst')
PRINT_HASHES_SCRIPT = os.path.join(
    ROOT, 'scripts', 'internal', 'print_hashes.py'
)

PRJ_NAME = 'psutil'
PRJ_VERSION = __version__
PRJ_URL_HOME = 'https://github.com/giampaolo/psutil'
PRJ_URL_DOC = 'http://psutil.readthedocs.io'
PRJ_URL_DOWNLOAD = 'https://pypi.org/project/psutil/#files'
PRJ_URL_WHATSNEW = 'https://psutil.readthedocs.io/en/latest/changelog.html'

template = """\
Hello all,
I'm glad to announce the release of {prj_name} {prj_version}:
{prj_urlhome}

About
=====

psutil (process and system utilities) is a cross-platform library for \
retrieving information on running processes and system utilization (CPU, \
memory, disks, network) in Python. It is useful mainly for system \
monitoring, profiling and limiting process resources and management of \
running processes. It implements many functionalities offered by command \
line tools such as: ps, top, lsof, netstat, ifconfig, who, df, kill, free, \
nice, ionice, iostat, iotop, uptime, pidof, tty, taskset, pmap. It \
currently supports Linux, Windows, macOS, Sun Solaris, FreeBSD, OpenBSD, \
NetBSD and AIX. Supported Python versions are cPython 3.7+ and PyPy.

What's new
==========

{changes}

Links
=====

- Home page: {prj_urlhome}
- Download: {prj_urldownload}
- Documentation: {prj_urldoc}
- What's new: {prj_urlwhatsnew}

Hashes
======

{hashes}

--

Giampaolo - https://gmpy.dev/about
"""


def rst_to_text(s):
    """Strip RST/Sphinx markup, returning plain text."""
    # :gh:`123` -> #123
    s = re.sub(r':gh:`(\d+)`', r'#\1', s)
    # :meth:, :func:, :class:, :attr:, :exc:, :mod:, :data:, etc.
    # :role:`text` -> text (also handles :role:`~text` and :role:`mod.text`)
    s = re.sub(r':[a-z]+:`~?([^`]+)`', r'\1', s)
    # ``code`` -> `code`
    s = re.sub(r'``([^`]+)``', r'`\1`', s)
    # **bold** -> bold
    s = re.sub(r'\*\*([^*]+)\*\*', r'\1', s)
    # *italic* -> italic
    s = re.sub(r'\*([^*]+)\*', r'\1', s)
    return s


def get_changes():
    """Get the most recent changes for this release by parsing
    docs/changelog.rst file.
    """
    with open(CHANGELOG) as f:
        lines = f.readlines()

    block = []

    # eliminate the part preceding the first block
    while lines:
        line = lines.pop(0)
        if line.startswith('^^^^'):
            break
    else:
        raise ValueError("something wrong")

    lines.pop(0)
    while lines:
        line = lines.pop(0)
        line = line.rstrip()
        if re.match(r"^- \d+_", line):
            line = re.sub(r"^- (\d+)_", r"- #\1", line)

        if line.startswith('^^^^'):
            break
        block.append(line)
    else:
        raise ValueError("something wrong")

    # eliminate bottom empty lines
    block.pop(-1)
    while not block[-1]:
        block.pop(-1)

    text = "\n".join(block)
    text = rst_to_text(text)
    return text


def main():
    changes = get_changes()
    hashes = (
        subprocess.check_output([sys.executable, PRINT_HASHES_SCRIPT, 'dist/'])
        .strip()
        .decode()
    )
    text = template.format(
        prj_name=PRJ_NAME,
        prj_version=PRJ_VERSION,
        prj_urlhome=PRJ_URL_HOME,
        prj_urldownload=PRJ_URL_DOWNLOAD,
        prj_urldoc=PRJ_URL_DOC,
        prj_urlwhatsnew=PRJ_URL_WHATSNEW,
        changes=changes,
        hashes=hashes,
    )
    print(text)


if __name__ == '__main__':
    main()
