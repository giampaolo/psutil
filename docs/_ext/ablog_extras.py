# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Ablog tweaks."""


def merge_ablog_posts(app, env, docnames, other):
    if hasattr(other, "ablog_posts"):
        if not hasattr(env, "ablog_posts"):
            env.ablog_posts = {}
        env.ablog_posts.update(other.ablog_posts)


def setup(app):
    app.connect("env-merge-info", merge_ablog_posts)
    # Ablog stores posts on the build environment but doesn't merge
    # them back when Sphinx builds in parallel, so worker results get
    # dropped. See https://github.com/sunpy/ablog/pull/330.
    app.extensions["ablog"].parallel_read_safe = True
    return {"parallel_read_safe": True, "parallel_write_safe": True}
