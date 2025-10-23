#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Generate MANIFEST.in file."""

import os
import shlex
import subprocess

SKIP_EXTS = ('.png', '.jpg', '.jpeg', '.svg')
SKIP_FILES = ()
SKIP_PREFIXES = ('.ci/', '.github/')
FILE = "MANIFEST.in"


def cat(path):
    with open(path) as f:
        return f.read()


def sh(cmd):
    return subprocess.check_output(
        shlex.split(cmd), universal_newlines=True
    ).strip()


def main():
    files = set()
    text = []
    for file in sh("git ls-files").split('\n'):
        if (
            file.startswith(SKIP_PREFIXES)
            or os.path.splitext(file)[1].lower() in SKIP_EXTS
            or file in SKIP_FILES
        ):
            continue
        files.add(file)

    for file in sorted(files):
        text.append(f"include {file}")  # noqa: PERF401

    text.append("recursive-exclude docs/_static *")  # noqa: FURB113
    text.append("")
    text = "\n".join(text)

    if cat(FILE) != text:
        with open(FILE, "w") as f:
            f.write(text)
        print(f"{FILE} was updated")


if __name__ == '__main__':
    main()
