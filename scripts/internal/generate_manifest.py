#!/usr/bin/env python

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Generate MANIFEST.in file.
"""

import os
import subprocess


def sh(cmd):
    return subprocess.check_output(
        cmd, shell=True, universal_newlines=True).strip()


def main():
    files = sh("git ls-files").split('\n')
    for file in files:
        if file.startswith('.ci/') or \
                os.path.splitext(file)[1] in ('.png', '.jpg') or \
                file in ('.travis.yml', 'appveyor.yml'):
            continue
        print("include " + file)


if __name__ == '__main__':
    main()
