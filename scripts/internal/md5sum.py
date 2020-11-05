#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A clone of md5sum utility on UNIX. Prints MD5 checksums of file(s)."""

import os
import hashlib
import sys


def md5(file):
    h = hashlib.new("md5")
    with open(file, "rb") as f:
        h.update(f.read())
        return h.hexdigest()


def main():
    files = sys.argv[1:]
    if not files:
        sys.exit("provide an argument")
    for file in files:
        print("%s %s" % (os.path.basename(file), md5(file)))


if __name__ == "__main__":
    main()
