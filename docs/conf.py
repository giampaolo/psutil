# Copyright (c) 2009, Giampaolo Rodola. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Sphinx config file."""

# See doc at:
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

import datetime
import pathlib
import sys

PROJECT_NAME = "psutil"
AUTHOR = "Giampaolo Rodola"
THIS_YEAR = str(datetime.datetime.now().year)
HERE = pathlib.Path(__file__).resolve().parent
ROOT_DIR = HERE.parent

sys.path.insert(0, str(ROOT_DIR))
from _bootstrap import get_version  # noqa: E402

VERSION = get_version()


sys.path.insert(0, str(HERE / '_ext'))

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
]

project = PROJECT_NAME
copyright = f"2009-{THIS_YEAR}, {AUTHOR}"
author = AUTHOR
version = VERSION
release = VERSION
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}
extlinks = {
    'gh': ('https://github.com/giampaolo/psutil/issues/%s', '#%s'),
}
templates_path = ['_templates']
html_static_path = ['_static']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
html_theme = 'sphinx_rtd_theme'
htmlhelp_basename = f"{PROJECT_NAME}-doc"
copybutton_exclude = '.linenos, .gp'
html_css_files = [
    'https://media.readthedocs.org/css/sphinx_rtd_theme.css',
    'https://media.readthedocs.org/css/readthedocs-doc-embed.css',
    'css/custom.css',
]

# https://pygments.org/styles/
pygments_style = "monokai"
