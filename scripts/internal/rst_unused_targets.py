#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola. All rights reserved.
# Use of this source code is governed by a BSD-style license that can
# be found in the LICENSE file.

"""Check .rst files for URL hyperlink targets that are defined but
never referenced.

Undefined references (backtick refs pointing at a missing target) are
already caught by Sphinx during the docs build, so this script only
covers the unused-target case.
"""

import argparse
import os
import re
import subprocess
import sys

# .. _`Foo`: https://...   or   .. _foo: https://...
RE_URL_TARGET = re.compile(r"^\.\. _`?([^`\n:]+)`?:\s*https?://", re.MULTILINE)

# `Foo Bar`_  but NOT  `text <url>`_  and NOT  `text`__
RE_BACKTICK_REF = re.compile(r"`([^`<\n]+)`_(?!_)")

# bare ref:  BPO-12442_
RE_BARE_REF = re.compile(r"(?<![`\w])([A-Za-z][\w-]*)_(?!\w)")


def all_rst_files():
    out = subprocess.check_output(["git", "ls-files", "*.rst"], text=True)
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", metavar="FILE")
    args = parser.parse_args()

    # We only report on definitions in the input files, but we collect
    # "used" references from every tracked .rst file. Without this the
    # script would false-positive when invoked on a subset (e.g. the
    # pre-commit hook scoping to changed files only).
    input_paths = {os.path.abspath(f) for f in args.files}
    defined = {}  # lower_name -> (name, path, lineno)
    used = set()
    for path in all_rst_files():
        with open(path) as f:
            text = f.read()
        if os.path.abspath(path) in input_paths:
            for m in RE_URL_TARGET.finditer(text):
                name = m.group(1).strip()
                lineno = text.count("\n", 0, m.start()) + 1
                defined[name.lower()] = (name, path, lineno)
        for regex in (RE_BACKTICK_REF, RE_BARE_REF):
            used.update(
                m.group(1).strip().lower() for m in regex.finditer(text)
            )

    errors = sorted(
        (path, lineno, f"unreferenced hyperlink target: {name!r}")
        for key, (name, path, lineno) in defined.items()
        if key not in used
    )
    for path, lineno, msg in errors:
        print(f"{path}:{lineno}: {msg}")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
