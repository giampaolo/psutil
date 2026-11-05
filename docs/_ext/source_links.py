# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Sphinx extension pointing the "[source]" links of the API docs to
GitHub, at the line where each function or class is defined.
"""

import pathlib
import subprocess

from sphinx.pycode import ModuleAnalyzer

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
URL = "https://github.com/giampaolo/psutil/blob/{sha}/{path}#L{lineno}"

GIT_SHA = subprocess.check_output(
    ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT_DIR, text=True
).strip()


# Line numbers come from the repo files, not from the installed
# psutil, which may be a different version.
def linkcode_resolve(domain, info):
    if domain != "py" or not info["module"]:
        return None
    path = ROOT_DIR.joinpath(*info["module"].split("."))
    path = path / "__init__.py" if path.is_dir() else path.with_suffix(".py")
    analyzer = ModuleAnalyzer.for_file(path, info["module"])
    tag = analyzer.find_tags().get(info["fullname"])
    if tag is None:  # defined in another module, or not a def / class
        return None
    _, lineno, _ = tag
    relpath = path.relative_to(ROOT_DIR).as_posix()
    return URL.format(sha=GIT_SHA, path=relpath, lineno=lineno)


def set_resolver(app, config):
    config.linkcode_resolve = linkcode_resolve


def setup(app):
    app.setup_extension("sphinx.ext.linkcode")
    app.connect("config-inited", set_resolver)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
