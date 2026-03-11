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
        if lang not in {"python", "py", "pycon"}:
            continue

        code = node.astext()

        if lang == "pycon":
            lines = []
            for line in code.splitlines():
                if line.startswith((">>> ", "... ")):
                    lines.append(line[4:])  # noqa: PERF401
            code = "\n".join(lines)

        try:
            ast.parse(code)
        except SyntaxError:
            lineno = node.line or "?"
            msg = f"invalid Python syntax in {path}:{lineno}:\n\n{code}"
            raise sphinx.errors.SphinxError(msg) from None


def setup(app):
    app.connect("doctree-resolved", check_python_blocks)
