#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Module needed so that certain scripts in this directory can freely
import psutil/_common.py without installing psutil first, and/or to
avoid circular import errors deriving from "psutil._common import …".
"""

import importlib
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def _import_module_by_path(path):
    name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_common = _import_module_by_path(ROOT / "psutil/_common.py")

bytes2human = _common.bytes2human
print_color = _common.print_color
