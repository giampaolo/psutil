# Copyright (c) 2009, Giampaolo Rodola. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Inject glossary terms into the Jinja context to enable rendering of
the right-side TOC on /glossary.
"""

from docutils import nodes


def on_html_page_context(app, page_name, template_name, context, doctree):
    if page_name != "glossary":
        return
    glossary_doctree = app.env.get_doctree("glossary")
    terms = []
    for term in glossary_doctree.findall(nodes.term):
        ids = term.get("ids") or []
        if ids:
            terms.append({"id": ids[0], "text": term.astext()})
    terms.sort(key=lambda t: t["text"].lower())
    context["glossary_terms"] = terms


def setup(app):
    app.connect("html-page-context", on_html_page_context)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
