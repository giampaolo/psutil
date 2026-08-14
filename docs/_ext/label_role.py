# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Sphinx role providing the changelog labels, e.g. :label:`critical`."""

from docutils import nodes

LABELS = ("breaking", "critical", "build-fail", "memleak")


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


def setup(app):
    app.add_role("label", label_role)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
