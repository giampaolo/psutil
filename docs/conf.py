# Copyright (c) 2009, Giampaolo Rodola. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Sphinx configuration file.

Sphinx doc:
https://www.sphinx-doc.org/en/master/usage/configuration.html

RTD theme doc:
https://sphinx-rtd-theme.readthedocs.io/en/stable/
"""

import datetime
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_ROOT_DIR = _HERE.parent
sys.path.insert(0, str(_ROOT_DIR))
sys.path.insert(0, str(_HERE / '_ext'))

from _bootstrap import get_version  # noqa: E402

PROJECT_NAME = "psutil"
AUTHOR = "Giampaolo Rodola"
THIS_YEAR = str(datetime.datetime.now().year)
VERSION = get_version()

# =====================================================================
# Extensions
# =====================================================================

extensions = [
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    # custom extensions in _ext/ dir
    "availability",
    "changelog_anchors",
    "check_python_syntax",
    "field_role",
    "genindex_filter",
]

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
}

# =====================================================================
# Paths
# =====================================================================

html_static_path = ["_static"]
exclude_patterns = ["_build", "_globals.rst"]

# =====================================================================
# HTML
# =====================================================================

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
        "navigation_depth": 5,
        "flyout_display": "attached",
    }
    templates_path = ["_templates", "_static/images"]
    pygments_style = "tango"  # https://pygments.org/styles/
    html_css_files = [
        "css/custom.css",
    ]
    html_js_files = [
        "js/highlight-repl.js",
        "js/external-urls.js",
        ("js/theme-toggle.js", {"defer": "defer"}),
        ("js/sidebar-close.js", {"defer": "defer"}),
        ("js/search-shortcuts.js", {"defer": "defer"}),
    ]

# =====================================================================
# Prolog prepended to every .rst file
# =====================================================================

rst_prolog = (_HERE / "_globals.rst").read_text()
