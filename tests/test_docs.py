# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for documentation files."""

import pathlib

from psutil._common import cat

from . import ROOT_DIR
from . import PsutilTestCase
from . import process_namespace
from . import system_namespace

RST_PATH = pathlib.Path(ROOT_DIR) / "docs" / "shell_equivalents.rst"


class TestShellEquivalents(PsutilTestCase):
    """Check that all psutil APIs are mentioned in
    docs/shell_equivalents.rst.
    """

    excluded_sys = set()
    excluded_proc = set()

    def test_system_functions(self):
        content = cat(RST_PATH)
        ignored = {name for name, _, _ in system_namespace.ignored}
        seen = set()
        for name, _, _ in system_namespace.getters:
            if name in ignored or name in seen or name in self.excluded_sys:
                continue
            seen.add(name)
            with self.subTest(name=name):
                assert f":func:`{name}" in content

    def test_process_methods(self):
        content = cat(RST_PATH)
        ignored = {name for name, _, _ in process_namespace.ignored}
        seen = set()
        all_methods = process_namespace.getters + process_namespace.utils
        for name, _, _ in all_methods:
            if name in ignored or name in seen or name in self.excluded_proc:
                continue
            with self.subTest(name=name):
                assert f":meth:`Process.{name}" in content
