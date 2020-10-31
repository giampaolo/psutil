#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Prints MD5/SHA hashes of all files found in dist/ directory.
"""

import os
import hashlib
import sys

import psutil


HERE = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.realpath(os.path.join(HERE, "..", ".."))


def gethash(file, kind):
    h = hashlib.new(kind)
    with open(file, 'rb') as f:
        h.update(f.read())
        return h.hexdigest()


def getver(name):
    name = name.rstrip('.tar.gz')
    return name.split('-')[1]


def main():
    sdist = os.path.join(ROOT_DIR, 'dist')
    ls = sorted(os.listdir(sdist))
    if not ls:
        sys.exit('dist directory is empty')
    version = getver(ls[0])
    assert psutil.__version__ == version
    for name in ls:
        assert version == getver(name)
        file = os.path.join(sdist, name)
        print(name)
        print("    SHA256: %s" % gethash(file, 'sha256'))
        print("    MD5: %s" % gethash(file, 'md5'))


main()
