#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Prints files hashes.
See: https://pip.pypa.io/en/stable/reference/pip_install/#hash-checking-mode
"""

import hashlib
import os
import sys


def csum(file, kind):
    h = hashlib.new(kind)
    with open(file, "rb") as f:
        h.update(f.read())
        return h.hexdigest()


def main():
    dir = sys.argv[1]
    for name in sorted(os.listdir(dir)):
        file = os.path.join(dir, name)
        md5 = csum(file, "md5")
        sha256 = csum(file, "sha256")
        print("%s\nmd5: %s\nsha256: %s\n" % (
            os.path.basename(file), md5, sha256))


if __name__ == "__main__":
    main()
