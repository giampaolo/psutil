# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Insert a metadata banner (date + author + tags + reading time)
right below the H1 of each blog post.

Ablog's sidebar exposes post metadata, but nothing appears near the
title on the post page itself. This extension walks post doctrees
and inserts a small container after the first section's title.
"""

import math
import posixpath

from ablog.blog import Blog
from docutils import nodes

# Conservative words-per-minute estimate for technical prose. Code
# blocks are excluded from the word count.
WPM = 200
SKIP_NODES = (
    nodes.literal_block,
    nodes.doctest_block,
    nodes.comment,
    nodes.raw,
    nodes.system_message,
)


def count_words(node):
    if isinstance(node, SKIP_NODES):
        return 0
    if isinstance(node, nodes.Text):
        return len(node.astext().split())
    return sum(count_words(c) for c in node.children)


def reading_minutes(doctree):
    return max(1, math.ceil(count_words(doctree) / WPM))


def tag_ref(blog, docname, label, text, classes=None):
    """Return a nodes.reference from `docname` to the tag page for
    `label`.
    """
    coll = blog.tags[label]
    base = posixpath.dirname(docname)
    target = posixpath.relpath(coll.docname, base) + ".html"
    return nodes.reference(
        text, text, refuri=target, internal=True, classes=classes or []
    )


def featured_inline(blog, post, docname):
    tags = [str(t) for t in post.get("tags") or []]
    if "featured" not in tags:
        return None
    # Reference must live inside a TextElement (sphinx html5 asserts
    # this). Wrap in an inline like tags_inline does.
    container = nodes.inline()
    container += tag_ref(
        blog, docname, "featured", "Featured", ["post-meta-featured"]
    )
    return container


def author_inline(post):
    authors = post.get("author") or []
    if not authors:
        return None
    text = ", ".join(str(a) for a in authors)
    return nodes.inline(text, text, classes=["post-meta-author"])


def date_inline(post):
    date = post.get("date")
    if not date:
        return None
    text = date.strftime("%b %d, %Y")
    return nodes.inline(text, text, classes=["post-meta-date"])


def readtime_inline(doctree):
    text = f"{reading_minutes(doctree)} min read"
    return nodes.inline(text, text, classes=["post-meta-readtime"])


def tags_inline(blog, post, docname):
    tags = [t for t in post.get("tags") or [] if str(t) != "featured"]
    if not tags:
        return None
    container = nodes.inline(classes=["post-meta-tags"])
    for label in sorted(tags, key=str):
        container += tag_ref(blog, docname, label, str(blog.tags[label]))
    return container


def find_title_position(doctree):
    """Return (section, title_index) for the first section with a
    title, or (None, None) if none exists.
    """
    section = next(iter(doctree.findall(nodes.section)), None)
    if section is None:
        return None, None
    idx = next(
        (
            i
            for i, c in enumerate(section.children)
            if isinstance(c, nodes.title)
        ),
        None,
    )
    return (section, idx) if idx is not None else (None, None)


class post_banner(nodes.container, nodes.Invisible):
    """Container subclass marked as docutils Invisible. The HTML
    writer still renders it as a <div> (via the visit/depart
    functions registered below), but sphinxext-opengraph's
    description parser skips isinstance(node, nodes.Invisible)
    nodes, so the banner text does not leak into og:description.
    """


def visit_post_banner(self, node):
    self.visit_container(node)


def depart_post_banner(self, node):
    self.depart_container(node)


def insert_banner(app, doctree, docname):
    posts = getattr(app.env, "ablog_posts", {}).get(docname)
    if not posts:
        return
    post = posts[0]

    section, title_idx = find_title_position(doctree)
    if section is None:
        return

    blog = Blog(app)
    banner = post_banner(classes=["post-meta-banner"])
    for child in (
        featured_inline(blog, post, docname),
        author_inline(post),
        date_inline(post),
        readtime_inline(doctree),
        tags_inline(blog, post, docname),
    ):
        if child is not None:
            banner += child

    section.insert(title_idx + 1, banner)


def setup(app):
    app.add_node(post_banner, html=(visit_post_banner, depart_post_banner))
    app.connect("doctree-resolved", insert_banner)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
