#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Prints files hashes, see:
https://pip.pypa.io/en/stable/reference/pip_install/#hash-checking-mode.
"""

import argparse
import hashlib
import os


def csum(file, kind):
    h = hashlib.new(kind)
    with open(file, "rb") as f:
        h.update(f.read())
        return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'dir', type=str, help='directory containing tar.gz or wheel files'
    )
    args = parser.parse_args()
    for name in sorted(os.listdir(args.dir)):
        file = os.path.join(args.dir, name)
        if os.path.isfile(file):
            md5 = csum(file, "md5")
            sha256 = csum(file, "sha256")
            print(
                "%s\nmd5: %s\nsha256: %s\n"
                % (os.path.basename(file), md5, sha256)
            )
        else:
            print("skipping %r (not a file)" % file)


if __name__ == "__main__":
    main()
