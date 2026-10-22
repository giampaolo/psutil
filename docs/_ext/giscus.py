# Copyright (c) 2009, Giampaolo Rodola. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Feed the giscus config and a per-page "is this a blog post" flag to
the HTML templates, so _templates/comments.html can render the comment
widget on post pages only.
"""

CONFIG_VALUES = (
    "giscus_repo",
    "giscus_repo_id",
    "giscus_category",
    "giscus_category_id",
)


def add_giscus_context(app, pagename, templatename, context, doctree):
    is_post = pagename in getattr(app.env, "ablog_posts", {})
    # A bare ":no_comments:" field at the top of a post opts it out.
    meta = app.env.metadata.get(pagename, {})
    context["is_blog_post"] = is_post and "no_comments" not in meta
    for name in CONFIG_VALUES:
        context[name] = getattr(app.config, name)


def setup(app):
    for name in CONFIG_VALUES:
        app.add_config_value(name, "", "html")
    app.connect("html-page-context", add_giscus_context)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
