# Copyright (c) 2009, Giampaolo Rodola. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Make the custom 404 page work under dirhtml + static hosting.

Two gaps sphinx-notfound-page / dirhtml leave, both about URLs on the
404 page:

- notfound absolutizes the 404's chrome and images but leaves body
  cross-references (:doc:, :class:) relative. Those break when the 404
  is served from a deep path, so absolutize them too, reusing
  notfound's own helper.
- dirhtml writes the 404 as ``404/index.html``. GitHub Pages and
  Starlette (sphinx-autobuild) serve the custom 404 from ``/404.html``
  at the root, so materialize it there.
"""

import shutil
from pathlib import Path

from docutils import nodes
from notfound.utils import replace_uris


def absolutize_404_links(app, doctree, docname):
    if docname == app.config.notfound_pagename:
        replace_uris(app, doctree, nodes.reference, "refuri")


def absolutize_404_content_root(app, pagename, templatename, context, doctree):
    # data-content_root is relative; JS (search, highlight) uses it to
    # build URLs. On the 404, served from any depth, it must be
    # absolute or those URLs resolve against the wrong base.
    if pagename == app.config.notfound_pagename:
        context["content_root"] = app.config.notfound_urls_prefix


def write_root_404(app, exception):
    if exception is not None:
        return
    name = app.config.notfound_pagename
    src = Path(app.outdir) / name / "index.html"
    if src.is_file():
        shutil.copyfile(src, Path(app.outdir) / f"{name}.html")


def setup(app):
    app.connect("doctree-resolved", absolutize_404_links)
    app.connect("html-page-context", absolutize_404_content_root)
    app.connect("build-finished", write_root_404)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
