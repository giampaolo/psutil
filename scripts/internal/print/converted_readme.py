#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Strip raw HTML and other unsupported parts from README.rst
so it renders correctly on PyPI when uploading a new release.
"""

import argparse
import pathlib
import re

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent.parent
README = ROOT_DIR / "README.rst"

quick_links = """\
Quick links
===========

- `Home page <https://github.com/giampaolo/psutil>`_
- `Documentation <https://psutil.io>`_
- `Who uses psutil <https://psutil.io/adoption/>`_
- `Download <https://pypi.org/project/psutil/#files>`_
- `Blog <https://psutil.io/blog/>`_
- `What's new <https://psutil.io/changelog/>`_
"""


def parse_cli():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()


def main():
    parse_cli()

    lines = []

    with open(README) as f:
        excluding = False
        for line in f:
            # Exclude sections which are not meant to be rendered on PYPI
            if line.startswith(".. <PYPI-EXCLUDE>"):
                excluding = True
                continue
            if line.startswith(".. </PYPI-EXCLUDE>"):
                excluding = False
                continue
            if not excluding:
                lines.append(line)

    text = "".join(lines)

    # Rewrite summary
    text = re.sub(
        r".. raw:: html\n+\s+<div align[\s\S]*?/div>", quick_links, text
    )

    print(text)


if __name__ == '__main__':
    main()
