#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for the /changelog bot (.github/workflows/changelog_bot.py).

The bot edits docs/changelog.rst and docs/credits.rst based on an LLM
decision. These tests exercise the deterministic file surgery and the
validation gate against small RST fixtures; no network or API is used.
"""

import io
import pathlib

import pytest

from . import ROOT_DIR
from . import import_module_by_path

BOT_PATH = (
    pathlib.Path(ROOT_DIR) / ".github" / "workflows" / "changelog_bot.py"
)

cb = import_module_by_path(BOT_PATH)

CHANGELOG = """\
Changelog
=========

8.0.0 (IN DEVELOPMENT)
^^^^^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`100`: enhancement one.

**Bug fixes**

- :gh:`200`: bug one.
- :gh:`201`, [Linux]: bug two spanning
  two physical lines.

7.2.2 — 2026-01-28
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`50`: old released bug.
"""


class TestContext:
    def test_returns_only_top_block(self):
        block = cb.changelog_context(CHANGELOG)
        assert block.startswith("8.0.0 (IN DEVELOPMENT)")
        assert ":gh:`200`" in block
        # The released block below must not be included.
        assert "7.2.2" not in block
        assert ":gh:`50`" not in block


class TestInsert:
    def _lines(self, text):
        return text.splitlines()

    def test_appends_to_end_of_section(self):
        out = cb.insert_entry(CHANGELOG, "Bug fixes", "- :gh:`300`: new bug.")
        lines = self._lines(out)
        idx = lines.index("- :gh:`300`: new bug.")
        # It lands after the existing bug entries.
        assert lines.index("- :gh:`200`: bug one.") < idx

    def test_does_not_glue_to_next_header(self):
        # The regression: a new entry must not abut the next version
        # header with no blank line in between.
        out = cb.insert_entry(CHANGELOG, "Bug fixes", "- :gh:`300`: new bug.")
        lines = self._lines(out)
        idx = lines.index("- :gh:`300`: new bug.")
        assert lines[idx + 1] == ""
        assert lines[idx + 2].startswith("7.2.2")

    def test_inserts_into_correct_section(self):
        out = cb.insert_entry(
            CHANGELOG, "Enhancements", "- :gh:`300`: new enh."
        )
        lines = self._lines(out)
        enh = lines.index("**Enhancements**")
        bug = lines.index("**Bug fixes**")
        idx = lines.index("- :gh:`300`: new enh.")
        assert enh < idx < bug

    def test_inserts_in_sorted_position(self):
        # 150 < 200, so it must come before it (#123 before #124).
        out = cb.insert_entry(CHANGELOG, "Bug fixes", "- :gh:`150`: early.")
        lines = self._lines(out)
        assert lines.index("- :gh:`150`: early.") < lines.index(
            "- :gh:`200`: bug one."
        )

    def test_inserts_into_last_run_of_grouped_section(self):
        # An Enhancements section split into pseudo-header groups: a new
        # entry goes into the last run, sorted, never into an earlier
        # group even if its number would sort there.
        text = """\
8.0.0 (IN DEVELOPMENT)
^^^^^^^^^^^^^^^^^^^^^^

**Enhancements**

New APIs:

- :gh:`100`: api one.
- :gh:`300`: api three.

Others:

- :gh:`200`: other two.
- :gh:`400`: other four.
"""
        out = cb.insert_entry(text, "Enhancements", "- :gh:`250`: new misc.")
        lines = self._lines(out)
        new = lines.index("- :gh:`250`: new misc.")
        # In the Others run (after that header), not New APIs.
        assert lines.index("Others:") < new
        assert lines.index("- :gh:`200`: other two.") < new
        assert new < lines.index("- :gh:`400`: other four.")

    def test_multiline_entry_kept_together(self):
        entry = "- :gh:`300`: a long entry that wraps onto\n  a second line."
        out = cb.insert_entry(CHANGELOG, "Bug fixes", entry)
        lines = self._lines(out)
        idx = lines.index("- :gh:`300`: a long entry that wraps onto")
        assert lines[idx + 1] == "  a second line."
        assert lines[idx + 2] == ""

    def test_creates_missing_section_after_enhancements(self):
        text = """\
8.0.0 (IN DEVELOPMENT)
^^^^^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`100`: enh.
"""
        out = cb.insert_entry(text, "Bug fixes", "- :gh:`300`: new bug.")
        lines = self._lines(out)
        assert lines.index("**Enhancements**") < lines.index("**Bug fixes**")
        assert lines.index("**Bug fixes**") < lines.index(
            "- :gh:`300`: new bug."
        )

    def test_created_section_has_blank_line_before_first_entry(self):
        # Regression: a freshly created section must not glue its first
        # entry to the header (renders as run-on prose, silently).
        text = """\
8.0.0 (IN DEVELOPMENT)
^^^^^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`100`: enh.
"""
        out = cb.insert_entry(text, "Bug fixes", "- :gh:`300`: new bug.")
        lines = self._lines(out)
        hdr = lines.index("**Bug fixes**")
        assert lines[hdr + 1] == ""
        assert lines[hdr + 2] == "- :gh:`300`: new bug."

    def test_created_enhancements_has_blank_line_before_entry(self):
        text = """\
8.0.0 (IN DEVELOPMENT)
^^^^^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`200`: bug.
"""
        out = cb.insert_entry(text, "Enhancements", "- :gh:`300`: new enh.")
        lines = self._lines(out)
        hdr = lines.index("**Enhancements**")
        assert lines[hdr + 1] == ""
        assert lines[hdr + 2] == "- :gh:`300`: new enh."

    def test_creates_missing_enhancements_before_bug_fixes(self):
        text = """\
8.0.0 (IN DEVELOPMENT)
^^^^^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`200`: bug.
"""
        out = cb.insert_entry(text, "Enhancements", "- :gh:`300`: new enh.")
        lines = self._lines(out)
        assert lines.index("**Enhancements**") < lines.index("**Bug fixes**")


class TestOrderCheck:
    ORDERED = """\
8.0.0 (IN DEVELOPMENT)
^^^^^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`100`: a.
- :gh:`200`: b.
"""

    def test_passes_for_sorted_run(self):
        cb.check_entry_ordered(self.ORDERED, 200)

    def test_raises_when_placed_after_higher_number(self):
        text = self.ORDERED.replace("- :gh:`100`", "- :gh:`300`")
        with pytest.raises(cb.ValidationError):
            cb.check_entry_ordered(text, 200)

    def test_stops_at_group_boundary(self):
        # A pseudo-header ends the run, so a higher number in an earlier
        # group doesn't count as "before" this entry.
        text = """\
8.0.0 (IN DEVELOPMENT)
^^^^^^^^^^^^^^^^^^^^^^

**Enhancements**

New APIs:

- :gh:`300`: api.

Others:

- :gh:`200`: other.
"""
        cb.check_entry_ordered(text, 200)


class TestAmend:
    def _lines(self, text):
        return text.splitlines()

    def test_replaces_single_line_entry(self):
        out = cb.amend_entry(
            CHANGELOG, 200, "- :gh:`200`: bug one, now amended."
        )
        lines = self._lines(out)
        assert "- :gh:`200`: bug one, now amended." in lines
        assert "- :gh:`200`: bug one." not in lines
        # Siblings untouched.
        assert "- :gh:`201`, [Linux]: bug two spanning" in lines

    def test_replaces_multiline_entry_span(self):
        out = cb.amend_entry(CHANGELOG, 201, "- :gh:`201`: collapsed.")
        lines = self._lines(out)
        assert "- :gh:`201`: collapsed." in lines
        # Both old physical lines of the 201 entry are gone.
        assert "- :gh:`201`, [Linux]: bug two spanning" not in lines
        assert "  two physical lines." not in lines

    def test_raises_when_entry_absent(self):
        with pytest.raises(cb.ValidationError):
            cb.amend_entry(CHANGELOG, 999, "- :gh:`999`: nope.")

    def test_does_not_match_released_block_entry(self):
        # :gh:`50` only exists in the released 7.2.2 block.
        with pytest.raises(cb.ValidationError):
            cb.amend_entry(CHANGELOG, 50, "- :gh:`50`: nope.")


CREDITS = """\
Code contributors
=================

Code contributors by year
-------------------------

2026
~~~~

* `Amaan Qureshi`_ - :gh:`2770`
* :user:`Gabriel Changamire <gabrielchangamire-arch>` - :gh:`2809`
* :user:`Tobias Klauser <tklauser>` - :gh:`2711`

2025
~~~~

* `Ben Peddell`_ - :gh:`2495`, :gh:`2568`
"""


class TestCreditLine:
    def test_full_name_form(self):
        line = cb.credit_line("hansonw", "Hanson Wang", 2809)
        assert line == "* :user:`Hanson Wang <hansonw>` - :gh:`2809`"

    def test_handle_only_form(self):
        # author_name falls back to the handle when no full name is set.
        line = cb.credit_line("someuser", "someuser", 2710)
        assert line == "* :user:`someuser` - :gh:`2710`"


class TestCredits:
    def _lines(self, text):
        return text.splitlines()

    def test_adds_new_contributor_sorted(self):
        out, status = cb.apply_credit(
            CREDITS, "newuser", "New User", 300, "2026"
        )
        assert status == "added"
        lines = self._lines(out)
        gab = lines.index(
            "* :user:`Gabriel Changamire <gabrielchangamire-arch>`"
            " - :gh:`2809`"
        )
        new = lines.index("* :user:`New User <newuser>` - :gh:`300`")
        tob = lines.index("* :user:`Tobias Klauser <tklauser>` - :gh:`2711`")
        assert gab < new < tob

    def test_appends_gh_to_existing_contributor(self):
        out, status = cb.apply_credit(
            CREDITS, "tklauser", "Tobias Klauser", 300, "2026"
        )
        assert status == "appended"
        assert (
            "* :user:`Tobias Klauser <tklauser>` - :gh:`2711`, :gh:`300`"
            in self._lines(out)
        )

    def test_sorts_before_legacy_named_link(self):
        out, status = cb.apply_credit(
            CREDITS, "aardvark", "Aardvark Zero", 300, "2026"
        )
        assert status == "added"
        lines = self._lines(out)
        new = lines.index("* :user:`Aardvark Zero <aardvark>` - :gh:`300`")
        amaan = lines.index("* `Amaan Qureshi`_ - :gh:`2770`")
        assert new < amaan

    LEGACY = """\
Code contributors
=================

Code contributors by year
-------------------------

2026
~~~~

* `Amaan Qureshi`_ - :gh:`2770`
* :user:`Tobias Klauser <tklauser>` - :gh:`2711`

.. _`Amaan Qureshi`: https://github.com/amaanq
"""

    def test_repeat_legacy_contributor_appends_not_duplicates(self):
        # Amaan is listed in the legacy `Name`_ style; his handle is in
        # the link target. A second 2026 PR must append, not add a
        # duplicate :user: line.
        out, status = cb.apply_credit(
            self.LEGACY, "amaanq", "Amaan Qureshi", 300, "2026"
        )
        assert status == "appended"
        lines = self._lines(out)
        assert "* `Amaan Qureshi`_ - :gh:`2770`, :gh:`300`" in lines
        assert not any(ln.startswith("* :user:`Amaan") for ln in lines)

    def test_giampaolo_is_skipped(self):
        out, status = cb.apply_credit(
            CREDITS, "giampaolo", "Giampaolo Rodola", 300, "2026"
        )
        assert status == "skipped"
        assert out == CREDITS

    def test_duplicate_gh_is_skipped(self):
        out, status = cb.apply_credit(
            CREDITS,
            "gabrielchangamire-arch",
            "Gabriel Changamire",
            2809,
            "2026",
        )
        assert status == "skipped"
        assert out == CREDITS

    WRAPPED = """\
Code contributors
=================

Code contributors by year
-------------------------

2026
~~~~

* :user:`Long Name Person <longname>` - :gh:`2001`, :gh:`2002`, :gh:`2003`,
  :gh:`2004`, :gh:`2005`
* :user:`Short <short>` - :gh:`10`
"""

    def test_append_to_wrapped_entry_hits_last_line(self):
        out, status = cb.apply_credit(
            self.WRAPPED, "longname", "Long Name Person", 2006, "2026"
        )
        assert status == "appended"
        lines = self._lines(out)
        # First physical line is untouched (no double comma).
        first = lines.index(
            "* :user:`Long Name Person <longname>` - :gh:`2001`,"
            " :gh:`2002`, :gh:`2003`,"
        )
        assert ",," not in out
        # The new ref lands on the continuation, not the first line.
        assert ":gh:`2006`" in out
        assert ":gh:`2006`" not in lines[first]

    def test_append_dup_check_spans_wrapped_entry(self):
        # :gh:`2005` is on the continuation line; must still skip.
        out, status = cb.apply_credit(
            self.WRAPPED, "longname", "Long Name Person", 2005, "2026"
        )
        assert status == "skipped"
        assert out == self.WRAPPED

    def test_append_stays_within_79_cols(self):
        out, _ = cb.apply_credit(
            self.WRAPPED, "longname", "Long Name Person", 2006, "2026"
        )
        assert all(len(ln) <= 79 for ln in self._lines(out))

    def test_creates_new_year_block(self):
        out, status = cb.apply_credit(
            CREDITS, "newuser", "New User", 1, "2027"
        )
        assert status == "added"
        lines = self._lines(out)
        assert "2027" in lines
        y2027 = lines.index("2027")
        y2026 = lines.index("2026")
        # Newest year on top.
        assert y2027 < y2026
        assert lines[y2027 + 1] == "~~~~"


class TestResortCredits:
    def test_sorts_year_block(self):
        text = """\
Code contributors by year
-------------------------

2026
~~~~

* :user:`Tobias Klauser <tklauser>` - :gh:`2711`
* `Amaan Qureshi`_ - :gh:`2770`
* :user:`Gabriel Changamire <gab>` - :gh:`2809`
"""
        out = cb.resort_credits_year(text, "2026")
        entries = [x for x in out.splitlines() if x.startswith("* ")]
        assert entries == [
            "* `Amaan Qureshi`_ - :gh:`2770`",
            "* :user:`Gabriel Changamire <gab>` - :gh:`2809`",
            "* :user:`Tobias Klauser <tklauser>` - :gh:`2711`",
        ]

    def test_keeps_multiline_entry_together(self):
        text = """\
Code contributors by year
-------------------------

2026
~~~~

* :user:`Zoe Last <zoe>` - :gh:`10`,
  :gh:`11`
* `Amaan Qureshi`_ - :gh:`2770`
"""
        out = cb.resort_credits_year(text, "2026")
        lines = out.splitlines()
        zoe = lines.index("* :user:`Zoe Last <zoe>` - :gh:`10`,")
        assert lines[zoe + 1] == "  :gh:`11`"
        assert lines.index("* `Amaan Qureshi`_ - :gh:`2770`") < zoe

    def test_leaves_other_years_untouched(self):
        text = """\
Code contributors by year
-------------------------

2026
~~~~

* :user:`Bea <bea>` - :gh:`2`
* :user:`Ann <ann>` - :gh:`1`

2025
~~~~

* :user:`Zed <zed>` - :gh:`9`
* :user:`Amy <amy>` - :gh:`8`
"""
        out = cb.resort_credits_year(text, "2026")
        lines = out.splitlines()
        # 2026 got sorted, 2025 kept as-is.
        assert lines.index("* :user:`Ann <ann>` - :gh:`1`") < lines.index(
            "* :user:`Bea <bea>` - :gh:`2`"
        )
        assert lines.index("* :user:`Zed <zed>` - :gh:`9`") < lines.index(
            "* :user:`Amy <amy>` - :gh:`8`"
        )


class TestReferencedIssues:
    def test_collects_refs_and_pr_number(self):
        refs = cb.referenced_issues(
            "Fix crash", "Closes #2809, see #100", 2810
        )
        assert refs == {2809, 100, 2810}

    def test_collects_url_and_gh_forms(self):
        body = (
            "Fixes https://github.com/giampaolo/psutil/issues/2809\n"
            "also GH-100 and giampaolo/psutil#42"
        )
        refs = cb.referenced_issues("t", body, 2810)
        assert {2809, 100, 42, 2810} <= refs


class TestApplyChangelogDecision:
    ALLOWED = {200, 201, 300}

    def test_insert_valid(self):
        decision = {
            "action": "insert",
            "section": "Bug fixes",
            "entry_text": "- :gh:`300`: new bug.",
            "amend_gh": None,
            "skip_reason": None,
        }
        out, status, gh = cb.apply_changelog_decision(
            CHANGELOG, decision, self.ALLOWED
        )
        assert status == "inserted"
        assert gh == 300
        assert "- :gh:`300`: new bug." in out

    def test_insert_rejects_issue_not_referenced(self):
        decision = {
            "action": "insert",
            "section": "Bug fixes",
            "entry_text": "- :gh:`777`: hallucinated.",
            "amend_gh": None,
            "skip_reason": None,
        }
        with pytest.raises(cb.ValidationError):
            cb.apply_changelog_decision(CHANGELOG, decision, self.ALLOWED)

    def test_insert_rejects_malformed_entry(self):
        decision = {
            "action": "insert",
            "section": "Bug fixes",
            "entry_text": "just some text without a gh ref",
            "amend_gh": None,
            "skip_reason": None,
        }
        with pytest.raises(cb.ValidationError):
            cb.apply_changelog_decision(CHANGELOG, decision, self.ALLOWED)

    def test_insert_rejects_when_issue_already_present(self):
        # :gh:`200` already has an entry; insert should have been amend.
        decision = {
            "action": "insert",
            "section": "Bug fixes",
            "entry_text": "- :gh:`200`: duplicate.",
            "amend_gh": None,
            "skip_reason": None,
        }
        with pytest.raises(cb.ValidationError):
            cb.apply_changelog_decision(CHANGELOG, decision, self.ALLOWED)

    def test_insert_rejects_entry_without_period(self):
        decision = {
            "action": "insert",
            "section": "Bug fixes",
            "entry_text": "- :gh:`300`: no period here",
            "amend_gh": None,
            "skip_reason": None,
        }
        with pytest.raises(cb.ValidationError):
            cb.apply_changelog_decision(CHANGELOG, decision, self.ALLOWED)

    def test_amend_valid(self):
        decision = {
            "action": "amend",
            "section": "Bug fixes",
            "entry_text": "- :gh:`200`: bug one and also two.",
            "amend_gh": 200,
            "skip_reason": None,
        }
        out, status, _ = cb.apply_changelog_decision(
            CHANGELOG, decision, self.ALLOWED
        )
        assert status == "amended"
        assert "- :gh:`200`: bug one and also two." in out

    def test_amend_allowed_when_issue_not_referenced_by_pr(self):
        # An amend targets an entry that already exists in the block;
        # the PR need not restate that issue number.
        decision = {
            "action": "amend",
            "section": None,
            "entry_text": "- :gh:`200`: bug one, extended.",
            "amend_gh": 200,
            "skip_reason": None,
        }
        out, status, _ = cb.apply_changelog_decision(
            CHANGELOG, decision, {12345}
        )
        assert status == "amended"
        assert "- :gh:`200`: bug one, extended." in out

    def test_amend_rejects_when_gh_changed(self):
        decision = {
            "action": "amend",
            "section": "Bug fixes",
            "entry_text": "- :gh:`999`: wrong number.",
            "amend_gh": 200,
            "skip_reason": None,
        }
        with pytest.raises(cb.ValidationError):
            cb.apply_changelog_decision(CHANGELOG, decision, self.ALLOWED)

    def test_skip_leaves_text_unchanged(self):
        decision = {
            "action": "skip",
            "section": None,
            "entry_text": None,
            "amend_gh": None,
            "skip_reason": "already covered.",
        }
        out, status, gh = cb.apply_changelog_decision(
            CHANGELOG, decision, self.ALLOWED
        )
        assert status == "skipped"
        assert out == CHANGELOG
        assert gh is None


class TestBuildComment:
    def test_inserted(self):
        decision = {
            "action": "insert",
            "section": "Bug fixes",
            "entry_text": "- :gh:`300`: x.",
            "amend_gh": None,
            "skip_reason": None,
        }
        out = cb.build_comment("inserted", "added", decision, 300, "bob")
        assert "entry added under **Bug fixes**" in out
        assert "- :gh:`300`: x." in out
        assert "credited @bob for :gh:`300`" in out

    def test_amended(self):
        decision = {
            "action": "amend",
            "section": None,
            "entry_text": "- :gh:`200`: y.",
            "amend_gh": 200,
            "skip_reason": None,
        }
        out = cb.build_comment("amended", "appended", decision, 200, "bob")
        assert "entry for :gh:`200` amended" in out
        assert "appended :gh:`200` to @bob" in out

    def test_skipped_states_reason_and_no_false_claim(self):
        decision = {
            "action": "skip",
            "section": None,
            "entry_text": None,
            "amend_gh": None,
            "skip_reason": "already covered.",
        }
        out = cb.build_comment("skipped", "skipped", decision, None, "bob")
        assert "**not** modified (skipped): already covered." in out
        assert "entry added" not in out


class TestRunDecision:
    def _setup_files(self):
        import tempfile

        d = pathlib.Path(tempfile.mkdtemp())
        clp = d / "changelog.rst"
        crp = d / "credits.rst"
        clp.write_text(CHANGELOG)
        crp.write_text(CREDITS)
        cb.CHANGELOG_FILE = str(clp)
        cb.CREDITS_FILE = str(crp)
        return clp, crp

    def test_amend_flow_writes_both_files(self):
        # The incident scenario: an entry for the issue already exists,
        # the PR amends it and the contributor is credited.
        clp, _ = self._setup_files()
        pr = {
            "number": 2810,
            "title": "Fix #200",
            "body": "",
            "author": "tklauser",
            "author_name": "Tobias Klauser",
        }
        decision = {
            "action": "amend",
            "section": None,
            "entry_text": "- :gh:`200`: bug one, now also two.",
            "amend_gh": 200,
            "skip_reason": None,
        }
        cl_status, cr_status, gh = cb.run_decision(pr, decision, year="2026")
        assert cl_status == "amended"
        assert gh == 200
        assert "- :gh:`200`: bug one, now also two." in clp.read_text()
        # tklauser already credited in 2026 -> append.
        assert cr_status == "appended"

    def test_skip_flow_touches_nothing(self):
        clp, crp = self._setup_files()
        before_cl = clp.read_text()
        before_cr = crp.read_text()
        pr = {
            "number": 2810,
            "title": "t",
            "body": "",
            "author": "tklauser",
            "author_name": "Tobias Klauser",
        }
        decision = {
            "action": "skip",
            "section": None,
            "entry_text": None,
            "amend_gh": None,
            "skip_reason": "already covered.",
        }
        cl_status, cr_status, _ = cb.run_decision(pr, decision, year="2026")
        assert cl_status == "skipped"
        assert cr_status == "skipped"
        assert clp.read_text() == before_cl
        assert crp.read_text() == before_cr

    def test_noop_amend_reports_skip(self):
        # Amending an entry with byte-identical text changes nothing, so
        # the bot must report a skip, not a false "amended".
        clp, _ = self._setup_files()
        before = clp.read_text()
        pr = {
            "number": 2810,
            "title": "t",
            "body": "",
            "author": "tklauser",
            "author_name": "Tobias Klauser",
        }
        decision = {
            "action": "amend",
            "section": None,
            "entry_text": "- :gh:`200`: bug one.",
            "amend_gh": 200,
            "skip_reason": None,
        }
        cl_status, cr_status, gh = cb.run_decision(pr, decision, year="2026")
        assert cl_status == "skipped"
        assert cr_status == "skipped"
        assert gh is None
        assert clp.read_text() == before

    def test_validation_failure_writes_nothing(self):
        clp, _ = self._setup_files()
        before_cl = clp.read_text()
        pr = {
            "number": 2810,
            "title": "t",
            "body": "",
            "author": "bob",
            "author_name": "Bob",
        }
        # :gh:`777` is not referenced by the PR -> rejected.
        decision = {
            "action": "insert",
            "section": "Bug fixes",
            "entry_text": "- :gh:`777`: hallucinated.",
            "amend_gh": None,
            "skip_reason": None,
        }
        with pytest.raises(cb.ValidationError):
            cb.run_decision(pr, decision, year="2026")
        assert clp.read_text() == before_cl


RELEASED_TOP = """\
Changelog
=========

8.0.1 (2026-02-01)
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`10`: released bug.
"""


class TestDecisionPostRelease:
    def test_insert_allowed_even_if_issue_in_released_block(self):
        # The released top block has :gh:`10`; a new PR for the same
        # issue must still insert (into a fresh dev block), not be
        # rejected as a duplicate.
        decision = {
            "action": "insert",
            "section": "Bug fixes",
            "entry_text": "- :gh:`10`: a follow-up fix.",
            "amend_gh": None,
            "skip_reason": None,
        }
        out, status, _ = cb.apply_changelog_decision(
            RELEASED_TOP, decision, {10}
        )
        assert status == "inserted"
        assert "X.X.X (IN DEVELOPMENT)" in out

    def test_amend_rejected_when_top_block_released(self):
        # Amending released history is never allowed.
        decision = {
            "action": "amend",
            "section": None,
            "entry_text": "- :gh:`10`: rewritten released bug.",
            "amend_gh": 10,
            "skip_reason": None,
        }
        with pytest.raises(cb.ValidationError):
            cb.apply_changelog_decision(RELEASED_TOP, decision, {10})


class TestReleasedBlock:
    def test_creates_dev_block_when_top_is_released(self):
        text = """\
Changelog
=========

8.0.1 (2026-02-01)
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`10`: released bug.
"""
        out = cb.insert_entry(text, "Bug fixes", "- :gh:`300`: new bug.")
        lines = out.splitlines()
        dev = lines.index("X.X.X (IN DEVELOPMENT)")
        released = lines.index("8.0.1 (2026-02-01)")
        new = lines.index("- :gh:`300`: new bug.")
        # New dev block sits above the released one, entry inside it.
        assert dev < new < released
        assert lines[dev + 1] == "^" * len("X.X.X (IN DEVELOPMENT)")


class TestGhRequest:
    class _Resp:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return self.body

    def _call(self, result):
        def fake_urlopen(req, timeout=None):
            if isinstance(result, Exception):
                raise result
            return self._Resp(result)

        orig_open = cb.urllib.request.urlopen
        cb.urllib.request.urlopen = fake_urlopen
        cb.TOKEN = "x"
        try:
            return cb.gh_request("/x")
        finally:
            cb.urllib.request.urlopen = orig_open

    def _http_error(self, code):
        return cb.urllib.error.HTTPError(
            "http://x", code, "err", {}, io.BytesIO(b"<html>boom</html>")
        )

    def test_returns_body(self):
        assert self._call(b"ok") == b"ok"

    def test_error_includes_github_body(self):
        # A bare "HTTP Error 404" hides why GitHub refused.
        with pytest.raises(SystemExit, match="boom"):
            self._call(self._http_error(404))
