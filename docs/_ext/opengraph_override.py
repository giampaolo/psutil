# Copyright (c) 2009, Giampaolo Rodola. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Bridge ablog and sphinxext-opengraph for social-card metadata."""

import html
import re

import sphinxext.opengraph

BLOG_DESCRIPTION = "Psutil blog: releases, deep dives, war stories"
HOME_OG_TITLE = "psutil: Process and System Utilities for Python"
DESCRIPTION_OVERRIDE = {}

STATIC_DESCRIPTIONS = {
    "index": (
        "psutil is a cross-platform Python library for retrieving "
        "information on running processes and system utilization: CPU, "
        "memory, disks, network and sensors."
    ),
    "api": "psutil full API reference.",
    "install": "How to install psutil.",
}

VIEWPORT_RE = re.compile(r'\s*<meta name="viewport"[^>]*>', re.IGNORECASE)
OG_TITLE_RE = re.compile(r'(<meta property="og:title" content=")[^"]*(")')

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
    static = STATIC_DESCRIPTIONS.get(pagename)
    if static:
        DESCRIPTION_OVERRIDE["current"] = static
        return
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


def blog_index_meta(app, pagename):
    """Title and description for an ablog-generated index page."""
    blog_path = app.config.blog_path
    if pagename == blog_path:
        return app.config.project + " blog", BLOG_DESCRIPTION
    m = re.fullmatch(re.escape(blog_path) + r"/(\d{4})", pagename)
    if m:
        year = m.group(1)
        return (
            f"{app.config.project} blog: {year}",
            f"psutil blog posts published in {year}.",
        )
    return None


def emit_blog_index_meta(app, pagename, templatename, context, doctree):
    # ablog renders the blog index and the year archives without a
    # doctree, so sphinxext-opengraph skips them: no description, no
    # og:* tags at all.
    meta = blog_index_meta(app, pagename)
    if meta is None:
        return
    og_title, description = meta
    project = app.config.project
    base = app.config.html_baseurl.rstrip("/") + "/"
    fields = [
        ("name", "description", description),
        ("property", "og:title", og_title),
        ("property", "og:type", "website"),
        # Builder-derived: dirhtml serves this as blog/, not blog.html.
        ("property", "og:url", base + app.builder.get_target_uri(pagename)),
        ("property", "og:site_name", project),
        ("property", "og:description", description),
        ("property", "og:image", base + "_static/images/logo-psutil.png"),
        (
            "property",
            "og:image:alt",
            (
                "psutil blog: articles on processes, system monitoring "
                "and psutil development"
            ),
        ),
        ("name", "twitter:card", "summary"),
    ]
    tags = "\n".join(
        f'<meta {attr}="{key}" content="{val}" />' for attr, key, val in fields
    )
    if pagename == app.config.blog_path:
        context["feed_title"] = app.config.blog_title or "Blog"
    context["metatags"] = context.get("metatags", "") + tags + "\n"


def finalize_head(app, pagename, templatename, context, doctree):
    tags = context.get("metatags")
    if not tags:
        return
    deduped = VIEWPORT_RE.sub("", tags)
    if pagename == app.config.master_doc:
        deduped = OG_TITLE_RE.sub(
            r"\g<1>" + html.escape(HOME_OG_TITLE, quote=True) + r"\g<2>",
            deduped,
        )
    if deduped != tags:
        context["metatags"] = deduped


def setup(app):
    sphinxext.opengraph.get_description = patched_get_description

    # priority < 500 ensures we run before sphinxext-opengraph.
    app.connect("html-page-context", capture_post_summary, priority=300)
    app.connect("html-page-context", set_og_type_article, priority=400)
    app.connect("html-page-context", emit_blog_index_meta)
    app.connect("html-page-context", finalize_head, priority=600)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
