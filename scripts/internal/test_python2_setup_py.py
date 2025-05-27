#!/usr/bin/env python2

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Invoke setup.py with Python 2.7, make sure it fails but not due to
SyntaxError, and that it prints a meaningful error message.
"""

import os
import subprocess
import sys

ROOT_DIR = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)


def main():
    if sys.version_info[:2] != (2, 7):
        raise RuntimeError("this script is supposed to be run with python 2.7")
    setup_py = os.path.join(ROOT_DIR, "setup.py")
    p = subprocess.Popen(
        [sys.executable, setup_py],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = p.communicate()
    assert p.wait() == 1
    assert not stdout, stdout
    assert "psutil no longer supports Python 2.7" in stderr, stderr
    assert "Latest version supporting Python 2.7 is" in stderr, stderr


if __name__ == "__main__":
    main()
