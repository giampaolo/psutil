#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Setup the right labels for new GitHub issues and PRs by asking Claude.

Usage:
    python3 .github/workflows/triage_labels.py 2635
    python3 .github/workflows/triage_labels.py 2635 1783 2029
    python3 .github/workflows/triage_labels.py 2635 --apply
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

REPO = "giampaolo/psutil"
HTTP_TIMEOUT = 30
MAX_BODY_CHARS = 6000
MAX_FILES = 100
MAX_TOKENS = 2048

# Set by parse_cli().
TOKEN = ""
MODEL = ""
NUMBERS = []
APPLY = False

PROMPT = """\
You are triaging a psutil issue or pull request. psutil is a Python
library that reads process and system information, with a Python layer
per platform (_pslinux.py, _pswindows.py, ...) backed by C extensions.

Type is always exactly one label. Platform, component and severity are
lists and may name more than one, though most items need a type and a
platform and nothing else. On the three lists, leave it empty rather
than reaching for a label that only half fits: a wrong label is worse
than no label.

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
  compile error on the reporter's own machine is build-fail instead.

- build-fail: psutil doesn't compile or link. A missing header, an
  undeclared constant, an undefined symbol, a compiler that chokes on
  the source. The reporter's own toolchain counts: no Python.h, no C
  compiler installed, the wrong MSVC. So does an extension that built
  but won't load for an undefined symbol. A test that fails, a compile
  warning and a wheel missing from PyPI are not this.

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

SEVERITY

Two ways a bug can be worse than a wrong answer. Usually neither
applies. Both at once is rare, but allowed.

- critical: the process doesn't survive, or its memory is no longer
  trustworthy. A segfault, a use-after-free, a double free, a buffer
  overflow, an abort. A deadlock or a hang counts too: the process is
  still there but it's never coming back.

- badexc: psutil raises something it isn't allowed to. The public API
  may raise NoSuchProcess, AccessDenied, ZombieProcess and
  TimeoutExpired, and nothing else. Anything else getting out is this:
  a RuntimeError, a SystemError, an OSError, a KeyError, an IndexError,
  a UnicodeDecodeError. FileNotFoundError and PermissionError count as
  well, being exactly what psutil should have turned into NoSuchProcess
  and AccessDenied.

  This is about the type, never the timing. One of those four raised
  when it shouldn't have been, a false NoSuchProcess on a process that
  is still alive say, is a wrong answer: a plain bug, not badexc.

  Near misses, none of them badexc: an AssertionError is a test
  failing. An ImportError or a DLL that won't load is a build that
  didn't work. An AttributeError on a name that's gone is a caller on
  an old API. NotImplementedError is how psutil says the platform
  can't answer. A warning is not an exception. ValueError and
  TypeError on a bad argument are the API working, though one escaping
  a /proc or registry parse does count.

It has to be psutil doing it: people paste whole tracebacks from
whatever program hit the problem, so find psutil in the failing frame
first. A wrong value, a slow call and a leak are plain bugs however
annoying. So is a build that won't compile, which never got as far as
running. An umbrella issue cataloguing ten crashes is about the audit,
not any one crash, but a PR that fixes several things carries all of
them: "[SunOS] various fixes" can end up with both labels.

CONFIDENCE

Give type, platform, component and severity a confidence. Use low when
the text is too thin to tell, so the choice can be discarded later. For
type, platform and component an empty answer with high confidence means
you are sure nothing applies, and is what lets a wrong label already on
the ticket be cleared. Severity is only ever added, never taken away,
so an empty one says nothing about what the ticket already carries.

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
type=bug, platform=["macos"], severity=["badexc"]. SystemError isn't
one of the four psutil is allowed to raise, so it counts however
small the fix turns out to be.

Title: "False NoSuchProcess('PID has been reused') on a process that is
still alive"
type=bug, platform=[], severity=[]. NoSuchProcess *is* one of the four.
Raising it at the wrong moment is a wrong answer, not badexc.

Title: "[Windows] win_service_iter() can segfault on enumeration
failure"
type=bug, platform=["windows"], severity=["critical"]. The process
dies. Nothing was raised, so no badexc.

Title: "[Windows] net_if_stats() reports the wrong link speed"
type=bug, platform=["windows"], severity=[]. A wrong number is a
plain bug. Nothing got out and nothing died.

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
# The axis names come from the label descriptions on GitHub.

TYPE_LABELS = ["bug", "enhancement"]
PLATFORM_LABELS = [
    "linux", "windows", "macos", "freebsd", "openbsd", "netbsd", "bsd",
    "sunos", "aix", "unix", "vm", "pypy",
]  # fmt: skip
SEVERITY_LABELS = ["critical", "badexc"]
COMPONENT_LABELS = [
    "doc", "tests", "ci", "scripts", "wheels", "new-api",
    "performance", "memleak", "compatibility", "new-platform",
    "build-fail",
]  # fmt: skip

# The model never sees these, and they're stripped before comparing.
IGNORED_LABELS = {
    "imported",
    "need-more-info",
    "dependencies",
    "github_actions",
}

AXES = ("type", "platform", "component", "severity")
LIST_AXES = ("platform", "component", "severity")
AXIS_LABELS = {
    "type": TYPE_LABELS,
    "platform": PLATFORM_LABELS,
    "component": COMPONENT_LABELS,
    "severity": SEVERITY_LABELS,
}
# severity is missing on purpose. The text can suggest it but never
# rule it out, so we add those and never take them away.
REMOVABLE_AXES = ("type", "platform", "component")


def enum_list(labels, description):
    return {
        "type": "array",
        "items": {"type": "string", "enum": labels},
        "description": description,
    }


GENERAL_PLATFORMS = {
    "bsd": {"freebsd", "openbsd", "netbsd"},
    "unix": {
        "aix",
        "bsd",
        "freebsd",
        "linux",
        "macos",
        "netbsd",
        "openbsd",
        "sunos",
    },
}


def drop_general_platforms(labels):
    """Drop unix / bsd when the same answer also names an OS."""
    out = set(labels)
    for general, specific in GENERAL_PLATFORMS.items():
        if out & specific:
            out.discard(general)
    return out


def axis_values(decision, axis):
    """What a decision puts on one axis, always as a set."""
    value = decision[axis]
    if axis in LIST_AXES:
        return set(value)
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
    "severity": enum_list(
        SEVERITY_LABELS,
        "critical when the process dies, badexc when psutil raises"
        " something it shouldn't. Usually empty.",
    ),
    "severity_confidence": CONFIDENCE,
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
        "by_bot": (raw.get("user") or {}).get("type") == "Bot",
    }
    if item["is_pr"]:
        files = gh_request(f"/repos/{REPO}/pulls/{number}/files")
        item["files"] = [f["filename"] for f in files][:MAX_FILES]
    return item


# "Fixes #123", "closes gh-123", or the full issue URL.
CLOSES = re.compile(
    r"\b(?:fix(?:e[sd])?|close[sd]?|resolve[sd]?)\b[\s:]*"
    r"(?:https?://github\.com/[\w.-]+/[\w.-]+/issues/|gh-|#)(\d+)",
    re.IGNORECASE,
)


def closed_issues(item):
    if not item["is_pr"]:
        return []
    seen = []
    for match in CLOSES.finditer(item["body"][:MAX_BODY_CHARS]):
        number = int(match.group(1))
        if number != item["number"] and number not in seen:
            seen.append(number)
    return seen


def inherit_from_closed(labels, issue_labels):
    """Take critical from the issue a PR closes.

    The issue quotes the traceback, the PR just says "handle EFAULT",
    so the same defect reads as critical on one and not the other.

    Sharing a platform is what says the PR really is the fix. "chore:
    test with Python 3.12" closes a Windows bug without being its fix
    and inherits nothing.
    """
    out = set(labels)
    ours = out & set(PLATFORM_LABELS)
    theirs = set(issue_labels) & set(PLATFORM_LABELS)
    if (ours & theirs) or not (ours or theirs):
        if "critical" in issue_labels:
            out.add("critical")
    return out


def add_labels(number, labels):
    """Add labels to a ticket. This endpoint never removes any."""
    gh_request(
        f"/repos/{REPO}/issues/{number}/labels", {"labels": sorted(labels)}
    )


def remove_label(number, label):
    path = urllib.parse.quote(label)
    gh_request(f"/repos/{REPO}/issues/{number}/labels/{path}", method="DELETE")


def fresh_labels(decision):
    """The labels a decision is willing to stand behind.

    Low means the model is guessing, so that axis contributes nothing.
    Medium still counts: a third of the corpus lands there and it's
    right most of the time.
    """
    out = set()
    for axis in AXES:
        # type has no "neither" answer, so a shaky one still beats
        # leaving the item out of the changelog entirely.
        if axis == "type" or decision[f"{axis}_confidence"] != "low":
            out |= axis_values(decision, axis)
    return drop_general_platforms(out)


def stale_labels(item, decision, from_bot=()):
    """Labels the model just contradicted on the same axis.

    Only where it was sure, since medium or low means "I can't tell"
    and that's no reason to delete what a person put there. A confident
    empty answer does count, and is the only way a wrong label ever
    gets cleared.

    from_bot is what the old regex bot applied; that comes off on
    medium too.
    """
    keep = model_labels(decision)
    out = set()
    for axis in REMOVABLE_AXES:
        conf = decision[f"{axis}_confidence"]
        if conf == "high":
            out |= {x for x in item["labels"] if x in AXIS_LABELS[axis]} - keep
        elif conf == "medium" and axis == "component":
            # The bot read components off the template's "Type:" line,
            # which reporters fill in by ticking everything. Its
            # platforms came from "[Linux]" title tags and are usually
            # right, so those stay protected.
            botted = {x for x in item["labels"] if x in AXIS_LABELS[axis]}
            out |= (botted & set(from_bot)) - keep
    return out


# --- the model


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
        # No caching. The 5 minute TTL never survives to the next
        # issue, so it only ever pays for the write.
        system=PROMPT,
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
    global TOKEN, MODEL, NUMBERS, APPLY
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("numbers", nargs="+", type=int, help="issue or PR numbers")
    p.add_argument(
        "--token",
        default="~/.github.api.key",
        help="file holding a GitHub token. GITHUB_TOKEN wins.",
    )
    p.add_argument("--model", default="claude-sonnet-5")
    p.add_argument(
        "--apply",
        action="store_true",
        help="add the labels on GitHub; without this nothing is written",
    )
    args = p.parse_args()
    TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
    if not TOKEN:
        with open(os.path.expanduser(args.token)) as f:
            TOKEN = f.read().strip()
    MODEL = args.model
    NUMBERS = args.numbers
    APPLY = args.apply


def show_tokens(prefix, usage):
    # input_tokens excludes the cache write, which is most of it.
    print(
        f"  {prefix:12s} {usage.input_tokens} in,"
        f" {usage.cache_creation_input_tokens} written,"
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
            judged = inherit_from_closed(judged, linked)
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


def run(totals):
    client = make_client()
    for index, number in enumerate(NUMBERS):
        item = fetch_item(number)
        if item["by_bot"]:
            print(f"#{number}: opened by a bot, skipping")
            continue
        try:
            decision, usage = classify(
                client, item["title"], item["body"], item["files"]
            )
        except BadDecision as err:
            sys.exit(f"#{number}: {err}")
        handle(item, decision, usage, totals, index)


def main():
    parse_cli()
    totals = dict.fromkeys(
        (
            "input_tokens",
            "cache_creation_input_tokens",
            "cache_read_input_tokens",
            "output_tokens",
        ),
        0,
    )
    run(totals)
    if len(NUMBERS) > 1 and totals["output_tokens"]:
        print(
            f"\ntotal: {totals['input_tokens']} in,"
            f" {totals['cache_creation_input_tokens']} written,"
            f" {totals['cache_read_input_tokens']} cached,"
            f" {totals['output_tokens']} out"
        )


if __name__ == "__main__":
    main()
