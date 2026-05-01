# Copyright (c) 2009, Giampaolo Rodola. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Bridge ablog and sphinxext-opengraph for social-card metadata."""

import html

import sphinxext.opengraph

BLOG_DESCRIPTION = "Psutil blog: releases, deep dives, war stories"
DESCRIPTION_OVERRIDE = {}

original_get_description = sphinxext.opengraph.get_description


def patched_get_description(doctree, desc_len, known_titles=None):
    text = DESCRIPTION_OVERRIDE.get("current")
    if text is None:
        return original_get_description(doctree, desc_len, known_titles)
    text = html.escape(text, quote=True)
    if desc_len and len(text) > desc_len:
        text = text[: desc_len - 3] + "..."
    return text


def capture_post_summary(app, pagename, templatename, context, doctree):
    # Get post's summary (the body of the .. post:: directive) and use
    # it in the og preview.
    DESCRIPTION_OVERRIDE.pop("current", None)
    posts = (getattr(app.env, "ablog_posts", {}) or {}).get(pagename) or []
    if not posts:
        return
    excerpt_nodes = posts[0].get("excerpt")
    if not excerpt_nodes:
        return
    text = " ".join(n.astext() for n in excerpt_nodes if hasattr(n, "astext"))
    text = " ".join(text.split())
    if text:
        DESCRIPTION_OVERRIDE["current"] = text


def set_og_type_article(app, pagename, templatename, context, doctree):
    # sphinxext-opengraph hardcodes og:type="website" globally. Override
    # it to "article" for blog posts so social platforms classify them.
    if pagename in getattr(app.env, "ablog_posts", {}):
        meta = context.get("meta")
        if meta is None:
            meta = {}
            context["meta"] = meta
        meta["og:type"] = "article"


def emit_blog_index_meta(app, pagename, templatename, context, doctree):
    # ablog renders blog.html without a doctree, so sphinxext-opengraph
    # skips it and emits no og:* tags.
    if pagename != app.config.blog_path:
        return
    project = app.config.project
    base = app.config.html_baseurl.rstrip("/") + "/"
    fields = [
        ("name", "description", BLOG_DESCRIPTION),
        ("property", "og:title", project + " blog"),
        ("property", "og:type", "website"),
        ("property", "og:url", base + pagename + ".html"),
        ("property", "og:site_name", project),
        ("property", "og:description", BLOG_DESCRIPTION),
        ("property", "og:image", base + "_static/images/logo-psutil.png"),
        ("name", "twitter:card", "summary_large_image"),
    ]
    tags = "\n".join(
        f'<meta {attr}="{key}" content="{val}" />' for attr, key, val in fields
    )
    context["metatags"] = context.get("metatags", "") + tags + "\n"


def setup(app):
    sphinxext.opengraph.get_description = patched_get_description

    # priority < 500 ensures we run before sphinxext-opengraph.
    app.connect("html-page-context", capture_post_summary, priority=300)
    app.connect("html-page-context", set_og_type_article, priority=400)
    app.connect("html-page-context", emit_blog_index_meta)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
