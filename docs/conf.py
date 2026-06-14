# Copyright (c) 2009, Giampaolo Rodola. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Sphinx configuration file.

Sphinx doc:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

import datetime
import importlib.util
import locale
import os
import pathlib
import sys
import time

_HERE = pathlib.Path(__file__).resolve().parent
_ROOT_DIR = _HERE.parent
sys.path.insert(0, str(_HERE / "_ext"))  # needed to load local extensions


# Load _bootstrap.py (at the repo root) without putting the repo
# root on sys.path. Doing so would expose the uncompiled source
# `psutil/` package and shadow any installed psutil, breaking
# `import psutil` at build time (needed by sphinx-codeautolink to
# resolve things like `p.name()` in code blocks).
def _load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


get_version = _load(_ROOT_DIR / "_bootstrap.py").get_version

PROJECT_NAME = "psutil"
AUTHOR = "Giampaolo Rodola"
THIS_YEAR = str(datetime.datetime.now().year)
VERSION = get_version()

# =====================================================================
# Core
# =====================================================================

needs_sphinx = "9.1"
language = "en"
nitpicky = True  # always warn on unresolved cross-references

# =====================================================================
# Extensions
# =====================================================================

_third_party_exts = [
    "ablog",
    "notfound.extension",  # custom 404 page
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_codeautolink",
    "sphinx_copybutton",
    "sphinx_design",  # tabbed code examples on the home page
    "sphinx_sitemap",
    "sphinxext.opengraph",
]

_local_exts = [  # defined in the _ext/ folder
    "availability",
    "changelog_anchors",
    "check_python_syntax",
    "field_role",
    "genindex_filter",
    "glossary_toc",
    "opengraph_override",
    "post_banner",
    "proc_role",
]

extensions = _third_party_exts + _local_exts

# =====================================================================
# Project metadata
# =====================================================================

project = PROJECT_NAME
author = AUTHOR
version = release = VERSION
copyright = f"2009-{THIS_YEAR}, {AUTHOR}"  # shown in the footer

# =====================================================================
# Cross-references and external links
# =====================================================================

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}
extlinks = {
    "gh": ("https://github.com/giampaolo/psutil/issues/%s", "#%s"),
    "pr": ("https://github.com/giampaolo/psutil/pull/%s", "PR-%s"),
    "user": ("https://github.com/%s", "@%s"),
    "commit": ("https://github.com/giampaolo/psutil/commit/%s", "%s"),
    "pypi": ("https://pypi.org/project/psutil/%s/", "%s"),
    "bpo": ("https://bugs.python.org/issue%s", "BPO-%s"),
    "cpy": ("https://github.com/python/cpython/issues/%s", "cpython/#%s"),
    "cpy-pr": ("https://github.com/python/cpython/pull/%s", "cpython/PR-%s"),
    "src": ("https://github.com/giampaolo/psutil/blob/master/%s", "%s"),
}
manpages_url = "https://manpages.debian.org/{path}"

# =====================================================================
# Paths
# =====================================================================

exclude_patterns = ["_build"]
rst_prolog = ".. currentmodule:: psutil\n"  # Prepended to every .rst file

# =====================================================================
# HTML
# =====================================================================

# Canonical site URL. Picked up by Sphinx for <link rel="canonical">
# tags. Reused below by sphinxext-opengraph (og:url), sphinx-sitemap,
# and (via blog_baseurl) ablog's atom feed.
#
#         -------- TODO / IMPORTANT -------
#
# At 8.0.0 release, change this to the final base URL
# (https://psutil.readthedocs.io/ or https://psutil.org/) and flip the
# RTD Single Version toggle at the same time.
html_baseurl = "https://psutil.readthedocs.io/latest/"

#         -------- TODO / IMPORTANT -------
#
# sphinx-notfound-page: absolute URL prefix for static files and
# nav links on 404.html. Will become "/" when we switch domain.
notfound_urls_prefix = "/latest/"

html_title = PROJECT_NAME
html_favicon = "_static/images/favicon.svg"
html_last_updated_fmt = "%Y-%m-%d"  # ISO date shown in the footer
html_show_sphinx = False  # removes "Created using Sphinx" in the footer
html_show_sourcelink = False  # removes "View page source" sidebar link

# Sidebar shows method() instead of Class.method()
toc_object_entries_show_parents = "hide"

# =====================================================================
# Plugins
# =====================================================================

copybutton_exclude = ".linenos, .gp"

# =====================================================================
# Theming
# =====================================================================

# Custom psutil-sphinx-theme, built on top of Sphinx's `basic` theme.

html_theme = "basic"
html_theme_options = {
    "globaltoc_maxdepth": 1,
    "globaltoc_collapse": False,
    "globaltoc_includehidden": True,
}
html_static_path = ["_static"]
templates_path = ["_templates"]
pygments_style = "tango"  # base palette (overridden by css/code.css)


def _css_files():
    css_dir = _HERE / "_static" / "css"
    files = sorted(p.name for p in css_dir.glob("*.css"))
    head = ["base.css", "fonts.css", "typography.css"]
    tail = ["home.css"]
    middle = [f for f in files if f not in head + tail]
    return [f"css/{name}" for name in head + middle + tail if name in files]


html_css_files = [
    # External: FontAwesome. (Web fonts are self-hosted in css/fonts.css.)
    (
        "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@7.2.0/css/all.min.css",
        {
            "integrity": (
                "sha384-EXatlQyrOJgDaM9/a74ArMzy7/2bTMSrZj8ID1IPeVmc3GncfCugefCFWSLj8JL/"
            ),
            "crossorigin": "anonymous",
        },
    ),
    *_css_files(),
]


def _js_files():
    js_dir = _HERE / "_static" / "js"
    files = sorted(p.name for p in js_dir.glob("*.js"))
    return [(f"js/{name}", {"defer": "defer"}) for name in files]


html_js_files = _js_files()

# =====================================================================
# Blog (ablog package)
# =====================================================================

# Force UTC for build-time timestamps so atom feed entries are
# the same across build hosts (RTD runs UTC; local devs may not).
os.environ["TZ"] = "UTC"
if hasattr(time, "tzset"):
    time.tzset()

# Fix for ablog which shows local dates locally (not on RTD)
try:
    locale.setlocale(locale.LC_TIME, "C")
except locale.Error:
    pass

# Drives atom feed entry <id>s and <link>s. Same value as html_baseurl
# so feed URLs track canonicals URLs.
blog_baseurl = html_baseurl

# =====================================================================
# sphinxext-opengraph
# =====================================================================

# sphinxext-opengraph emits <meta property="og:*"> + Twitter Card tags
# in every page's <head>, so that URLs shared on social medias render
# as rich preview cards instead of bare links.
ogp_site_url = html_baseurl
ogp_site_name = PROJECT_NAME
ogp_description_length = 160  # Google SERP snippet width

# The logo shown in the preview. sphinxext-opengraph requires a .png
# file.
_logo = "_static/images/logo-psutil.png"
ogp_social_cards = {"image": _logo, "image_mini": _logo}

# =====================================================================
# sphinx-sitemap
# =====================================================================

# sphinx-sitemap emits <build>/sitemap.xml listing every built page,
# for search engine discovery. Reads html_baseurl; {link} scheme avoids
# the default {lang}{version} prefix (we don't use either in URLs).
sitemap_url_scheme = "{link}"
sitemap_show_lastmod = True
sitemap_excludes = [
    "search.html",
    "genindex.html",
    "py-modindex.html",
    "404.html",
    "_modules/*",
    "blog/archive.html",
    "blog/drafts.html",
    "blog/tag.html",
    "blog/tag/*",
    "blog/category.html",
    "blog/category/*",
    "blog/author.html",
    "blog/author/*",
]
# Suppress sphinx-sitemap warning (turned into error by
# --fail-on-warning) occurring on CI.
suppress_warnings = ["git.too_shallow"]

# =====================================================================
# sphinx-codeautolink
# =====================================================================

# Treat all code blocks on the same page as one interpreter session: a
# variable defined in block 1 stays known in block 2. Without this,
# snippets like `>>> p = psutil.Process()` followed by `>>> p.name()`
# in a later block lose the type of `p`.
codeautolink_concat_default = True

# Seed every block with an implicit `import psutil`, so snippets that
# start mid-session (no explicit import line) still have `psutil.X`
# references resolvable.
codeautolink_global_preface = "import psutil"

# Print warnings for names it can't resolve.
# codeautolink_warn_on_failed_resolve = True

# =====================================================================
# Sphinx setup hook
# =====================================================================


def setup(app):
    # sphinx-codeautolink needs `import psutil` to resolve things like
    # `p.name()` in code blocks. It imports psutil itself internally,
    # but silently passes if it can't, so we do it here to crash
    # explicitly. Kept inside setup() (not at module scope) so pytest
    # collection of docs/test_docs.py doesn't hit it.
    import psutil  # noqa: F401

    # Monkey patch ablog to support parallel builds:
    # https://github.com/sunpy/ablog/pull/330.
    def merge_ablog_posts(app, env, docnames, other):
        if hasattr(other, "ablog_posts"):
            if not hasattr(env, "ablog_posts"):
                env.ablog_posts = {}
            env.ablog_posts.update(other.ablog_posts)

    app.connect("env-merge-info", merge_ablog_posts)
    app.extensions["ablog"].parallel_read_safe = True
