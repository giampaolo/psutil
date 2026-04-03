# Copyright (c) 2009, Giampaolo Rodola. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Sphinx extension providing the :field:`name` role for marking named
tuple fields in the API doc.
"""

from docutils import nodes


def field_role(
    name, rawtext, text, lineno, inliner, options=None, content=None
):
    """Render :field:`name` as inline code (monospace bold)."""
    node = nodes.literal(rawtext, text, classes=["ntuple-field"])
    return [node], []


def setup(app):
    app.add_role("field", field_role)
