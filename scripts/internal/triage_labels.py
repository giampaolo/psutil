#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Setup the right labels for GitHub issues and PRs by asking Claude.

Usage:
    python3 scripts/internal/triage_labels.py 2635
    python3 scripts/internal/triage_labels.py 2635 1783 2029
    python3 scripts/internal/triage_labels.py 2635 --apply
    python3 scripts/internal/triage_labels.py 2635 1783 --via-cli
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

REPO = "giampaolo/psutil"
HTTP_TIMEOUT = 30
MAX_BODY_CHARS = 6000
MAX_FILES = 100
MAX_TOKENS = 2048
# How long to give one `claude -p` call. A chunk of tickets takes a
# minute or so; this is just there to stop a hung one hanging us.
CLI_TIMEOUT = 900

# Set by parse_cli().
TOKEN = ""
MODEL = ""
NUMBERS = []
APPLY = False
VIA_CLI = False
CHUNK = 0

PROMPT = """\
You are triaging a psutil issue or pull request. psutil is a Python
library that reads process and system information, with a Python layer
per platform (_pslinux.py, _pswindows.py, ...) backed by C extensions.

Type is always exactly one label. Platform and component are lists and
may name more than one, though most items need a type and a platform
and nothing else. On those two, leave the list empty rather than
reaching for a label that only half fits: a wrong label is worse than
no label.

TYPE

- bug: something is broken, wrong, or crashes.
- enhancement: something new, faster, or improved.

Every item gets one of the two, no exceptions. The changelog is split
into those same two sections, so an item with neither has nowhere to
go. Questions, discussions and tracking issues included: if nothing is
broken, it's an enhancement.

The template's "Bug fix: yes/no" line is a hint, not the answer. Read
what the change does. Adding support for something that never worked
is an enhancement even when the author ticked yes.

PLATFORM

Fill this only when the item is specific to where psutil runs: an OS,
a container, a different cPython implementation (PYPY). A bug that would
happen anywhere is an empty list, even when the reporter happens to be
on Linux.

A "[Linux]" tag in the title or a filled-in "* OS: ..." line is the
reporter saying it outright, so take them at their word. When they
name two or three, list all of them. These mix freely, so a container
bug on Linux is ["linux", "vm"].

On a PR, the changed files outrank that line. People fill the template
in loosely and it is often stale or plain wrong: a PR whose only file
is .github/workflows/build.yml has no platform, whatever its "OS:"
line claims. Believe the diff.

Going wide is the opposite of specific, so leave it empty. A sweep
across every arch/ directory, a refactor of shared code, anything that
lands everywhere: no platform at all. Four or more is nearly always
this mistake. Don't read a PR's changed files as a list of platforms
to claim.

That rule is about the diff, not the title. Names written in the title
always count, tagged or not: "[Windows/Linux/Mac] ..." and "publish
macos and linux wheels" each name platforms out loud, so list them.
An environment counts as the OS it runs on, so cygwin and msys are
windows.

One path does settle it. psutil/arch/ holds a directory per platform,
and a diff that stays inside one of them says which: arch/windows/ is
windows, arch/osx/ is macos, arch/solaris/ is sunos, arch/bsd/ is bsd,
arch/posix/ is unix. Only arch/all/ is everywhere. Land in two of them
and you're back to the sweep above.

An OS named in passing is not the subject either. "Known cases are
AccessDenied on Windows and a null ctime on NetBSD" is a cross-platform
bug illustrated with examples, so the list stays empty. "OS: all" means
empty no matter which names follow it. Ask what the fix changes, not
where the symptom was noticed.


- linux, windows, macos, freebsd, openbsd, netbsd, sunos, aix: the
  item is about that OS.

- bsd: the item is about the BSDs as a family. "on all 3 BSDs", a
  "[BSD]" tag, a fix in the shared psutil/arch/bsd/ code. Listing the
  three by name changes nothing: "all 3 BSDs (FreeBSD, OpenBSD,
  NetBSD)" is still one bsd label, not three. Reach for the specific
  ones only when the item is about some of them but not all.

- unix: very rare. Shared POSIX code across several unices where no
  single OS fits and the item names none. Something POSIX has and
  Windows doesn't counts even with nothing named: zombie processes,
  signals, uid and gid, fork, terminals. So does a diff confined to
  psutil/arch/posix/ or _psutil_posix.c. It stands alone: the moment
  you can name one OS, list that instead.

- vm: any container or virtual OS, Docker included. Only when it's
  material, not merely where the reporter happened to run.

- pypy: the item is about running under PyPy, not CPython.

COMPONENT

Usually empty. Roughly half of all items are just a platform bug with
no component at all. Two is common enough: a cibuildwheel change in a
workflow file is ["wheels", "ci"]. Three is rarer but real, and a CI
change to the wheel build that is also a speedup earns all three.
Four is almost certainly wrong.

The rule for all of them: the item has to be *specific* to the
component, not merely touch it. A new feature updates the docs, adds
tests and maybe a script, and it is still just the feature. Only reach
for a component label when it is what the item is for. These get
over-applied, so the labels already in the repo are a poor guide. When
in doubt, leave the list empty.


- doc: prose under docs/, the README, docstrings, the doc build or
  theme. A docstring-only fix counts even though it lives in a .py
  file. A feature or bugfix that updates the docs on the way past
  does not: that one is the feature or the bug.

- tests: the test suite and nothing else. A flaky test, a slow test, a
  test asserting the wrong thing, a skip, a test helper. For a PR the
  changed files settle it: touching library code (psutil/*.py,
  psutil/arch/, the C extensions) means the PR is about that code, so
  no; tests plus boilerplate like HISTORY.rst or the Makefile is fine.
  A reported test failure that turns out to be a real bug is that bug,
  and the PR fixing it gets the bug's labels, never this one.

- ci: psutil's own automation. Anything under .github/workflows/, plus
  cirrus, appveyor and travis. A "CI:" prefix in the title says it
  outright, so take it. The runners and the test matrix, but
  equally the bots and release jobs that never run a test: a changed
  workflow file is nearly always this. Also a job failing for reasons
  unrelated to the code under test.

- scripts: psutil's own scripts/ directory, including the examples.
  Not the reporter's script. People often paste one to show a bug;
  that bug is about whatever it exercises.

- wheels: building or publishing psutil's wheels. The release matrix,
  manylinux, a wheel missing from PyPI. cibuildwheel settles it on its
  own: an item that touches it is about wheels, even when the change
  is to the workflow around it, in which case it is ci as well. A
  compile error on the reporter's own machine is just a build bug.

- new-api: the public API grows. A brand new function or method, but
  equally a new argument on one that already exists, a new field in a
  namedtuple it returns, a new value it can now give back. Anything
  that hands callers something they couldn't reach before. Making an
  existing call work on one more platform is not this.

- performance: speed or resource usage is the point. Slow is
  performance, wrong is a bug, and an optimisation is usually
  enhancement and performance at once. psutil's own build and CI count
  too: making the suite, the wheel build or a workflow faster is
  performance, on top of ci or wheels. A timing table, or a benchmark
  showing timings before and after, is the giveaway. So is releasing
  and reacquiring the GIL around a blocking syscall, numbers or no
  numbers: the whole point is letting other threads run.

- memleak: memory is leaked. Growth without bound, but also a single
  allocation or refcount never released, error paths included. If the
  text says leak and points at what leaks, that's this.

- compatibility: psutil's support matrix moves, or what callers can
  rely on does. Dropping an old Python or OS version, or restoring
  one psutil had lost. Dropping a wheel target or an interpreter
  build, removing a dependency that moves the floor psutil builds
  on, removing or renaming a public API, dropping a field from a
  namedtuple. The test is whether a working install or working code
  has to change. Correcting a value that was simply wrong is not
  this, it's the bug fix, and a one-off build error on a platform
  psutil already supports is a plain bug, not a change of support.

- new-platform: support for an operating system psutil does not target
  yet.

CRITICAL

psutil's public API is allowed to raise NoSuchProcess, AccessDenied
and ZombieProcess. Anything else escaping a psutil call is a defect
of a different order: a RuntimeError, a SystemError, an
OverflowError, a segfault or a hang. Set critical for those.

It has to be psutil raising. People paste the whole traceback from
whatever program hit the problem and most of those frames are
somebody else's, so find psutil in the failing one before setting
this. An umbrella or audit issue collecting many findings isn't one
either. Neither is a wrong value, a slow call or a leak: those are
plain bugs, however annoying.

CONFIDENCE

Give type, platform, component and critical a confidence. Use low when
the text is too thin to tell, so the choice can be discarded later. An
empty answer with high confidence means you are sure nothing applies,
and is what lets a wrong label already on the ticket be cleared.

EXAMPLES

Title: "Process.memory_info() returns 0 for all processes on Windows 11"
type=bug, platform=["windows"], component=[]. A plain platform bug,
which is the most common shape. No component label applies.

Title: "add Process.num_threads() to the AIX implementation"
type=enhancement, platform=["aix"], component=["new-api"].

Title: "test_disk_partitions fails on the macOS runner since the image
bump"
type=bug, platform=["macos"], component=["ci"]. The suite is fine; the
runner image changed. Not tests.

Title: "test_cpu_percent asserts the wrong bound"
type=bug, platform=[], component=["tests"]. The test code is wrong, and
it is wrong everywhere.

Title: "[SunOS] test_unix fails: invalid kind argument 'unix'"
type=bug, platform=["sunos"], component=[]. A test is how this
surfaced, but net_connections() really is missing a kind on SunOS.
Fix the code and the test goes green, so the bug is the item.

Title: "cpu_times() is 3x slower than it needs to be"
type=enhancement, component=["performance"].

Title: "[OpenBSD, NetBSD] build failed"
type=bug, platform=["openbsd", "netbsd"]. Both named, so both go in.
Not bsd.

Title: "macOS: fix SystemError in Process.cmdline() and environ()"
type=bug, platform=["macos"], critical=true. SystemError isn't one of
the three psutil is allowed to raise, so it counts however small the
fix turns out to be.

Title: "[Windows] net_if_stats() reports the wrong link speed"
type=bug, platform=["windows"], critical=false. A wrong number is a
plain bug. Nothing got out that shouldn't have.

Title: "Fix refcount leaks on parse failure (Linux disk_partitions,
SunOS proc)"
type=bug, platform=["linux", "sunos"], component=["memleak"]. Both
named, and a leak down an error path is still a leak.

Title: "Drop Python 3.6 and 3.7"
type=enhancement, component=["compatibility"]. Installs that worked
have to change. No platform: this isn't about where psutil runs.

Title: "Upgrade cibuildwheel to 4.1.1, drop cp313t wheels"
type=enhancement, component=["wheels", "ci", "compatibility"].
cibuildwheel means wheels, it lands in a workflow so ci, and dropping
a build target narrows what we ship. Three is unusual and here it's
right.

Title: "docs: add explanatory comments to the README examples"
type=enhancement, component=["doc"]. Prose and nothing else, so doc is
what the item is for rather than something it touched on the way past.

Answer with the submit tool."""

# Kept out of PROMPT so the cached prefix is byte-identical between
# tickets. Anything ticket-specific has to live after the breakpoint.
TICKET = """\
Kind: {kind}
Title: {title}

Body:
{body}
{files}"""


# --- the label taxonomy, as axes
#
# The axis names are the label descriptions on GitHub: bug and
# enhancement are described as "type", the OSes as "platform". Only
# some of the component labels carry the description, but they group
# the same way.

TYPE_LABELS = ["bug", "enhancement"]
PLATFORM_LABELS = [
    "linux", "windows", "macos", "freebsd", "openbsd", "netbsd", "bsd",
    "sunos", "aix", "unix", "vm", "pypy",
]  # fmt: skip
CRITICAL_LABELS = ["critical"]
COMPONENT_LABELS = [
    "doc", "tests", "ci", "scripts", "wheels", "new-api",
    "performance", "memleak", "compatibility", "new-platform",
]  # fmt: skip

# Bot workflow state and dependabot's own labels. The model never sees
# these and they're stripped before any comparison.
IGNORED_LABELS = {
    "imported",
    "need-more-info",
    "dependencies",
    "github_actions",
}

AXES = ("type", "platform", "component", "critical")
# Axes holding a list instead of a single value. Plenty of items name
# more than one OS, and a container bug is a platform on top of one.
# Components overlap too: a cibuildwheel change in a workflow file is
# both wheels and ci.
LIST_AXES = ("platform", "component")
# Axes answered yes or no rather than with a label.
BOOL_AXES = ("critical",)
AXIS_LABELS = {
    "type": TYPE_LABELS,
    "platform": PLATFORM_LABELS,
    "component": COMPONENT_LABELS,
    "critical": CRITICAL_LABELS,
}
# Axes we'll drop a stale label from. Only the ones carrying a
# confidence, so there's something to gate the removal on. critical is
# missing on purpose: the maintainer sets it by his own judgement of
# how much a bug hurts, and the text can suggest it but never rule it
# out. We add, we never take away.
REMOVABLE_AXES = ("type", "platform", "component")

# Pairs that can't both be true. An item is a bug or an enhancement,
# never both, and bsd means "the family, none of them named", so it
# can't sit beside one that is. unix is the same idea one level up:
# it's for POSIX code where no single OS fits, so naming any of them
# rules it out. Without this a medium-confidence answer leaves the old
# label in place next to the new one.
INCOMPATIBLE = (
    ("bug", "enhancement"),
    ("bsd", "freebsd"),
    ("bsd", "openbsd"),
    ("bsd", "netbsd"),
    ("unix", "bsd"),
    ("unix", "linux"),
    ("unix", "macos"),
    ("unix", "freebsd"),
    ("unix", "openbsd"),
    ("unix", "netbsd"),
    ("unix", "sunos"),
    ("unix", "aix"),
)


def enum_list(labels, description):
    return {
        "type": "array",
        "items": {"type": "string", "enum": labels},
        "description": description,
    }


def axis_values(decision, axis):
    """What a decision puts on one axis, always as a set."""
    value = decision[axis]
    if axis in LIST_AXES:
        return set(value)
    if axis in BOOL_AXES:
        return {axis} if value else set()
    return {value} if value else set()


CONFIDENCE = {"type": "string", "enum": ["high", "medium", "low"]}

DECISION_PROPS = {
    "type": {
        "type": "string",
        "enum": TYPE_LABELS,
        "description": "bug or enhancement. Always one of the two.",
    },
    "type_confidence": CONFIDENCE,
    "platform": enum_list(
        PLATFORM_LABELS,
        "Every OS, container or interpreter the item is specific to."
        " Often empty.",
    ),
    "platform_confidence": CONFIDENCE,
    "component": enum_list(
        COMPONENT_LABELS,
        "What the item is specifically about. Usually empty, sometimes two.",
    ),
    "component_confidence": CONFIDENCE,
    "critical": {
        "type": "boolean",
        "description": (
            "psutil raises something other than NoSuchProcess,"
            " AccessDenied or ZombieProcess."
        ),
    },
    "critical_confidence": CONFIDENCE,
}

SUBMIT_TOOL = {
    "name": "submit",
    "description": "Submit the label decision for this issue or PR.",
    # Without this the schema is advisory: seen returning a single
    # out-of-enum field, and nesting the payload under "parameter name".
    "strict": True,
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": DECISION_PROPS,
        "required": list(DECISION_PROPS),
    },
}

# --- github


def gh_request(path, post=None, method=None):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        data=json.dumps(post).encode() if post else None,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        sys.exit(f"GitHub API {err.code} for {path}: {body}")


def fetch_item(number):
    """One issue or PR, in the shape classify() wants."""
    raw = gh_request(f"/repos/{REPO}/issues/{number}")
    item = {
        "number": raw["number"],
        "title": raw["title"],
        "body": raw.get("body") or "",
        "is_pr": "pull_request" in raw,
        "labels": sorted(x["name"] for x in raw["labels"]),
        "files": [],
    }
    if item["is_pr"]:
        files = gh_request(f"/repos/{REPO}/pulls/{number}/files")
        item["files"] = [f["filename"] for f in files][:MAX_FILES]
    return item


# "Fixes #123", "closes gh-123", the full URL, all of it.
CLOSES = re.compile(
    r"\b(?:fix(?:e[sd])?|close[sd]?|resolve[sd]?)\b[\s:]*"
    r"(?:https?://github\.com/[\w.-]+/[\w.-]+/issues/|gh-|#)(\d+)",
    re.IGNORECASE,
)


def closed_issues(item):
    """Issues this PR says it fixes."""
    if not item["is_pr"]:
        return []
    seen = []
    for match in CLOSES.finditer(item["body"][:MAX_BODY_CHARS]):
        number = int(match.group(1))
        if number != item["number"] and number not in seen:
            seen.append(number)
    return seen


def inherit_from_closed(labels, item, issue_labels):
    """Take from the issue what the PR's own text can't show.

    A PR and the issue it closes are about one defect, but they
    describe different halves of it. The issue quotes the traceback;
    the PR says "handle EFAULT" and never names an exception, so it
    reads as an ordinary fix. Same for the platform: the reporter
    said which OS, the patch just changes a file.

    Across the sweep 31% of linked pairs ended up disagreeing, and
    critical was the single biggest cause. Only those two are taken.
    Whether something is a fix or a feature, and what area it touches,
    the PR says perfectly well on its own.
    """
    out = set(labels)
    if "critical" in issue_labels:
        out.add("critical")
    if not out & set(PLATFORM_LABELS):
        out |= set(issue_labels) & set(PLATFORM_LABELS)
    return out


def add_labels(number, labels):
    """Add labels to a ticket. This endpoint never removes any."""
    gh_request(
        f"/repos/{REPO}/issues/{number}/labels", {"labels": sorted(labels)}
    )


def remove_label(number, label):
    path = urllib.parse.quote(label)
    gh_request(f"/repos/{REPO}/issues/{number}/labels/{path}", method="DELETE")


def axis_of(label):
    for axis, labels in AXIS_LABELS.items():
        if label in labels:
            return axis
    return None


def resolve_conflicts(labels, decision, current=frozenset()):
    """Drop the losing half of any impossible pair.

    Only where the model picked a side, and only where it was sure of
    the axis that decides it. Without that second test this quietly
    undid the gate in stale_labels(): a medium-confidence "enhancement"
    couldn't remove a hand-applied bug directly, but it could sit next
    to it, be declared the winner here, and take it off anyway. Below
    high confidence the label already on the ticket wins instead.

    Two labels that already contradicted each other before we touched
    the ticket are left alone: that's the maintainer's mess, not one
    we made.
    """
    out = set(labels)
    judged = model_labels(decision)
    for left, right in INCOMPATIBLE:
        if not {left, right} <= out:
            continue
        axis = axis_of(left) or axis_of(right)
        if axis and decision.get(f"{axis}_confidence") != "high":
            # Not sure enough to overrule anyone. If the ticket already
            # carried one of the two, that one stays and ours goes.
            held = {left, right} & set(current)
            if len(held) == 1:
                out -= {left, right} - held
            continue
        if left in judged and right not in judged:
            out.discard(right)
        elif right in judged and left not in judged:
            out.discard(left)
    return out


def fresh_labels(decision):
    """The labels a decision is willing to stand behind.

    Removals already ignore anything below high confidence. Additions
    used to go in regardless, which is how a "fix typos in comments"
    PR ended up tagged bug on a low-confidence guess. Low means the
    model is guessing, so nothing gets applied from that axis. Medium
    still counts: it covers a good third of the corpus and is right
    most of the time.
    """
    out = set()
    for axis in AXES:
        # type is exempt. It has no "neither" answer and the changelog
        # has a section for each, so dropping a shaky one leaves the
        # item with nowhere to go. A coin flip between two beats that.
        if axis == "type" or decision[f"{axis}_confidence"] != "low":
            out |= axis_values(decision, axis)
    return out


def stale_labels(item, decision):
    """Labels the model just contradicted on the same axis.

    Only where it was sure. Medium or low confidence means "I can't
    tell", which is no reason to delete what a person put there.

    A confident empty answer does count: the prompt asks for null with
    high confidence to mean "certain nothing here applies", and that is
    the only way a wrong label ever gets cleared. Labels off the axes,
    critical among them, are never touched.
    """
    keep = model_labels(decision)
    out = set()
    for axis in REMOVABLE_AXES:
        if decision[f"{axis}_confidence"] != "high":
            continue
        out |= {x for x in item["labels"] if x in AXIS_LABELS[axis]} - keep
    return out


# --- the model
#
# classify(), PROMPT and SUBMIT_TOOL are what moves into triage_bot.py.
# Between them they touch nothing but the title, the body and the
# changed files, which is what a webhook payload can hand over.


class BadDecision(Exception):
    """The model's tool call doesn't match the schema."""


def allowed_values(prop):
    """The values a schema property accepts, None if unconstrained."""
    if "enum" in prop:
        return prop["enum"]
    if prop.get("type") == "array":
        return prop["items"]["enum"]
    for branch in prop.get("anyOf", []):
        if "enum" in branch:
            return [*branch["enum"], None]
    return None


def build_prompt(title, body, files):
    listing = ""
    if files:
        names = "\n".join(f"- {f}" for f in files)
        listing = f"\nChanged files:\n{names}\n"
    return TICKET.format(
        # An issue has no changed files, a PR always has at least one.
        kind="pull request" if files else "issue",
        title=title,
        body=body[:MAX_BODY_CHARS] or "(empty)",
        files=listing,
    )


def check_decision(decision):
    """Fail loud on a decision that doesn't match the schema.

    strict=True should make this unreachable, but a malformed decision
    reads downstream as "no labels" and quietly poisons the result,
    which has already happened once.
    """
    unknown = set(decision) - set(DECISION_PROPS)
    missing = set(DECISION_PROPS) - set(decision)
    if unknown or missing:
        raise BadDecision(
            f"bad keys (unknown={sorted(unknown)},"
            f" missing={sorted(missing)}): {decision}"
        )
    for name, value in decision.items():
        allowed = allowed_values(DECISION_PROPS[name])
        if allowed is None:
            continue
        if not isinstance(value, list):
            value = [value]
        elif len(set(value)) != len(value):
            raise BadDecision(f"{name}={value!r} has duplicates")
        for one in value:
            if one not in allowed:
                raise BadDecision(f"{name}={one!r} not in {allowed}")


def thinking_kwargs():
    if MODEL.startswith(
        ("claude-opus-5", "claude-sonnet-5", "claude-fable-5")
    ):
        return {
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": "low"},
        }
    return {}


def classify(client, title, body, files):
    """Ask Claude which labels apply.

    Returns (decision, usage). Pass files=None for an issue. Raises
    BadDecision when the tool call doesn't validate, so a bad answer
    can't pass for an empty one.
    """
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        **thinking_kwargs(),
        tools=[SUBMIT_TOOL],
        tool_choice={"type": "tool", "name": "submit"},
        # Tools and system render before messages, so this one
        # breakpoint caches the schema and the taxonomy together. The
        # ticket goes after it, where it can vary without a miss.
        system=[{
            "type": "text",
            "text": PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[
            {"role": "user", "content": build_prompt(title, body, files)}
        ],
    )
    if message.stop_reason == "max_tokens":
        raise BadDecision("response truncated (raise MAX_TOKENS)")
    block = next((b for b in message.content if b.type == "tool_use"), None)
    if block is None:
        raise BadDecision(f"no tool call (stop_reason={message.stop_reason})")
    check_decision(block.input)
    return block.input, message.usage


# --- the model, through the claude CLI
#
# Same taxonomy, but billed against a Claude subscription instead of
# API credits. Launching the CLI costs tens of thousands of tokens
# before it reads a word of the prompt, so tickets go in a chunk at a
# time and that overhead gets spread over all of them.


def build_cli_prompt(items):
    """One prompt covering a whole chunk of tickets.

    There's no tool to call here, so the schema goes in the text and
    the answer comes back as JSON.
    """
    schema = json.dumps(SUBMIT_TOOL["input_schema"]["properties"], indent=1)
    tickets = "\n\n".join(
        f"=== ITEM {number} ===\n"
        + build_prompt(item["title"], item["body"], item["files"])
        for number, item in items.items()
    )
    return (
        PROMPT.replace("Answer with the submit tool.", "")
        + f"\n\nYou are given {len(items)} items, each headed by"
        " '=== ITEM <number> ==='. Judge each one on its own, with the"
        " same care you'd give a single item.\n\nReply with ONLY a JSON"
        " array, one object per item, in the order given. No prose, no"
        " markdown fence. Each object carries a 'number' field plus"
        f" exactly these:\n{schema}\n\n{tickets}"
    )


def classify_via_cli(items):
    """Ask the claude CLI to label a chunk of tickets.

    Returns {number: decision}. Anything that comes back malformed is
    warned about and left out, rather than sinking the whole chunk.
    """
    proc = subprocess.run(
        ["claude", "-p", "--model", MODEL, "--output-format", "json"],
        input=build_cli_prompt(items),
        capture_output=True,
        text=True,
        timeout=CLI_TIMEOUT,
        check=False,
    )
    if proc.returncode != 0:
        sys.exit(f"claude -p failed ({proc.returncode}): {proc.stderr[:500]}")
    envelope = json.loads(proc.stdout)
    usd = envelope.get("total_cost_usd") or 0
    print(f"chunk of {len(items)}: ${usd:.4f} (${usd / len(items):.5f}/item)")

    raw = envelope["result"].strip()
    # It's told not to fence the JSON, but it sometimes does anyway.
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        replies = json.loads(raw)
    except json.JSONDecodeError as err:
        sys.exit(f"claude -p didn't return JSON ({err}): {raw[:300]}")

    out = {}
    for reply in replies:
        number = reply.pop("number", None)
        if number not in items:
            print(f"warning: unknown item {number!r}", file=sys.stderr)
            continue
        try:
            check_decision(reply)
        except BadDecision as err:
            print(f"warning: #{number}: {err}", file=sys.stderr)
            continue
        out[number] = reply
    missing = sorted(set(items) - set(out))
    if missing:
        print(f"warning: no decision for {missing}", file=sys.stderr)
    return out


def model_labels(decision):
    """Flatten a decision into the label set it implies."""
    out = set()
    for axis in AXES:
        out |= axis_values(decision, axis)
    return out


# --- cli


def make_client():
    import anthropic

    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        path = os.path.expanduser("~/.anthropic.api.key")
        if not os.path.exists(path):
            sys.exit(f"no ANTHROPIC_API_KEY and no {path}")
        with open(path) as f:
            key = f.read().strip()
    return anthropic.Anthropic(api_key=key)


def fmt(labels):
    return ", ".join(sorted(labels)) if labels else "-"


def report(item, decision):
    kind = "PR" if item["is_pr"] else "issue"
    print(f"#{item['number']} ({kind}) {item['title']}")
    for axis in AXES:
        conf = decision.get(f"{axis}_confidence")
        suffix = f"  ({conf})" if conf else ""
        print(f"  {axis:12s} {fmt(axis_values(decision, axis))}{suffix}")
    print(f"  already has: {fmt(set(item['labels']) - IGNORED_LABELS)}")


def parse_cli():
    global TOKEN, MODEL, NUMBERS, APPLY, VIA_CLI, CHUNK
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("numbers", nargs="+", type=int, help="issue or PR numbers")
    p.add_argument(
        "--token",
        default="~/.github.api.key",
        help="file holding a GitHub token",
    )
    p.add_argument("--model", default="claude-sonnet-5")
    p.add_argument(
        "--apply",
        action="store_true",
        help="add the labels on GitHub; without this nothing is written",
    )
    p.add_argument(
        "--via-cli",
        action="store_true",
        help="go through the claude CLI instead of the paid API",
    )
    p.add_argument(
        "--chunk",
        type=int,
        default=10,
        help="tickets per claude CLI call (--via-cli only)",
    )
    args = p.parse_args()
    if args.chunk < 1:
        p.error("--chunk must be at least 1")
    with open(os.path.expanduser(args.token)) as f:
        TOKEN = f.read().strip()
    MODEL = args.model
    NUMBERS = args.numbers
    APPLY = args.apply
    VIA_CLI = args.via_cli
    CHUNK = args.chunk


def show_tokens(prefix, usage):
    print(
        f"  {prefix:12s} {usage.input_tokens} in,"
        f" {usage.cache_read_input_tokens} cached,"
        f" {usage.output_tokens} out"
    )


def handle(item, decision, usage, totals, index):
    """Print one decision and, with --apply, act on it."""
    if index:
        print()
    report(item, decision)
    if usage is not None:
        for field in totals:
            totals[field] += getattr(usage, field)
        show_tokens("tokens:", usage)
    judged = fresh_labels(decision)
    for number in closed_issues(item):
        try:
            linked = fetch_item(number)["labels"]
            judged = inherit_from_closed(judged, item, linked)
        except SystemExit:
            # The issue may be gone, or in another repo. Not a reason
            # to give up on labelling the PR.
            print(f"  (couldn't read #{number}, ignoring the link)")
    add = judged - set(item["labels"])
    drop = stale_labels(item, decision)
    print(f"  to add:      {fmt(add)}")
    print(f"  to drop:     {fmt(drop)}")
    if not (add or drop):
        return
    if not APPLY:
        print("  (--apply to do it)")
        return
    if add:
        add_labels(item["number"], add)
    for label in sorted(drop):
        remove_label(item["number"], label)
    print("  applied")


def run_via_api(totals):
    client = make_client()
    for index, number in enumerate(NUMBERS):
        item = fetch_item(number)
        try:
            decision, usage = classify(
                client, item["title"], item["body"], item["files"]
            )
        except BadDecision as err:
            sys.exit(f"#{number}: {err}")
        handle(item, decision, usage, totals, index)


def run_via_cli(totals):
    # A chunk at a time, reported and applied as it lands, so a crash
    # halfway doesn't throw away the chunks already done.
    index = 0
    for start in range(0, len(NUMBERS), CHUNK):
        numbers = NUMBERS[start : start + CHUNK]
        items = {number: fetch_item(number) for number in numbers}
        for number, decision in classify_via_cli(items).items():
            handle(items[number], decision, None, totals, index)
            index += 1


def main():
    parse_cli()
    totals = dict.fromkeys(
        ("input_tokens", "cache_read_input_tokens", "output_tokens"), 0
    )
    if VIA_CLI:
        run_via_cli(totals)
    else:
        run_via_api(totals)
    if len(NUMBERS) > 1 and totals["output_tokens"]:
        print(
            f"\ntotal: {totals['input_tokens']} in,"
            f" {totals['cache_read_input_tokens']} cached,"
            f" {totals['output_tokens']} out"
        )


if __name__ == "__main__":
    main()
