# Copyright (c) 2009, Giampaolo Rodola. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Sphinx configuration file.

Sphinx doc:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

import datetime
import importlib.util
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_ROOT_DIR = _HERE.parent
sys.path.insert(0, str(_HERE / '_ext'))  # needed to load local extensions


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
# Extensions
# =====================================================================

_third_party_exts = [
    "ablog",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_codeautolink",
    "sphinx_copybutton",
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
    "post_banner",
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
}

# =====================================================================
# Paths
# =====================================================================

html_static_path = ["_static"]
exclude_patterns = ["_build", "_globals.rst"]
rst_prolog = (_HERE / "_globals.rst").read_text()

# =====================================================================
# HTML
# =====================================================================

# Canonical site URL. Picked up by Sphinx for <link rel="canonical">
# tags. Reused below by ablog (Atom feed), sphinxext-opengraph
# (og:url), and sphinx-sitemap.
# - TODO: revisit once the psutil.org domain is live. Changing this
#   later may cause feed readers to redeliver all posts as "new". See
#   also RTD's READTHEDOCS_CANONICAL_URL env var.
html_baseurl = "https://psutil.readthedocs.io/"

html_title = PROJECT_NAME
html_favicon = "_static/images/favicon.svg"
html_last_updated_fmt = "%Y-%m-%d"  # ISO date shown in the footer

# Sidebar shows method() instead of Class.method()
toc_object_entries_show_parents = "hide"

# =====================================================================
# Plugins
# =====================================================================

copybutton_exclude = ".linenos, .gp"

# =====================================================================
# Theming
# =====================================================================

html_theme = "sphinx_rtd_theme"

if html_theme == "sphinx_rtd_theme":
    html_theme_options = {
        "collapse_navigation": False,
        "navigation_depth": 1,
        "titles_only": True,
        "flyout_display": "attached",
    }
    templates_path = ["_templates", "_static/images"]
    pygments_style = "tango"  # https://pygments.org/styles/
    html_css_files = [
        "css/custom.css",
        "css/code.css",
        "css/home.css",
        "css/blog.css",
        "css/right-toc.css",
    ]
    html_js_files = [
        "js/highlight-repl.js",
        "js/external-urls.js",
        ("js/theme-toggle.js", {"defer": "defer"}),
        ("js/sidebar-close.js", {"defer": "defer"}),
        ("js/search-shortcuts.js", {"defer": "defer"}),
        ("js/right-toc.js", {"defer": "defer"}),
    ]

# =====================================================================
# Blog (ablog package)
# =====================================================================

# ablog-specific alias of html_baseurl; used in Atom feed entry
# <link> and <id>.
blog_baseurl = html_baseurl

# =====================================================================
# sphinxext-opengraph
# =====================================================================

# sphinxext-opengraph emits <meta property="og:*"> + Twitter Card tags
# in every page's <head>, so that URLs shared on social medias render
# as rich preview cards instead of bare links.
ogp_site_url = html_baseurl
ogp_site_name = PROJECT_NAME
ogp_description_length = 200

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
