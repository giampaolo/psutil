#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A clone of md5sum utility on UNIX. Prints MD5 checksums of file(s)."""

import glob
import hashlib
import os
import sys


def csum(file, kind):
    h = hashlib.new(kind)
    with open(file, "rb") as f:
        h.update(f.read())
        return h.hexdigest()


def main():
    files = sys.argv[1:]
    if not files:
        sys.exit("provide an argument")
    if os.name == 'nt' and '*' in files[0]:
        files = glob.glob(files[0])
    for file in files:
        md5 = csum(file, "md5")
        sha256 = csum(file, "sha256")
        print("%s md5:%s sha256:%s" % (os.path.basename(file), md5, sha256))


if __name__ == "__main__":
    main()
