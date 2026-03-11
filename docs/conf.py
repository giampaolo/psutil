# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Sphinx config file."""

# See doc at:
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

import ast
import datetime
import os
import sys

PROJECT_NAME = "psutil"
AUTHOR = "Giampaolo Rodola"
THIS_YEAR = str(datetime.datetime.now().year)
HERE = os.path.abspath(os.path.dirname(__file__))


def get_version():
    INIT = os.path.abspath(os.path.join(HERE, '../psutil/__init__.py'))
    with open(INIT) as f:
        for line in f:
            if line.startswith('__version__'):
                ret = ast.literal_eval(line.strip().split(' = ')[1])
                assert ret.count('.') == 2, ret
                for num in ret.split('.'):
                    assert num.isdigit(), ret
                return ret
        msg = "couldn't find version string"
        raise ValueError(msg)


VERSION = get_version()


sys.path.insert(0, os.path.join(HERE, '_ext'))

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx.ext.extlinks",
    "sphinx.ext.imgmath",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
    # our own custom extensions in _ext/ dir
    "add_home_link",
    "changelog_anchors",
    "check_python_syntax",
]

# project info
project = PROJECT_NAME
copyright = f"2009-{THIS_YEAR}, {AUTHOR}"
author = AUTHOR
version = VERSION
release = VERSION

extlinks = {
    'gh': ('https://github.com/giampaolo/psutil/issues/%s', '#%s'),
}

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

language = "eng"
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
pygments_style = 'sphinx'

todo_include_todos = False

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
htmlhelp_basename = f"{PROJECT_NAME}-doc"

latex_documents = [
    (master_doc, 'psutil.tex', 'psutil Documentation', AUTHOR, 'manual')
]

html_css_files = [
    'https://media.readthedocs.org/css/sphinx_rtd_theme.css',
    'https://media.readthedocs.org/css/readthedocs-doc-embed.css',
    'css/custom.css',
]
