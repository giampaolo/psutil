#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Setup the right labels for GitHub issues and PRs by asking Claude.

Usage:
    python3 scripts/internal/triage_labels.py 2635
    python3 scripts/internal/triage_labels.py 2635 1783 2029
    python3 scripts/internal/triage_labels.py 2635 --apply
"""

import argparse
import json
import os
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

Assign at most ONE label per axis, except platform, which is a list
and may name more than one OS. Most items need a nature and a platform
and nothing else. Leave an axis null, or the list empty, rather than
reaching for a label that only half fits: a wrong label is worse than
no label.

NATURE

- bug: something is broken, wrong, or crashes.
- enhancement: something new, faster, or improved.

Almost every item is one or the other. Leave it null only for
questions, discussions and tracking issues that propose no change.

PLATFORM

Fill this only when the item is specific to some OS. A bug that would
happen anywhere is an empty list, even when the reporter happens to be
on Linux.

A "[Linux]" tag in the title or a filled-in "* OS: ..." line is the
reporter saying it outright, so take them at their word. When they
name two or three, list all of them.

- linux, windows, macos, freebsd, openbsd, netbsd, sunos, aix, cygwin,
  wsl: the item is about that OS.
- bsd: almost never. Only when the item is about the BSDs as a family
  and names none of them. If FreeBSD, OpenBSD or NetBSD appears
  anywhere in the report, list those instead.
- unix: shared POSIX code affecting several unices, where no single OS
  fits.

AREA

Usually null. Roughly half of all items are just a platform bug with no
area at all. Use it when the item is fundamentally *about* one of
these, not when it merely touches one.

- doc: documentation, docstrings, README, the doc build.
- tests: the test suite itself. A test asserting the wrong thing, a
  missing test, a test helper.
- ci: the infrastructure that runs the tests. Workflow files, runner
  and matrix configuration, cirrus, appveyor, travis, a job failing for
  reasons unrelated to the code under test.
- scripts: files under scripts/, including the example scripts.
- wheels: building, publishing or installing wheels; manylinux;
  packaging.
- new-api: proposes a public function, method or field that does not
  exist yet. Much commoner than api; prefer it when both seem to fit.
- api: changes the shape or behaviour of something already public, as
  a deliberate design change rather than a bug fix.
- performance: speed or resource usage is the point. Slow is
  performance, wrong is a bug, and an optimisation is usually
  enhancement and performance at once.
- memleak: memory grows without bound.
- compatibility: breakage against a Python version, an OS version, or
  another library.
- new-platform: support for an operating system psutil does not target
  yet.

ENVIRONMENT

Null unless a container or virtual machine is material to the report,
not merely where the reporter happened to run.

- docker: specifically Docker.
- vm: any other container or virtualised environment.

CRITICAL

True only for a segfault, a crash of the interpreter, memory
corruption, or a failure that leaves psutil unusable. Not for ordinary
wrong values or exceptions.

CONFIDENCE

Give nature, platform, area and critical a confidence. Use low when
the text is too thin to tell, so the choice can be discarded later. A
null label with high confidence means you are sure nothing applies.

EXAMPLES

Title: "Process.memory_info() returns 0 for all processes on Windows 11"
nature=bug, platform=["windows"], area=null. A plain platform bug,
which is the most common shape. No area label applies.

Title: "add Process.num_threads() to the AIX implementation"
nature=enhancement, platform=["aix"], area=new-api.

Title: "test_disk_partitions fails on the macOS runner since the image
bump"
nature=bug, platform=["macos"], area=ci. The suite is fine; the runner
image changed. Not tests.

Title: "test_cpu_percent asserts the wrong bound"
nature=bug, platform=[], area=tests. The test code is wrong, and it
is wrong everywhere.

Title: "cpu_times() is 3x slower than it needs to be"
nature=enhancement, area=performance.

Title: "[OpenBSD, NetBSD] build failed"
nature=bug, platform=["openbsd", "netbsd"]. Both named, so both go in.
Not bsd.

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

NATURE_LABELS = ["bug", "enhancement"]
PLATFORM_LABELS = [
    "linux", "windows", "macos", "freebsd", "openbsd", "netbsd", "bsd",
    "sunos", "aix", "cygwin", "wsl", "unix",
]  # fmt: skip
AREA_LABELS = [
    "doc", "tests", "ci", "scripts", "wheels", "new-api", "api",
    "performance", "memleak", "compatibility", "new-platform",
]  # fmt: skip
ENV_LABELS = ["docker", "vm"]

# Bot workflow state and dependabot's own labels. The model never sees
# these and they're stripped before any comparison.
IGNORED_LABELS = {
    "imported",
    "need-more-info",
    "dependencies",
    "github_actions",
}

AXES = ("nature", "platform", "area", "environment")
# Axes holding a list instead of a single value. An item can be about
# more than one OS, and plenty of them are.
LIST_AXES = ("platform",)
AXIS_LABELS = {
    "nature": NATURE_LABELS,
    "platform": PLATFORM_LABELS,
    "area": AREA_LABELS,
    "environment": ENV_LABELS,
}
# Axes we'll drop a stale label from. Only the ones carrying a
# confidence, so there's something to gate the removal on.
REMOVABLE_AXES = ("nature", "platform", "area")


def nullable_enum(labels, description):
    # Under strict mode a nullable enum has to be spelled as anyOf.
    # "type": ["string", "null"] with None in the enum is rejected.
    return {
        "anyOf": [{"type": "string", "enum": labels}, {"type": "null"}],
        "description": description,
    }


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
    return {value} if value else set()


CONFIDENCE = {"type": "string", "enum": ["high", "medium", "low"]}

DECISION_PROPS = {
    "nature": nullable_enum(NATURE_LABELS, "bug, enhancement, or null."),
    "nature_confidence": CONFIDENCE,
    "platform": enum_list(
        PLATFORM_LABELS, "Every OS the item is specific to. Often empty."
    ),
    "platform_confidence": CONFIDENCE,
    "area": nullable_enum(AREA_LABELS, "What the item is about, else null."),
    "area_confidence": CONFIDENCE,
    "environment": nullable_enum(
        ENV_LABELS, "Container or VM, when material. Else null."
    ),
    "critical": {
        "type": "boolean",
        "description": "Crash, segfault or corruption.",
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


def add_labels(number, labels):
    """Add labels to a ticket. This endpoint never removes any."""
    gh_request(
        f"/repos/{REPO}/issues/{number}/labels", {"labels": sorted(labels)}
    )


def remove_label(number, label):
    path = urllib.parse.quote(label)
    gh_request(f"/repos/{REPO}/issues/{number}/labels/{path}", method="DELETE")


def stale_labels(item, decision):
    """Labels the model just contradicted on the same axis.

    Only where it committed to an answer and was sure of it. A null or
    a medium/low confidence means "I can't tell", which is not a reason
    to delete what a human put there.
    """
    keep = model_labels(decision)
    out = set()
    for axis in REMOVABLE_AXES:
        if not decision[axis] or decision[f"{axis}_confidence"] != "high":
            continue
        out |= {x for x in item["labels"] if x in AXIS_LABELS[axis]} - keep
    if (
        "critical" in item["labels"]
        and not decision["critical"]
        and decision["critical_confidence"] == "high"
    ):
        out.add("critical")
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


def model_labels(decision):
    """Flatten a decision into the label set it implies."""
    out = set()
    for axis in AXES:
        out |= axis_values(decision, axis)
    # docker is a kind of vm; every docker issue in the repo carries
    # both, so the hierarchy lives here rather than in the prompt.
    if decision["environment"] == "docker":
        out.add("vm")
    # critical is an escalation and the model wavers on it, so it only
    # goes on when it says so outright.
    if decision["critical"] and decision["critical_confidence"] == "high":
        out.add("critical")
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
    print(
        f"  {'critical':12s} {decision['critical']}"
        f"  ({decision['critical_confidence']})"
    )
    print(f"  already has: {fmt(set(item['labels']) - IGNORED_LABELS)}")


def parse_cli():
    global TOKEN, MODEL, NUMBERS, APPLY
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("numbers", nargs="+", type=int, help="issue or PR numbers")
    p.add_argument(
        "--token",
        default="~/.github.api.key",
        help="file holding a GitHub token",
    )
    p.add_argument("--model", default="claude-haiku-4-5-20251001")
    p.add_argument(
        "--apply",
        action="store_true",
        help="add the labels on GitHub; without this nothing is written",
    )
    args = p.parse_args()
    with open(os.path.expanduser(args.token)) as f:
        TOKEN = f.read().strip()
    MODEL = args.model
    NUMBERS = args.numbers
    APPLY = args.apply


def show_tokens(prefix, usage):
    print(
        f"  {prefix:12s} {usage.input_tokens} in,"
        f" {usage.cache_read_input_tokens} cached,"
        f" {usage.output_tokens} out"
    )


def main():
    parse_cli()
    client = make_client()
    totals = dict.fromkeys(
        ("input_tokens", "cache_read_input_tokens", "output_tokens"), 0
    )
    for n, number in enumerate(NUMBERS):
        item = fetch_item(number)
        try:
            decision, usage = classify(
                client, item["title"], item["body"], item["files"]
            )
        except BadDecision as err:
            sys.exit(f"#{number}: {err}")
        for field in totals:
            totals[field] += getattr(usage, field)
        if n:
            print()
        report(item, decision)
        show_tokens("tokens:", usage)
        add = model_labels(decision) - set(item["labels"])
        drop = stale_labels(item, decision)
        print(f"  to add:      {fmt(add)}")
        print(f"  to drop:     {fmt(drop)}")
        if not (add or drop):
            continue
        if not APPLY:
            print("  (--apply to do it)")
            continue
        if add:
            add_labels(number, add)
        for label in sorted(drop):
            remove_label(number, label)
        print("  applied")
    if len(NUMBERS) > 1:
        print(
            f"\ntotal: {totals['input_tokens']} in,"
            f" {totals['cache_read_input_tokens']} cached,"
            f" {totals['output_tokens']} out"
        )


if __name__ == "__main__":
    main()
