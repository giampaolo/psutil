#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola. All rights reserved.
# Use of this source code is governed by a BSD-style license that can
# be found in the LICENSE file.

"""Check RST files for two classes of reference errors:

1. Hyperlink targets with a URL that are defined but never referenced.
2. Backtick references (`name`_) that point to an undefined target.

Targets and references are resolved across all files passed as arguments,
so cross-file references work correctly.

Usage::

    python3 scripts/internal/rst_check_dead_refs.py docs/*.rst
"""

import argparse
import re
import sys

# .. _`Foo Bar`: https://...   or   .. _foo: https://...  (URL targets only)
RE_URL_TARGET = re.compile(
    r'^\.\. _`?([^`\n:]+)`?\s*:\s*(https?://\S+)',
    re.MULTILINE,
)
# .. _`Foo Bar`:   or   .. _foo:   (any target, with or without URL)
RE_ANY_TARGET = re.compile(
    r'^\.\. _`?([^`\n:]+)`?\s*:',
    re.MULTILINE,
)
# `Foo Bar`_  but NOT  `text <url>`_  and NOT  `text`__
RE_REF = re.compile(r'`([^`<\n]+)`_(?!_)')


def line_number(text, pos):
    return text.count('\n', 0, pos) + 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", metavar="FILE")
    args = parser.parse_args()

    # Pass 1: collect all defined targets across all files.
    all_targets = set()  # lower-case names
    # URL-only targets: lower-case name -> (original name, file)
    url_targets = {}

    for path in args.files:
        with open(path) as f:
            text = f.read()
        for m in RE_ANY_TARGET.finditer(text):  # noqa: FURB142
            all_targets.add(m.group(1).strip().lower())
        for m in RE_URL_TARGET.finditer(text):
            name = m.group(1).strip()
            url_targets[name.lower()] = (
                name,
                path,
                line_number(text, m.start()),
            )

    # Pass 2: collect all backtick references (with file + line).
    all_refs = []  # list of (lower-case name, original, file, lineno)
    referenced = set()  # lower-case names of all referenced targets

    for path in args.files:
        with open(path) as f:
            text = f.read()
        for m in RE_REF.finditer(text):
            name = m.group(1).strip()
            all_refs.append((
                name.lower(),
                name,
                path,
                line_number(text, m.start()),
            ))
            referenced.add(name.lower())

    errors = []

    # Check 1: URL targets that are never referenced.
    for key, (name, path, lineno) in url_targets.items():
        if key not in referenced:
            errors.append(
                (path, lineno, f"unreferenced hyperlink target: {name!r}")
            )

    # Check 2: backtick references with no matching target.
    for key, name, path, lineno in all_refs:
        if key not in all_targets:
            errors.append((path, lineno, f"unknown target name: {name!r}"))

    errors.sort()
    for path, lineno, msg in errors:
        print(f"{path}:{lineno}: {msg}")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
