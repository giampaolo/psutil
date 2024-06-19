#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Prints release announce based on HISTORY.rst file content.
See: https://pip.pypa.io/en/stable/reference/pip_install/#hash-checking-mode.

"""

import os
import re
import subprocess
import sys

from psutil import __version__


HERE = os.path.abspath(os.path.dirname(__file__))
ROOT = os.path.realpath(os.path.join(HERE, '..', '..'))
HISTORY = os.path.join(ROOT, 'HISTORY.rst')
PRINT_HASHES_SCRIPT = os.path.join(
    ROOT, 'scripts', 'internal', 'print_hashes.py'
)

PRJ_NAME = 'psutil'
PRJ_VERSION = __version__
PRJ_URL_HOME = 'https://github.com/giampaolo/psutil'
PRJ_URL_DOC = 'http://psutil.readthedocs.io'
PRJ_URL_DOWNLOAD = 'https://pypi.org/project/psutil/#files'
PRJ_URL_WHATSNEW = (
    'https://github.com/giampaolo/psutil/blob/master/HISTORY.rst'
)

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
NetBSD and AIX, both 32-bit and 64-bit architectures.  Supported Python \
versions are 2.7 and 3.6+. PyPy is also known to work.

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


def get_changes():
    """Get the most recent changes for this release by parsing
    HISTORY.rst file.
    """
    with open(HISTORY) as f:
        lines = f.readlines()

    block = []

    # eliminate the part preceding the first block
    while lines:
        line = lines.pop(0)
        if line.startswith('===='):
            break
    else:
        raise ValueError("something wrong")

    lines.pop(0)
    while lines:
        line = lines.pop(0)
        line = line.rstrip()
        if re.match(r"^- \d+_", line):
            line = re.sub(r"^- (\d+)_", r"- #\1", line)

        if line.startswith('===='):
            break
        block.append(line)
    else:
        raise ValueError("something wrong")

    # eliminate bottom empty lines
    block.pop(-1)
    while not block[-1]:
        block.pop(-1)

    return "\n".join(block)


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
