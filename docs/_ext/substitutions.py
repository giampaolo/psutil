# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Expand {{name}} tokens in the .rst sources.

For values that would otherwise be hardcoded and go stale. Docutils
substitutions (|name|) can't be used: they don't expand inside
`raw:: html` blocks, and the home page stats live in one. This runs
on the raw text, before parsing, so tokens work anywhere.
"""

import datetime

# Date of the first commit. A constant so the build doesn't shell out
# to git (and doesn't depend on a full clone); test_docs.py checks it
# against the real history.
FIRST_COMMIT = datetime.date(2008, 4, 22)


def years_in_development(today=None):
    today = today or datetime.date.today()
    years = today.year - FIRST_COMMIT.year
    if (today.month, today.day) < (FIRST_COMMIT.month, FIRST_COMMIT.day):
        years -= 1
    return years


def substitute(app, docname, source):
    values = {"years_in_development": years_in_development()}
    text = source[0]
    for name, value in values.items():
        text = text.replace("{{" + name + "}}", str(value))
    source[0] = text


def setup(app):
    app.connect("source-read", substitute)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
