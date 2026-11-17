# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for anti_slop.py script."""

import importlib.util
import pathlib
from unittest import mock

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


class TestPRFarm:
    def test_check(self):
        rule = bot.PRFarm()
        pr = make_pr("bob", "2026-11-01T10:05:00Z")
        rule.account = lambda *_: (10, 60, 69)
        assert rule.check(pr)
        rule.account = lambda *_: (10, 59, 69)
        assert not rule.check(pr)
        rule.account = lambda *_: (10, 100, 70)
        assert not rule.check(pr)
        rule.account = lambda *_: (10, 100, None)
        assert not rule.check(pr)
        rule.account = lambda *_: (299, 100, 0)
        assert rule.check(pr)
        rule.account = lambda *_: (300, 100, 0)
        assert not rule.check(pr)

    def test_account_ratio(self):
        def user(merged, closed):
            return {
                "user": {
                    "followers": {"totalCount": 5},
                    "merged": {"totalCount": merged},
                    "closed": {"totalCount": closed},
                    "contributionsCollection": {
                        "totalRepositoriesWithContributedPullRequests": 80
                    },
                }
            }

        pr = make_pr("bob", "2026-11-01T10:05:00Z")
        with mock.patch.object(bot.ghlib, "graphql") as graphql:
            graphql.return_value = user(423, 188)
            assert bot.PRFarm().account(pr) == (5, 80, 69)
            graphql.return_value = user(0, 0)
            assert bot.PRFarm().account(pr) == (5, 80, None)
