# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for the triage bot (.github/workflows/triage_labels.py).

These cover the confidence gating, which is what keeps a shaky answer
from deleting a label someone applied by hand. No network or API is
used.
"""

import importlib.util
import pathlib

BOT_PATH = pathlib.Path(__file__).parent.parent / "triage_labels.py"


def import_module_by_path(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tl = import_module_by_path(BOT_PATH)


def decide(**kw):
    """A decision, confident and empty unless told otherwise.

    Pass e.g. platform=["linux"], platform_confidence="low".
    """
    out = {
        "type": "bug",
        "platform": [],
        "component": [],
        "severity": [],
    }
    out.update({f"{axis}_confidence": "high" for axis in tl.AXES})
    out.update(kw)
    return out


class TestFreshLabels:
    def test_low_confidence_axis_contributes_nothing(self):
        decision = decide(
            platform=["linux"],
            platform_confidence="low",
            component=["tests"],
        )
        assert tl.fresh_labels(decision) == {"bug", "tests"}

    def test_low_confidence_type_contributes_nothing(self):
        decision = decide(type="bug", type_confidence="low")
        assert tl.fresh_labels(decision) == set()


class TestStaleLabels:
    def test_removes_only_when_confident(self):
        item = {"labels": ["bug", "windows"]}
        decision = decide(platform=["linux"], platform_confidence="medium")
        assert tl.stale_labels(item, decision) == set()

        decision = decide(platform=["linux"], platform_confidence="high")
        assert tl.stale_labels(item, decision) == {"windows"}

    def test_severity_is_never_removed(self):
        # severity is add-only: the text can suggest critical but it
        # can never prove the absence of one.
        item = {"labels": ["bug", "critical", "memleak"]}
        decision = decide(severity=[], severity_confidence="high")
        assert tl.stale_labels(item, decision) == set()

    def test_confident_null_type_clears_bug(self):
        item = {"labels": ["bug", "linux"]}
        decision = decide(type=None, platform=["linux"])
        assert tl.stale_labels(item, decision) == {"bug"}


class TestDropGeneralPlatforms:
    def test_named_os_wins_over_the_general_one(self):
        decision = decide(platform=["unix", "linux"])
        assert tl.fresh_labels(decision) == {"bug", "linux"}

        decision = decide(platform=["bsd", "freebsd"])
        assert tl.fresh_labels(decision) == {"bug", "freebsd"}

    def test_general_one_stays_when_nothing_names_an_os(self):
        decision = decide(platform=["unix", "pypy"])
        assert tl.fresh_labels(decision) == {"bug", "unix", "pypy"}
