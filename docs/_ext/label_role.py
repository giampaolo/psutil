# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Sphinx role providing the changelog labels, e.g. :label:`critical`.
Also fails the build on an unknown [Platform] tag in changelog.rst.
"""

import re

from docutils import nodes
from sphinx.util import logging

logger = logging.getLogger(__name__)

LABELS = ("breaking", "critical", "build-fail", "memleak")
PLATFORMS = (
    "Linux",
    "Windows",
    "macOS",
    "FreeBSD",
    "NetBSD",
    "OpenBSD",
    "SunOS",
    "AIX",
    "BSD",
    "POSIX",
    "PyPy",
)
# entry prefix, e.g. "- :gh:`123`, [Linux], :label:`critical`: "
PREFIX_RE = re.compile(
    r"^[ \t]*- ((?:(?::(?:gh|pr|commit|label):`[^`]+`|\[[^\]]+\])[,:]\s+)+)",
    re.MULTILINE,
)


def label_role(
    name, rawtext, text, lineno, inliner, options=None, content=None
):
    label = text.strip().lower()
    if label not in LABELS:
        msg = inliner.reporter.error(
            f"unknown label {text!r}, expected one of {', '.join(LABELS)}",
            line=lineno,
        )
        return [inliner.problematic(rawtext, rawtext, msg)], [msg]
    node = nodes.inline(
        rawtext, label, classes=["cl-label", f"cl-label-{label}"]
    )
    return [node], []


def check_platform_tags(app, docname, source):
    if docname != "changelog":
        return
    text = source[0]
    for m in PREFIX_RE.finditer(text):
        for tag in re.findall(r"\[([^\]]+)\]", m.group(1)):
            if tag not in PLATFORMS:
                logger.error(
                    "unknown platform tag [%s], expected one of %s",
                    tag,
                    ", ".join(PLATFORMS),
                    location=(docname, text.count("\n", 0, m.start()) + 1),
                )


def setup(app):
    app.add_role("label", label_role)
    app.connect("source-read", check_platform_tags)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
