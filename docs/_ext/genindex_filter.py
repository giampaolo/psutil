# Copyright (c) 2009, Giampaolo Rodola. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Post-process genindex.html to clean up index entry labels.

Transforms:
    <a href="...">NAME (qualifier)</a>

Into:
    <a href="...">NAME</a> <span class="index-qualifier">(qualifier)</span>

Also shortens verbose Sphinx qualifiers:
  (in module psutil)    → (function) if NAME ends with "()", else (constant)
  (class in psutil)     → (class)
  (exception in psutil) → (exception)
"""

import pathlib
import re

# Matches <a href="...">NAME (qualifier)</a> where NAME does not start
# with "(" — leaving pure-paren sub-entries like "(psutil.Foo method)" alone.
REGEX = re.compile(r'<a href="([^"]+)">([^(<][^<]*?) (\([^)]+\))</a>')


def replace(m):
    href, name, qualifier = m.group(1), m.group(2), m.group(3)
    if qualifier == "(in module psutil)":
        qualifier = "(function)" if name.endswith("()") else "(constant)"
    elif qualifier == "(class in psutil)":
        qualifier = "(class)"
    elif qualifier == "(exception in psutil)":
        qualifier = "(exception)"
    return (
        f'<a href="{href}">{name}</a> <span'
        f' class="index-qualifier">{qualifier}</span>'
    )


def on_build_finished(app, exception):
    # format (not name) so this also runs under dirhtml, which writes
    # genindex/index.html rather than genindex.html.
    if exception or app.builder.format != "html":
        return
    genindex = pathlib.Path(app.builder.get_outfilename("genindex"))
    if not genindex.exists():
        return
    original = genindex.read_text(encoding="utf-8")
    processed = REGEX.sub(replace, original)
    if processed != original:
        genindex.write_text(processed, encoding="utf-8")


def setup(app):
    app.connect("build-finished", on_build_finished)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
