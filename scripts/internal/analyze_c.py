#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Run the clang static analyzer over the C files built on this
platform, with the same macros setup.py uses. Exit with 1 if it
reports anything. Run via `make lint-c-analyze`.
"""

import concurrent.futures
import os
import subprocess
import sys
import sysconfig

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

import setup  # noqa: E402


def get_cmd(src):
    cmd = ["clang", "--analyze", "-Xclang", "-analyzer-output=text"]
    cmd += ["-o", os.devnull]
    for name, value in setup.ext.define_macros:
        if value is None:
            cmd.append(f"-D{name}")
        else:
            cmd.append(f"-D{name}={value}")
    for path in setup.ext.include_dirs + [sysconfig.get_paths()["include"]]:
        cmd.append(f"-I{path}")
    cmd.append(src)
    return cmd


def analyze(src):
    p = subprocess.run(
        get_cmd(src), capture_output=True, text=True, check=False
    )
    return p.returncode, p.stdout + p.stderr


def main():
    if setup.WINDOWS:
        sys.exit("Windows is not supported")
    sources = setup.ext.sources
    failed = False
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for rc, output in executor.map(analyze, sources):
            if rc != 0 or output:
                print(output, end="")
                failed = True
    if failed:
        sys.exit(1)
    print(f"clang static analyzer: {len(sources)} files, no issues")


if __name__ == "__main__":
    main()
