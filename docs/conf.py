# Copyright (c) 2009, Giampaolo Rodola. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Sphinx configuration file.

Sphinx doc at:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

import datetime
import pathlib
import sys

PROJECT_NAME = "psutil"
AUTHOR = "Giampaolo Rodola"
THIS_YEAR = str(datetime.datetime.now().year)

_HERE = pathlib.Path(__file__).resolve().parent
_ROOT_DIR = _HERE.parent
sys.path.insert(0, str(_ROOT_DIR))
from _bootstrap import get_version  # noqa: E402

VERSION = get_version()

# =====================================================================
# Extensions
# =====================================================================

sys.path.insert(0, str(_HERE / '_ext'))

extensions = [
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    # custom extensions in _ext/ dir
    "availability",
    "add_home_link",
    "changelog_anchors",
    "check_python_syntax",
    "field_role",
]

# =====================================================================
# Project metadata
# =====================================================================

project = PROJECT_NAME
author = AUTHOR
version = VERSION
release = VERSION
copyright = f"2009-{THIS_YEAR}, {AUTHOR}"  # shown in the footer

# =====================================================================
# Cross-references and external links
# =====================================================================

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}
extlinks = {
    'gh': ('https://github.com/giampaolo/psutil/issues/%s', '#%s'),
}

# =====================================================================
# Paths
# =====================================================================

templates_path = ['_templates']
html_static_path = ['_static']
exclude_patterns = ['_build']
html_css_files = [
    'css/custom.css',
]
html_js_files = [
    "js/highlight-repl.js",
    "js/external-urls.js",
    ("js/theme-toggle.js", {"defer": "defer"}),
]

# =====================================================================
# HTML / theming
# =====================================================================

html_title = "psutil"
html_logo = "_static/images/logo-psutil.svg"
html_favicon = "_static/images/favicon.svg"
html_theme = 'sphinx_rtd_theme'
pygments_style = "monokai"  # https://pygments.org/styles/
html_last_updated_fmt = "%b %d, %Y"  # shown in the footer

# =====================================================================
# Plugins
# =====================================================================

htmlhelp_basename = f"{PROJECT_NAME}-doc"
copybutton_exclude = '.linenos, .gp'
