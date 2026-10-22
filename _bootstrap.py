# Copyright (c) 2009 Giampaolo Rodola. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Bootstrap utilities for loading psutil modules without psutil
being installed.
"""

import ast
import importlib.util
import os
import pathlib

ROOT_DIR = pathlib.Path(__file__).resolve().parent


def load_module(path):
    """Load a Python module by file path without importing it
    as part of a package.
    """
    name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def get_version():
    """Extract __version__ from psutil/__init__.py using AST
    (no imports needed).
    """
    path = ROOT_DIR / "psutil" / "__init__.py"
    with open(path, encoding="utf-8") as f:
        mod = ast.parse(f.read())
    for node in mod.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if getattr(target, "id", None) == "__version__":
                    return ast.literal_eval(node.value)
    msg = "could not find __version__"
    raise RuntimeError(msg)
