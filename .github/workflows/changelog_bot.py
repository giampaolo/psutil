# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Activated when commenting "/changelog" on a PR.

This bot will ask Claude to add an entry into docs/changelog.rst based
on the changes introduced in the PR, and also add an entry to
docs/credits.rst.

Requires:

- A subscription to Claude API
- The "ANTHROPIC_API_KEY" environment variable to be set via GitHub
  web interface (Settings -> Secrets & Variables)
"""

import argparse
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.request

# CLI args
PR_NUMBER = None
REPO = None
TOKEN = None
COMMENT_FILE = None
ERROR_FILE = None

CHANGELOG_FILE = "docs/changelog.rst"
CREDITS_FILE = "docs/credits.rst"
MODEL = "claude-sonnet-5"
MAX_DIFF_CHARS = 20_000
COMPARE_MAX_FILES = 300
MAX_TOKENS = 4096  # thinking tokens count against this too
HTTP_TIMEOUT = 30

PROMPT = """\
You are helping maintain the official changelog for psutil, a Python
system monitoring library.

Your task is to decide how ONE pull request should be recorded in the
changelog, and to produce at most ONE entry.

PR #{number}: {title}
Author: @{author} (full name: {author_name})

Description:
{body}

Diff:
{diff}

CURRENT CHANGELOG BLOCK

This is the top (in-development) version block of docs/changelog.rst.
Base your decision on what it already contains:

----- BEGIN BLOCK -----
{block}
----- END BLOCK -----

DECIDING THE ACTION

- insert: the block has no entry for this change. Provide "section"
  and "entry_text".
- amend: the block already has an entry for this issue, or for the
  same user-visible change, and this PR extends or corrects it.
  Provide "amend_gh" (the issue number of that entry) and "entry_text",
  a full replacement entry that keeps the same :gh:`N` reference and
  now covers both changes.
- skip: the block already fully describes this PR. Provide
  "skip_reason".

The script places the text and handles ordering, blank lines, badge
labels and the credits file. It rejects an insert whose issue already
has an entry, so pick amend in that case.

ISSUE NUMBER SELECTION

The entry should reference the GitHub ISSUE number when one exists,
not the pull request number.

1. If the PR title or description references an issue such as
   "Fixes #1234", "Closes #1234", "Refs #1234" or "#1234", use that
   number.
2. If multiple issues are referenced, choose the primary one.
3. If no issue reference exists, fall back to the PR number.

STYLE

- Write concise entries (1-2 sentences max).
- Focus on the user-visible behavior change.
- Avoid implementation details unless relevant.
- Prefer imperative verbs: "fix", "add", "improve", "avoid", "detect".
- Do not repeat the PR title verbatim.
- Do not mention "PR" in the text.
- Wrap lines around ~79 characters.

CLASSIFICATION

Choose the section for an insert, from the vocabulary the changelog
uses (listed in the order sections appear in a release):

- New APIs: a new function, argument or field, or an existing one now
  working where it didn't.
- New platforms: support for a new OS, architecture or interpreter.
- API changes: an existing API changed, was deprecated or was removed.
- Performance: something got faster.
- Build and packaging: wheels, the sdist, what gets installed.
- Documentation: docs/ only.
- Internals: psutil's own machinery: CI, tests, scripts, debug output.
  Nothing user-facing.
- Dropped support: a platform, OS or Python version is no longer
  supported.
- Bug fixes: crashes, wrong results, leaks, build failures.

PLATFORM TAGS

If the change is platform specific, add tags immediately after the
issue reference, e.g.:

:gh:`1234`, [Linux]:
:gh:`1234`, [macOS], [BSD]:

Known tags: [Linux], [Windows], [macOS], [FreeBSD], [NetBSD],
[OpenBSD], [SunOS], [AIX], [BSD], [UNIX], [PyPy]. Use the specific OS
when one is named; [BSD] only when the change is about the BSDs as a
family, [UNIX] for shared POSIX behavior where no single OS fits.
Only add platform tags if the change clearly affects specific OSes.
The script checks every tag against the issue's labels on the bug
tracker and rejects the entry when a tag isn't backed by one.

BADGE LABELS

Do not write :label:`...` badges (critical, build-fail, memleak,
breaking). The script derives them from the issue's labels on the
tracker and adds them to the entry itself.

RST FORMATTING

Use Sphinx roles for psutil APIs: :func:`function_name`,
:meth:`Class.method`, :class:`ClassName`, :exc:`ExceptionName`. C
functions or identifiers use double backticks: ``function_name()``.

ENTRY FORMAT

An entry is a single bullet:

- :gh:`ISSUE_NUMBER`: <description>.

Or with platform tags:

- :gh:`ISSUE_NUMBER`, [Linux]: <description>.

Continuation lines are indented by two spaces. End with a period.

EXAMPLES

- :gh:`2708`, [macOS]: :meth:`Process.cmdline` and
  :meth:`Process.environ` may fail with ``OSError: [Errno 0]``. They
  now raise :exc:`AccessDenied` instead.

- :gh:`2674`, [Windows]: :func:`disk_usage` could truncate values on
  32-bit systems for drives larger than 4GB.
"""

SUBMIT_TOOL = {
    "name": "submit",
    "description": "Submit the changelog decision for this PR.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "action": {
                "type": "string",
                "enum": ["insert", "amend", "skip"],
                "description": (
                    "insert: no entry for this change exists yet. amend:"
                    " the block already has an entry for this issue that"
                    " should be extended/corrected. skip: the block already"
                    " fully covers this PR."
                ),
            },
            "section": {
                "type": ["string", "null"],
                "enum": [
                    "New APIs",
                    "New platforms",
                    "API changes",
                    "Performance",
                    "Build and packaging",
                    "Documentation",
                    "Internals",
                    "Dropped support",
                    "Bug fixes",
                    None,
                ],
                "description": "Required for insert.",
            },
            "entry_text": {
                "type": ["string", "null"],
                "description": (
                    "Full RST entry, wrapped at ~79 cols. Required for"
                    " insert/amend. For amend, the complete replacement"
                    " entry (must keep the same :gh:`N` reference)."
                ),
            },
            "amend_gh": {
                "type": ["integer", "null"],
                "description": (
                    "Issue number of the existing entry to replace."
                    " Required for amend."
                ),
            },
            "skip_reason": {
                "type": ["string", "null"],
                "description": "One sentence. Required for skip.",
            },
        },
        "required": [
            "action",
            "section",
            "entry_text",
            "amend_gh",
            "skip_reason",
        ],
    },
}


def gh_request(path, accept="application/vnd.github+json"):
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return resp.read()
    except urllib.error.HTTPError as err:
        # Surface GitHub's error body; a bare "HTTP Error 404" hides it.
        body = err.read().decode("utf-8", errors="replace")
        sys.exit(f"GitHub API {err.code} for {path}: {body}")


def fetch_pr_metadata():
    pr = json.loads(gh_request(f"/repos/{REPO}/pulls/{PR_NUMBER}"))
    author = pr["user"]["login"]
    # Fetch the user profile to get the full name.
    user = json.loads(gh_request(f"/users/{author}"))
    author_name = user.get("name") or author
    return {
        "number": pr["number"],
        "title": pr["title"],
        "body": pr.get("body") or "",
        "author": author,
        "author_name": author_name,
        "head_sha": pr["head"]["sha"],
    }


def fetch_pr_diff():
    return gh_request(
        f"/repos/{REPO}/pulls/{PR_NUMBER}",
        accept="application/vnd.github.v3.diff",
    ).decode("utf-8", errors="replace")


def stale_reason(head_sha):
    """Why the branch is too old to receive an entry, if it is.
    We commit on top of the PR head, so an entry written against a
    stale copy of the docs makes the PR unmergeable.
    """
    data = json.loads(gh_request(f"/repos/{REPO}/compare/{head_sha}...master"))
    files = [f["filename"] for f in data.get("files", [])]
    stale = [f for f in (CHANGELOG_FILE, CREDITS_FILE) if f in files]
    if stale:
        return f"master has moved on: {' and '.join(stale)} changed"
    if len(files) >= COMPARE_MAX_FILES:
        return "master's diff is too big to tell whether the docs changed"
    return None


def ask_claude(pr, diff, block):
    prompt = PROMPT.format(
        number=pr["number"],
        title=pr["title"],
        author=pr["author"],
        author_name=pr["author_name"],
        body=pr["body"],
        diff=diff[:MAX_DIFF_CHARS],
        block=block,
    )
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY is not set")
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        thinking={"type": "adaptive"},
        output_config={"effort": "low"},
        tools=[SUBMIT_TOOL],
        tool_choice={"type": "tool", "name": "submit"},
        messages=[{"role": "user", "content": prompt}],
    )
    if message.stop_reason == "max_tokens":
        sys.exit("Claude response was truncated (raise MAX_TOKENS)")
    tool_use = next((b for b in message.content if b.type == "tool_use"), None)
    if tool_use is None:
        sys.exit(
            f"Claude returned no tool call (stop_reason={message.stop_reason})"
        )
    return tool_use.input


VERSION_RE = re.compile(r"^(\d+\.\d+\.\d+|X\.X\.X)\b")

# The section vocabulary, in the order sections appear in a release.
SECTIONS = (
    "New APIs",
    "New platforms",
    "API changes",
    "Performance",
    "Build and packaging",
    "Documentation",
    "Internals",
    "Dropped support",
    "Bug fixes",
)

# Badge labels: (tracker label, badge name), in the order badges
# appear in an entry and entries sort within a section.
BADGES = (
    ("critical", "critical"),
    ("build-fail", "build-fail"),
    ("memleak", "memleak"),
    ("compatibility", "breaking"),
)

# Platform tags accepted in an entry, with the tracker label that must
# back each one.
TAG2LABEL = {
    "Linux": "linux",
    "Windows": "windows",
    "macOS": "macos",
    "FreeBSD": "freebsd",
    "NetBSD": "netbsd",
    "OpenBSD": "openbsd",
    "SunOS": "sunos",
    "AIX": "aix",
    "BSD": "bsd",
    "UNIX": "unix",
    "POSIX": "unix",
    "PyPy": "pypy",
}
NAMED_BSD = {"freebsd", "netbsd", "openbsd"}
POSIXY = NAMED_BSD | {"linux", "macos", "sunos", "aix", "bsd", "unix"}

ENTRY_PREFIX_RE = re.compile(
    r"^- (?::gh:`\d+`, )*:gh:`\d+`((?:,? \[[^\]]+\])*)"
)


class ValidationError(Exception):
    """The LLM decision doesn't match the file state; fail loud."""


def find_dev_block(lines):
    """Locate the top version block in a list of changelog lines.

    Returns (start, end, header, is_dev): start/end are line indices
    (end points at the next version header or len(lines)); is_dev is
    False when the top block is an already-released, dated version.
    """
    start = next(
        (i for i, ln in enumerate(lines) if VERSION_RE.match(ln)), None
    )
    if start is None:
        sys.exit(f"No version header found in {CHANGELOG_FILE}")
    end = next(
        (
            i
            for i in range(start + 1, len(lines))
            if VERSION_RE.match(lines[i])
        ),
        len(lines),
    )
    header = lines[start]
    is_dev = "(IN DEVELOPMENT)" in header or header.startswith("X.X.X")
    return start, end, header, is_dev


def changelog_context(text):
    """Return only the top version block, to feed to the LLM."""
    lines = text.splitlines()
    start, end, _, _ = find_dev_block(lines)
    return "\n".join(lines[start:end]).rstrip() + "\n"


def section_header_idx(block, section):
    header = f"**{section}**"
    return next(
        (i for i, ln in enumerate(block) if ln.strip() == header), None
    )


def next_header_idx(block, from_idx):
    """Index of the next ``**...**`` header after from_idx, else end."""
    return next(
        (
            i
            for i in range(from_idx + 1, len(block))
            if block[i].startswith("**")
        ),
        len(block),
    )


def section_rank(header_name):
    """Canonical position of a section header, or None.

    Per-platform variants ("Bug fixes: Linux") rank as their base.
    """
    base = header_name.split(":")[0].strip()
    return SECTIONS.index(base) if base in SECTIONS else None


def create_section(block, section):
    """Insert an empty ``**section**`` header keeping the canonical
    section order.
    """
    rank = SECTIONS.index(section)
    new = [f"**{section}**", ""]
    for i, ln in enumerate(block):
        if ln.startswith("**") and ln.rstrip().endswith("**"):
            got = section_rank(ln.strip().strip("*"))
            if got is not None and got > rank:
                return block[:i] + [*new, ""] + block[i:]
    insert_at = len(block)
    while insert_at > 0 and not block[insert_at - 1].strip():
        insert_at -= 1
    return block[:insert_at] + ["", *new] + block[insert_at:]


def entry_number(line):
    m = re.match(r"- :gh:`(\d+)`", line)
    return int(m.group(1)) if m else None


def entry_tier(line):
    """Sort tier of an entry: badge-labelled ones first, in badge
    order, plain ones last.
    """
    for i, (_, name) in enumerate(BADGES):
        if f":label:`{name}`" in line:
            return i
    return len(BADGES)


def entry_tags(entry_text):
    """The [Platform] tags in an entry's prefix (not its prose)."""
    m = ENTRY_PREFIX_RE.match(entry_text)
    if not m:
        return []
    return re.findall(r"\[([^\]]+)\]", m.group(1))


def check_platform_tags(entry_text, issue_labels):
    """Every [Tag] must be backed by a label on the issue, so the
    changelog never asserts a platform the tracker doesn't know
    about. The family tags are backed by any label of the family.
    """
    have = set(issue_labels)
    for tag in entry_tags(entry_text):
        label = TAG2LABEL.get(tag)
        if label is None:
            raise ValidationError(f"unknown platform tag [{tag}]")
        if label in have:
            continue
        if label == "bsd" and have & NAMED_BSD:
            continue
        if label == "unix" and have & POSIXY:
            continue
        raise ValidationError(
            f"[{tag}] is not backed by a {label!r} label on the issue"
            f" (it has: {sorted(have) or 'none'})"
        )


def rst_words(text):
    """Split on spaces, except inside a `...` or ``...`` span."""
    words, cur, span = [], "", 0
    i = 0
    while i < len(text):
        if text[i] == "`":
            run = 1
            while i + run < len(text) and text[i + run] == "`":
                run += 1
            cur += "`" * run
            i += run
            if span == 0:
                span = run
            elif run >= span:
                span = 0
            continue
        if text[i] == " " and span == 0:
            if cur:
                words.append(cur)
            cur = ""
        else:
            cur += text[i]
        i += 1
    if cur:
        words.append(cur)
    return words


def wrap_entry(flat, width=79):
    """Wrap a one-line entry into '- ' + two-space continuations."""
    out, cur = [], ""
    for word in rst_words(flat):
        trial = f"{cur} {word}" if cur else ("  " + word if out else word)
        if len(trial) > width and cur:
            out.append(cur)
            cur = "  " + word
        else:
            cur = trial
    if cur:
        out.append(cur)
    return "\n".join(out)


def inject_labels(entry_text, issue_labels):
    """Add the :label:`...` badges the issue's labels call for, then
    rewrap. The model never writes badges itself.
    """
    flat = " ".join(ln.strip() for ln in entry_text.splitlines())
    badges = [name for lab, name in BADGES if lab in issue_labels]
    if badges:
        m = ENTRY_PREFIX_RE.match(flat)
        roles = ", ".join(f":label:`{b}`" for b in badges)
        flat = f"{flat[: m.end()]}, {roles}{flat[m.end():]}"
    return wrap_entry(flat)


def insert_in_section(block, section, entry_lines):
    hdr = section_header_idx(block, section)
    if hdr is None:
        block = create_section(block, section)
        hdr = section_header_idx(block, section)
    boundary = next_header_idx(block, hdr)
    # End of the section's content, before any trailing blank lines.
    end = boundary
    while end > hdr + 2 and not block[end - 1].strip():
        end -= 1
    # Start of the last contiguous run of entries. A blank line or a
    # pseudo-header (e.g. "New APIs:") ends a run, so we stay out of
    # earlier groups.
    run_start = end
    while run_start > hdr + 2:
        if not block[run_start - 1].startswith(("- ", "  ")):
            break
        run_start -= 1
    # Insert after the last entry that sorts before ours: labelled
    # entries lead (critical, build-fail, memleak, breaking), plain
    # ones follow, numerically within each tier. Robust to a leading
    # out-of-order entry (we compare keys, not positions).
    gh = entry_number(entry_lines[0])
    tier = entry_tier(entry_lines[0])
    insert_at = run_start
    i = run_start
    while i < end:
        num = entry_number(block[i])
        j = i + 1
        while j < end and block[j].startswith("  "):  # skip continuations
            j += 1
        if block[i].startswith("- "):
            t = entry_tier(block[i])
            if t < tier or (
                t == tier and num is not None and gh is not None and num < gh
            ):
                insert_at = j
        i = j
    return block[:insert_at] + list(entry_lines) + block[insert_at:]


def check_entry_ordered(text, gh):
    """Verify the new :gh:`gh` entry respects its run's ordering:
    labelled entries first in badge order, then plain ones, numeric
    within each tier. Raises ValidationError otherwise. A blank line
    or a pseudo-header ends a run, so an earlier group doesn't count.
    """
    block = changelog_context(text).splitlines()
    idx = next(
        (i for i, ln in enumerate(block) if ln.startswith(f"- :gh:`{gh}`")),
        None,
    )
    if idx is None:
        return
    mine = (entry_tier(block[idx]), gh)

    def run_neighbor(indices):
        for i in indices:
            ln = block[i]
            if ln.startswith("- "):
                return (entry_tier(ln), entry_number(ln))
            if not ln.startswith("  "):  # blank / pseudo-header
                return None
        return None

    def sorts_after(a, b):
        if a[0] != b[0]:
            return a[0] > b[0]
        if a[1] is None or b[1] is None:
            return False
        return a[1] > b[1]

    prev = run_neighbor(range(idx - 1, -1, -1))
    nxt = run_neighbor(range(idx + 1, len(block)))
    if prev is not None and sorts_after(prev, mine):
        raise ValidationError(
            f"changelog: :gh:`{gh}` is out of order (after {prev})"
        )
    if nxt is not None and sorts_after(mine, nxt):
        raise ValidationError(
            f"changelog: :gh:`{gh}` is out of order (before {nxt})"
        )


def prepend_dev_block(lines, start):
    header = "X.X.X (IN DEVELOPMENT)"
    new = [header, "^" * len(header), ""]
    lines = lines[:start] + new + lines[start:]
    return lines, start, start + len(new)


def insert_entry(text, section, entry_text):
    """Append an entry to a section, creating a dev block if needed."""
    lines = text.splitlines()
    start, end, _, is_dev = find_dev_block(lines)
    if not is_dev:
        lines, start, end = prepend_dev_block(lines, start)
    block = lines[start:end]
    block = insert_in_section(block, section, entry_text.splitlines())
    lines[start:end] = block
    return "\n".join(lines) + "\n"


def find_entry_span(block, gh):
    """Return (start, end) of the entry for :gh:`gh` within block lines.

    The span covers the ``- :gh:`gh``` line plus its continuation
    lines. Returns None if there's no such entry.
    """
    prefix = f"- :gh:`{gh}`"
    start = next(
        (i for i, ln in enumerate(block) if ln.startswith(prefix)), None
    )
    if start is None:
        return None
    end = start + 1
    while end < len(block):
        ln = block[end]
        if (
            ln.startswith(("- ", "**"))
            or not ln.strip()
            or VERSION_RE.match(ln)
        ):
            break
        end += 1
    return start, end


def amend_entry(text, gh, entry_text):
    """Replace the dev-block entry for :gh:`gh` with entry_text."""
    lines = text.splitlines()
    start, end, _, _ = find_dev_block(lines)
    block = lines[start:end]
    prefix = f"- :gh:`{gh}`"
    matches = [i for i, ln in enumerate(block) if ln.startswith(prefix)]
    if len(matches) != 1:
        raise ValidationError(
            f"expected one entry for :gh:`{gh}` to amend, found {len(matches)}"
        )
    span_start, span_end = find_entry_span(block, gh)
    block[span_start:span_end] = entry_text.splitlines()
    lines[start:end] = block
    return "\n".join(lines) + "\n"


ENTRY_RE = re.compile(
    r"^- :gh:`(\d+)`(?:,? \[[^\]]+\])*(?:, :label:`[a-z-]+`)*:\s"
)


def referenced_issues(title, body, pr_number):
    """Issue numbers this PR may legitimately reference."""
    text = f"{title}\n{body}"
    pat = r"#(\d+)|GH-(\d+)|/(?:issues|pull)/(\d+)"
    refs = {int(n) for group in re.findall(pat, text) for n in group if n}
    refs.add(pr_number)
    return refs


def validate_entry_text(entry_text):
    """Check an entry's RST shape; return its issue number."""
    entry_lines = entry_text.splitlines()
    m = ENTRY_RE.match(entry_lines[0]) if entry_lines else None
    if not m:
        raise ValidationError(
            f"entry must start with '- :gh:`N`...: ', got: {entry_text!r}"
        )
    if not entry_text.rstrip().endswith("."):
        raise ValidationError("entry must end with a period")
    if entry_text.count("``") % 2 or entry_text.count("`") % 2:
        raise ValidationError("entry has unbalanced backticks")
    for ln in entry_lines[1:]:
        if ln.startswith("- "):
            raise ValidationError("entry must be a single bullet")
        if ln.strip() and not ln.startswith("  "):
            raise ValidationError("continuation lines must be indented")
    return int(m.group(1))


BUGFIX_FAMILY = {
    "linux": "Linux",
    "windows": "Windows",
    "macos": "macOS",
    "freebsd": "BSD",
    "netbsd": "BSD",
    "openbsd": "BSD",
    "bsd": "BSD",
    "sunos": "UNIX",
    "aix": "UNIX",
    "unix": "UNIX",
}


def bugfix_section(text, entry_text):
    """When the dev block splits Bug fixes per platform (8.0.0 does),
    route the entry by its platform tags. Otherwise plain "Bug fixes".
    """
    block = changelog_context(text).splitlines()
    subs = {
        ln.strip().strip("*")
        for ln in block
        if ln.strip().startswith("**Bug fixes:")
    }
    if not subs:
        return "Bug fixes"
    labels = {TAG2LABEL[t] for t in entry_tags(entry_text)}
    names = {BUGFIX_FAMILY.get(lab) for lab in labels} - {None}
    name = names.pop() if len(names) == 1 else "cross-platform"
    for candidate in (f"Bug fixes: {name}", "Bug fixes: cross-platform"):
        if candidate in subs:
            return candidate
    return "Bug fixes"


def apply_changelog_decision(text, decision, allowed_issues):
    """Validate and apply the LLM decision to the changelog text.

    Returns (new_text, status, gh) where status is "inserted",
    "amended" or "skipped" and gh is the issue number touched (None on
    skip). Raises ValidationError on any mismatch, so nothing is
    written on bad input.
    """
    action = decision["action"]
    if action == "skip":
        return text, "skipped", None

    entry_text = decision.get("entry_text")
    if not entry_text:
        raise ValidationError(f"{action} requires entry_text")
    gh = validate_entry_text(entry_text)
    _, _, _, is_dev = find_dev_block(text.splitlines())

    if action == "insert":
        # An insert must reference an issue the PR actually touches; an
        # amend is authorized by the entry already existing in the block
        # (checked in amend_entry), so the PR need not restate it.
        if gh not in allowed_issues:
            raise ValidationError(
                f":gh:`{gh}` is not referenced by this PR"
                f" (allowed: {sorted(allowed_issues)})"
            )
        section = decision.get("section")
        if section not in SECTIONS:
            raise ValidationError(f"invalid section {section!r}")
        if section == "Bug fixes":
            section = bugfix_section(text, entry_text)
        # Only dedup against a real in-development block; after a
        # release the top block is history, and a new entry belongs in
        # a fresh dev block regardless of what shipped.
        if is_dev:
            block_lines = changelog_context(text).splitlines()
            if any(ln.startswith(f"- :gh:`{gh}`") for ln in block_lines):
                raise ValidationError(
                    f"an entry for :gh:`{gh}` already exists; amend it instead"
                )
        new_text = insert_entry(text, section, entry_text)
        check_entry_ordered(new_text, gh)
        return new_text, "inserted", gh

    if action == "amend":
        if not is_dev:
            raise ValidationError(
                "top changelog block is released; cannot amend, insert instead"
            )
        amend_gh = decision.get("amend_gh")
        if amend_gh is None:
            raise ValidationError("amend requires amend_gh")
        if gh != amend_gh:
            raise ValidationError(
                f"amended entry must keep :gh:`{amend_gh}`, got :gh:`{gh}`"
            )
        return amend_entry(text, amend_gh, entry_text), "amended", gh

    raise ValidationError(f"unknown action {action!r}")


def credit_line(author, author_name, gh):
    if author_name and author_name != author:
        who = f":user:`{author_name} <{author}>`"
    else:
        who = f":user:`{author}`"
    return f"* {who} - :gh:`{gh}`"


def credits_sort_key(line):
    s = line.strip()
    # :user:`Name <handle>` or :user:`handle`
    m = re.match(r"\*\s+:user:`([^<`]+?)(?:\s*<[^>]+>)?`", s)
    if m:
        return m.group(1).strip().lower()
    # legacy: * `Display Name`_ - ...
    m = re.match(r"\*\s+`([^`]+)`_", s)
    if m:
        return m.group(1).strip().lower()
    return s.lower()


def credits_handle(line):
    m = re.search(r":user:`(?:[^<`]+<([^>]+)>|([^`<]+))`", line)
    if not m:
        return None
    return (m.group(1) or m.group(2)).strip()


def legacy_name_to_handle(lines):
    """Map a legacy ``Name``_ display name to its GitHub handle.

    Built from the ``.. _`Name`: https://github.com/<handle>`` target
    definitions at the bottom of credits.rst.
    """
    out = {}
    pat = r"\.\. _`([^`]+)`:\s*https?://github\.com/([^/\s]+)"
    for ln in lines:
        m = re.match(pat, ln.strip())
        if m:
            out[m.group(1).strip()] = m.group(2).strip()
    return out


def line_handle(line, name_map):
    """GitHub handle for a credits line (``:user:`` or legacy form)."""
    handle = credits_handle(line)
    if handle:
        return handle
    m = re.match(r"\*\s+`([^`]+)`_", line)
    if m:
        return name_map.get(m.group(1).strip())
    return None


def append_gh_to_line(line, gh):
    ref = f":gh:`{gh}`"
    # Insert before a trailing parenthetical note like "(wheels ...)".
    m = re.search(r"\s+\([^)]*\)\s*$", line)
    if m:
        return f"{line[: m.start()]}, {ref}{line[m.start():]}"
    return f"{line.rstrip()}, {ref}"


def apply_credit(text, author, author_name, gh, year):
    """Add or extend the author's credits line for the given year.

    Returns (new_text, status) where status is "added", "appended" or
    "skipped". @giampaolo is never credited.
    """
    if author == "giampaolo":
        return text, "skipped"
    lines = text.splitlines()
    year_re = re.compile(r"^\d{4}$")
    section_idx = next(
        (
            i
            for i, ln in enumerate(lines)
            if ln.strip() == "Code contributors by year"
        ),
        None,
    )
    if section_idx is None:
        sys.exit(f"'Code contributors by year' not found in {CREDITS_FILE}")

    year_idx = next(
        (
            i
            for i in range(section_idx, len(lines))
            if lines[i].strip() == year
        ),
        None,
    )
    if year_idx is None:
        first_year = next(
            (
                i
                for i in range(section_idx, len(lines))
                if year_re.match(lines[i].strip())
            ),
            len(lines),
        )
        lines[first_year:first_year] = [
            year,
            "~" * len(year),
            "",
            credit_line(author, author_name, gh),
            "",
        ]
        return "\n".join(lines) + "\n", "added"

    year_end = next(
        (
            i
            for i in range(year_idx + 2, len(lines))
            if year_re.match(lines[i].strip())
        ),
        len(lines),
    )
    name_map = legacy_name_to_handle(lines)
    for i in range(year_idx + 2, year_end):
        ln = lines[i]
        if ln.startswith("* ") and line_handle(ln, name_map) == author:
            # A credit may wrap onto 2-space-indented continuation
            # lines; treat the whole thing as one logical entry.
            j = i + 1
            while j < year_end and lines[j].startswith("  "):
                j += 1
            entry = lines[i:j]
            if any(f":gh:`{gh}`" in ln for ln in entry):
                return text, "skipped"
            appended = append_gh_to_line(entry[-1], gh)
            if len(appended) <= 79:
                entry[-1] = appended
            else:
                entry[-1] = entry[-1].rstrip() + ","
                entry.append(f"  :gh:`{gh}`")
            lines[i:j] = entry
            result = resort_credits_year("\n".join(lines) + "\n", year)
            return result, "appended"

    new_line = credit_line(author, author_name, gh)
    key = credits_sort_key(new_line)
    insert_idx = year_end
    for i in range(year_idx + 2, year_end):
        if lines[i].startswith("* ") and credits_sort_key(lines[i]) > key:
            insert_idx = i
            break
    min_idx = year_idx + 3
    while insert_idx > min_idx and not lines[insert_idx - 1].strip():
        insert_idx -= 1
    lines.insert(insert_idx, new_line)
    result = resort_credits_year("\n".join(lines) + "\n", year)
    return result, "added"


def resort_credits_year(text, year):
    """Sort the year's credit entries alphabetically, keeping each
    entry's wrapped continuation lines with it.
    """
    lines = text.splitlines()
    year_re = re.compile(r"^\d{4}$")
    section_idx = next(
        (
            i
            for i, ln in enumerate(lines)
            if ln.strip() == "Code contributors by year"
        ),
        None,
    )
    if section_idx is None:
        return text
    year_idx = next(
        (
            i
            for i in range(section_idx, len(lines))
            if lines[i].strip() == year
        ),
        None,
    )
    if year_idx is None:
        return text
    start = year_idx + 2
    while start < len(lines) and not lines[start].strip():
        start += 1
    end = next(
        (
            i
            for i in range(year_idx + 2, len(lines))
            if year_re.match(lines[i].strip())
        ),
        len(lines),
    )
    while end > start and not lines[end - 1].strip():
        end -= 1
    entries = []
    for ln in lines[start:end]:
        if ln.startswith("* ") or not entries:
            entries.append([ln])
        else:
            entries[-1].append(ln)
    entries.sort(key=lambda e: credits_sort_key(e[0]))
    lines[start:end] = [ln for entry in entries for ln in entry]
    return "\n".join(lines) + "\n"


def write_file(path, body):
    """Write a PR comment body for the workflow to post later.

    Success and validation-error bodies go to different files so the
    workflow's failure step never posts a stale "entry added" body when
    a later step (e.g. the push) is what failed.
    """
    print(body)
    if path:
        with open(path, "w") as f:
            f.write(body)


def parse_cli():
    global PR_NUMBER, REPO, TOKEN, COMMENT_FILE, ERROR_FILE
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pr-number", type=int, required=True)
    p.add_argument(
        "--repo", type=str, required=True, help="e.g. giampaolo/psutil"
    )
    p.add_argument("--token", type=str, required=True, help="GitHub token")
    p.add_argument(
        "--comment-file",
        type=str,
        default=None,
        help="On success, write the PR comment body here",
    )
    p.add_argument(
        "--error-file",
        type=str,
        default=None,
        help="On a validation failure, write the error comment here",
    )
    args = p.parse_args()
    PR_NUMBER = args.pr_number
    REPO = args.repo
    TOKEN = args.token
    COMMENT_FILE = args.comment_file
    ERROR_FILE = args.error_file


def build_comment(cl_status, cr_status, decision, gh, author):
    """Compose the PR comment strictly from what the script did."""
    entry = decision.get("entry_text") or ""
    block = f"```rst\n{entry}\n```"
    if cl_status == "inserted":
        section = decision["section"]
        header = f"`{CHANGELOG_FILE}` entry added under **{section}**:"
        parts = [f"{header}\n\n{block}"]
    elif cl_status == "amended":
        header = f"`{CHANGELOG_FILE}` entry for :gh:`{gh}` amended:"
        parts = [f"{header}\n\n{block}"]
    else:
        reason = decision.get("skip_reason") or "already covered"
        parts = [f"`{CHANGELOG_FILE}` **not** modified (skipped): {reason}"]

    if cr_status == "added":
        parts.append(f"`{CREDITS_FILE}`: credited @{author} for :gh:`{gh}`.")
    elif cr_status == "appended":
        parts.append(
            f"`{CREDITS_FILE}`: appended :gh:`{gh}` to @{author}'s line."
        )
    return "\n\n".join(parts)


def fetch_issue_labels(number):
    raw = json.loads(gh_request(f"/repos/{REPO}/issues/{number}"))
    return sorted(x["name"] for x in raw["labels"])


def run_decision(pr, decision, year=None, get_labels=fetch_issue_labels):
    """Apply the decision to both files; return (cl_status, cr_status, gh)."""
    allowed = referenced_issues(pr["title"], pr["body"], pr["number"])
    entry = decision.get("entry_text")
    if decision.get("action") != "skip" and entry:
        if ":label:`" in entry:
            raise ValidationError(
                "entry must not contain :label: badges; they are"
                " derived from the issue's labels"
            )
        labels = get_labels(validate_entry_text(entry))
        check_platform_tags(entry, labels)
        # In place, so the PR comment shows what was really written.
        decision["entry_text"] = inject_labels(entry, labels)
    with open(CHANGELOG_FILE) as f:
        changelog = f.read()
    new_changelog, cl_status, gh = apply_changelog_decision(
        changelog, decision, allowed
    )
    # A no-op amend (identical text) changes nothing; report it as a
    # skip so the comment doesn't claim an edit that never happened.
    if cl_status != "skipped" and new_changelog == changelog:
        cl_status, gh = "skipped", None
    if cl_status != "skipped":
        with open(CHANGELOG_FILE, "w") as f:
            f.write(new_changelog)
    print(f"Changelog: {cl_status}")

    cr_status = "skipped"
    if gh is not None:
        year = year or str(datetime.date.today().year)
        with open(CREDITS_FILE) as f:
            credits = f.read()
        new_credits, cr_status = apply_credit(
            credits, pr["author"], pr["author_name"], gh, year
        )
        if cr_status != "skipped":
            with open(CREDITS_FILE, "w") as f:
                f.write(new_credits)
    print(f"Credits: {cr_status}")
    return cl_status, cr_status, gh


def main():
    parse_cli()
    print(f"Fetching PR #{PR_NUMBER} from {REPO}...")
    pr = fetch_pr_metadata()
    stale = stale_reason(pr["head_sha"])
    if stale:
        write_file(
            ERROR_FILE,
            f"⚠️ The /changelog bot did nothing: {stale}. Committing an"
            " entry now would make this PR unmergeable. Click **Update"
            " branch**, then comment `/changelog` again.",
        )
        sys.exit(f"stale branch: {stale}")
    diff = fetch_pr_diff()
    with open(CHANGELOG_FILE) as f:
        block = changelog_context(f.read())
    print("Asking Claude for changelog decision...")
    decision = ask_claude(pr, diff, block)
    print(f"Decision: {decision}")
    try:
        cl_status, cr_status, gh = run_decision(pr, decision)
    except ValidationError as err:
        blob = json.dumps(decision, indent=2)
        write_file(
            ERROR_FILE,
            f"⚠️ The /changelog bot could not apply the entry: {err}\n\n"
            f"Model output:\n\n```json\n{blob}\n```",
        )
        sys.exit(f"validation failed: {err}")
    write_file(
        COMMENT_FILE,
        build_comment(cl_status, cr_status, decision, gh, pr["author"]),
    )


if __name__ == "__main__":
    main()
