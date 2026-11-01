# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for anti_slop.py script."""

import importlib.util
import pathlib

BOT_PATH = pathlib.Path(__file__).parent.parent / "anti_slop.py"
ISSUE = {
    "number": 1,
    "user": {"login": "alice"},
    "created_at": "2026-11-01T10:00:00Z",
}


def import_module_by_path(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bot = import_module_by_path(BOT_PATH)


def make_rule():
    rule = bot.IssueHunters()
    rule.maintainer_replied = lambda *_: False
    return rule


def make_pr(login, created_at):
    return {"user": {"login": login}, "created_at": created_at}


class TestIsSniped:
    def test_same_author(self):
        pr = make_pr("alice", "2026-11-01T10:05:00Z")
        assert not make_rule().is_sniped(pr, ISSUE)

    def test_other_author(self):
        rule = make_rule()
        pr = make_pr("bob", "2026-11-01T10:05:00Z")
        assert rule.is_sniped(pr, ISSUE)
        pr = make_pr("bob", "2026-11-02T10:05:00Z")
        assert not rule.is_sniped(pr, ISSUE)
