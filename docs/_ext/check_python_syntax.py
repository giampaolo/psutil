# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Sphinx extension that checks the Python syntax of code blocks in the
documentation. This script gets called on `make html`.
"""

import ast

import docutils.nodes
import sphinx.errors


def check_python_blocks(app, doctree, docname):
    path = app.env.doc2path(docname)

    for node in doctree.traverse(docutils.nodes.literal_block):
        lang = node.get("language")
        if lang not in {"python", "py"}:
            continue

        code = node.astext()

        # skip empty blocks
        if not code.strip():
            continue

        # skip REPL examples containing >>>
        if ">>>" in code:
            continue

        try:
            ast.parse(code)
        except SyntaxError as err:
            lineno = node.line or "?"
            msg = (
                f"invalid Python syntax in {path}:{lineno}:\n\n{code}\n\n{err}"
            )
            raise sphinx.errors.SphinxError(msg) from None


def setup(app):
    app.connect("doctree-resolved", check_python_blocks)
