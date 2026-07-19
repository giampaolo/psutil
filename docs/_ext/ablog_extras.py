# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Ablog tweaks."""

import pathlib
import xml.etree.ElementTree as ET

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def merge_ablog_posts(app, env, docnames, other):
    if hasattr(other, "ablog_posts"):
        if not hasattr(env, "ablog_posts"):
            env.ablog_posts = {}
        env.ablog_posts.update(other.ablog_posts)


def dedupe_sitemap(app, exception):
    # ablog re-renders the blog index on top of blog.rst, so
    # sphinx-sitemap sees that page twice and lists its URL twice.
    if exception:
        return
    path = pathlib.Path(app.outdir) / app.config.sitemap_filename
    if not path.is_file():
        return
    ET.register_namespace("", SITEMAP_NS)
    tree = ET.parse(path)
    root = tree.getroot()
    seen = set()
    for url in list(root):
        loc = url.findtext(f"{{{SITEMAP_NS}}}loc")
        if loc in seen:
            root.remove(url)
        else:
            seen.add(loc)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def setup(app):
    app.connect("env-merge-info", merge_ablog_posts)
    # priority > 500 so this runs after sphinx-sitemap writes the file.
    app.connect("build-finished", dedupe_sitemap, priority=600)
    # Ablog stores posts on the build environment but doesn't merge
    # them back when Sphinx builds in parallel, so worker results get
    # dropped. See https://github.com/sunpy/ablog/pull/330.
    app.extensions["ablog"].parallel_read_safe = True
    return {"parallel_read_safe": True, "parallel_write_safe": True}
