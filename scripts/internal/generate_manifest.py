#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Generate MANIFEST.in file.
"""

import os
import subprocess


SKIP_EXTS = ('.png', '.jpg', '.jpeg')
SKIP_FILES = ('appveyor.yml')
SKIP_PREFIXES = ('.ci/', '.github/')


def sh(cmd):
    return subprocess.check_output(
        cmd, shell=True, universal_newlines=True).strip()


def main():
    files = sh("git ls-files").split('\n')
    for file in files:
        if file.startswith(SKIP_PREFIXES) or \
                os.path.splitext(file)[1].lower() in SKIP_EXTS or \
                file in SKIP_FILES:
            continue
        print("include " + file)


if __name__ == '__main__':
    main()
