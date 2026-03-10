# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Sphinx extension for adding anchors to each section in
docs/changelog.rst.

This script gets called on `make html`, and adds numeric anchors for
version titles (e.g., 7.2.3 -> #723).
"""

import re

from docutils import nodes

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def add_version_anchors(app, doctree):
    if app.env.docname != "changelog":
        return

    for node in doctree.traverse(nodes.section):
        title = node.next_node(nodes.title)
        if not title:
            continue

        text = title.astext()
        if VERSION_RE.match(text):
            anchor = text.replace(".", "")
            if anchor not in node["ids"]:
                node["ids"].insert(0, anchor)


def setup(app):
    app.connect("doctree-read", add_version_anchors)
