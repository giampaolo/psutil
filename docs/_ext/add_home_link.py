# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Sphinx extension that prepends a 'Home' link to the TOC sidebar.
This script gets called on `make html`.
"""

from sphinx.application import Sphinx


def add_home_link(app: Sphinx, pagename, templatename, context, doctree):
    if "toctree" in context:
        toctree_func = context["toctree"]
        toc_html = toctree_func(
            maxdepth=2, collapse=False, includehidden=False
        )
        # prepend Home link manually
        home_link = '<li class="toctree-l1"><a href="index.html">Home</a></li>'
        context["toctree"] = lambda **_kw: home_link + toc_html


def setup(app: Sphinx):
    app.connect("html-page-context", add_home_link)
