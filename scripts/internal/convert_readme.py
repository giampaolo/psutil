#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Convert README.rst format to make it compatible with PyPI (no raw html).
"""

import re
import sys

summary = """\
Quick links
===========

- `Home page <https://github.com/giampaolo/psutil>`_
- `Install <https://github.com/giampaolo/psutil/blob/master/INSTALL.rst>`_
- `Documentation <http://psutil.readthedocs.io>`_
- `Download <https://pypi.org/project/psutil/#files>`_
- `Forum <http://groups.google.com/group/psutil/topics>`_
- `StackOverflow <https://stackoverflow.com/questions/tagged/psutil>`_
- `Blog <https://gmpy.dev/tags/psutil>`_
- `What's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst>`_
"""

funding = """\
Sponsors
========

.. image:: https://github.com/giampaolo/psutil/raw/master/docs/_static/tidelift-logo.png
  :width: 200
  :alt: Alternative text

`Add your logo <https://github.com/sponsors/giampaolo>`__.

Example usages"""


def main():
    with open(sys.argv[1]) as f:
        data = f.read()
    data = re.sub(r".. raw:: html\n+\s+<div align[\s\S]*?/div>", summary, data)
    data = re.sub(r"Sponsors\n========[\s\S]*?Example usages", funding, data)
    print(data)


if __name__ == '__main__':
    main()
