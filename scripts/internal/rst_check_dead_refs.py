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
import os
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
RE_BACKTICK_REF = re.compile(r'`([^`<\n]+)`_(?!_)')
# bare reference: BPO-12442_  (word chars and hyphens, no backticks)
RE_BARE_REF = re.compile(r'(?<![`\w])([A-Za-z0-9][\w-]*)_(?!_)(?![\w`*{])')
# .. include:: somefile.rst
RE_INCLUDE = re.compile(r'^\.\. include::\s*(\S+)', re.MULTILINE)


def line_number(text, pos):
    return text.count('\n', 0, pos) + 1


def read_with_includes(path, _seen=None):
    """Return file text plus the text of any ``.. include::`` files."""
    if _seen is None:
        _seen = set()
    path = os.path.normpath(path)
    if path in _seen:
        return ""
    _seen.add(path)
    try:
        with open(path) as f:
            text = f.read()
    except OSError:
        return ""
    base = os.path.dirname(path)
    for m in RE_INCLUDE.finditer(text):
        inc = os.path.join(base, m.group(1))
        text += read_with_includes(inc, _seen)
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", metavar="FILE")
    args = parser.parse_args()

    # Pass 1: collect all defined targets across all files.
    # Targets from ".. include::" files are also collected so that
    # cross-file references resolve correctly.
    all_targets = set()
    # URL-only targets defined directly in a file (not via include), used
    # to detect targets that are defined but never referenced.
    url_targets = {}

    for path in args.files:
        # Use expanded text (with includes) so cross-file references resolve.
        expanded = read_with_includes(path)
        for m in RE_ANY_TARGET.finditer(expanded):  # noqa: FURB142
            all_targets.add(m.group(1).strip().lower())
        # Only record URL targets from the file itself, not from includes,
        # so we don't falsely report included targets as unreferenced.
        with open(path) as f:
            own_text = f.read()
        for m in RE_URL_TARGET.finditer(own_text):
            name = m.group(1).strip()
            url_targets[name.lower()] = (
                name,
                path,
                line_number(own_text, m.start()),
            )

    # Pass 2: collect all references (with file + line).
    all_refs = []  # list of (lower-case name, original, file, lineno)
    referenced = set()  # lower-case names of all referenced targets

    for path in args.files:
        with open(path) as f:
            text = f.read()

        for m in RE_BACKTICK_REF.finditer(text):
            name = m.group(1).strip()
            all_refs.append((
                name.lower(),
                name,
                path,
                line_number(text, m.start()),
            ))
            referenced.add(name.lower())

        for m in RE_BARE_REF.finditer(text):
            name = m.group(1).strip()
            if name.lower() not in referenced:
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
