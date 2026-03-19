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
import urllib.request

import anthropic

# CLI args
PR_NUMBER = None
REPO = None
TOKEN = None

CHANGELOG_FILE = "docs/changelog.rst"
CREDITS_FILE = "docs/credits.rst"
MAX_DIFF_CHARS = 20_000
MAX_TOKENS = 1024

PROMPT = """\
You are helping maintain the official changelog for psutil, a Python
system monitoring library.

Your task is to generate ONE changelog entry describing the user-visible
change introduced by a pull request. Do not generate more than one entry.

PR #{number}: {title}
Author: @{author} (full name: {author_name})

Description:
{body}

Diff:
{diff}

ISSUE NUMBER SELECTION

The changelog should reference the GitHub ISSUE number when one exists,
not the pull request number.

Determine the correct issue number using these rules:

1. If the PR title or description references an issue such as:
   - "Fixes #1234"
   - "Closes #1234"
   - "Refs #1234"
   - "#1234"
   then use that number.

2. If multiple issues are referenced, choose the primary one most
   closely related to the change.

3. If no issue reference exists, fall back to the PR number.

The chosen number will be used in the :gh:`...` role.

STYLE

- Write concise entries (1-2 sentences max).
- Focus on the user-visible behavior change.
- Avoid implementation details unless relevant.
- Prefer imperative verbs: "fix", "add", "improve", "avoid", "detect".
- Do not repeat the PR title verbatim.
- Do not mention "PR" in the text.
- Wrap lines around ~79 characters.

CLASSIFICATION

Classify the change into one of:

Bug fixes
Enhancements

Bug fixes include:
- crashes
- incorrect behavior
- race conditions
- compilation failures
- incorrect return values
- memory leaks
- platform regressions

Enhancements include:
- new features
- performance improvements
- better detection
- improved error handling
- new platform support
- packaging improvements (e.g. wheels)

PLATFORM TAGS

If the change is platform specific, add tags immediately after the issue
reference.

Examples:

:gh:`1234`, [Linux]:
:gh:`1234`, [Windows]:
:gh:`1234`, [macOS], [BSD]:

Only add platform tags if the change clearly affects specific OSes.

RST FORMATTING

Use Sphinx roles for psutil APIs:

Functions:
:func:`function_name`

Methods:
:meth:`Class.method`

Classes:
:class:`ClassName`

Exceptions:
:exc:`ExceptionName`

C functions or identifiers must use double backticks:

``function_name()``

FORMAT

Each entry must follow this structure:

- :gh:`ISSUE_NUMBER`: <description>.

Or with platforms:

- :gh:`ISSUE_NUMBER`, [Linux]: <description>.

DESCRIPTION GUIDELINES

- Describe the user-visible change.
- Mention affected psutil APIs when applicable.
- Avoid mentioning internal helper functions.
- If fixing incorrect behavior, describe the previous issue.
- If fixing a crash or compilation error, state it clearly.

EXAMPLES

- :gh:`2708`, [macOS]: :meth:`Process.cmdline()` and
  :meth:`Process.environ()` may fail with ``OSError: [Errno 0]``.
  They now raise :exc:`AccessDenied` instead.

- :gh:`2674`, [Windows]: :func:`disk_usage()` could truncate values on
  32-bit systems for drives larger than 4GB.

- :gh:`2705`, [Linux]: :meth:`Process.wait()` now uses
  ``pidfd_open()`` + ``poll()`` for waiting, avoiding busy loops
  and improving response times.

CREDITS

psutil maintains a list of contributors in docs/credits.rst under
"Code contributors by year".

Generate a credits entry unless the author is @giampaolo, in which
case set credits_entry to null.

Use the contributor's full name from their GitHub profile ({author_name})
unless it is not set, in which case fall back to their username (@{author}).

The format used in docs/credits.rst is:

* `Name or username`_ - :gh:`ISSUE_NUMBER`

Examples:

* `Sergey Fedorov`_ - :gh:`2701`
* `someuser`_ - :gh:`2710`

Use the same issue number used in the changelog entry.
"""

SUBMIT_TOOL = {
    "name": "submit",
    "description": "Submit the changelog and credits entries.",
    "input_schema": {
        "type": "object",
        "properties": {
            "section": {
                "type": "string",
                "enum": ["Bug fixes", "Enhancements"],
            },
            "changelog_entry": {
                "type": "string",
                "description": "The RST changelog entry.",
            },
            "credits_entry": {
                "type": ["string", "null"],
                "description": (
                    "The RST credits line, or null if author is @giampaolo."
                ),
            },
        },
        "required": ["section", "changelog_entry", "credits_entry"],
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
    with urllib.request.urlopen(req) as resp:
        return resp.read()


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
    }


def fetch_pr_diff():
    return gh_request(
        f"/repos/{REPO}/pulls/{PR_NUMBER}",
        accept="application/vnd.github.v3.diff",
    ).decode("utf-8", errors="replace")


def ask_claude(pr, diff):
    prompt = PROMPT.format(
        number=pr["number"],
        title=pr["title"],
        author=pr["author"],
        author_name=pr["author_name"],
        body=pr["body"],
        diff=diff[:MAX_DIFF_CHARS],
    )
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=MAX_TOKENS,
        tools=[SUBMIT_TOOL],
        tool_choice={"type": "tool", "name": "submit"},
        messages=[{"role": "user", "content": prompt}],
    )
    tool_use = next(b for b in message.content if b.type == "tool_use")
    return tool_use.input


def insert_changelog_entry(section, entry):
    with open(CHANGELOG_FILE) as f:
        lines = f.readlines()

    version_re = re.compile(r"^(\d+\.\d+\.\d+|X\.X\.X).*$")
    version_idx = next(
        (i for i, ln in enumerate(lines) if version_re.match(ln.rstrip())),
        None,
    )
    if version_idx is None:
        sys.exit(f"Could not find version block in {CHANGELOG_FILE}")
    next_version_idx = next(
        (
            i
            for i in range(version_idx + 1, len(lines))
            if version_re.match(lines[i].rstrip())
        ),
        len(lines),
    )
    block = lines[version_idx:next_version_idx]

    # Skip if this issue is already referenced in the version block
    gh_ref = re.search(r":gh:`\d+`", entry)
    if gh_ref and any(gh_ref.group(0) in ln for ln in block):
        print(
            f"Changelog entry for {gh_ref.group(0)} already exists, skipping"
        )
        return

    header = f"**{section}**"
    header_idx = next(
        (i for i, ln in enumerate(block) if ln.rstrip() == header), None
    )

    def _entry_gh_number(line):
        """Extract the ticket number from a :gh:`N` reference."""
        m = re.search(r":gh:`(\d+)`", line)
        return int(m.group(1)) if m else None

    new_entry_num = _entry_gh_number(entry)

    if header_idx is None:
        insert_at = next(
            (
                i
                for i, ln in enumerate(block)
                if ln.startswith("**") and ln.rstrip() != header
            ),
            len(block),
        )
        new_block = (
            block[:insert_at]
            + [f"{header}\n", "\n", f"{entry}\n", "\n"]
            + block[insert_at:]
        )
    else:
        # Find the end of this section (next ** header or end of block).
        section_end = next(
            (
                i
                for i in range(header_idx + 1, len(block))
                if block[i].startswith("**")
            ),
            len(block),
        )
        # Skip the blank line after the header.
        first_entry = header_idx + 1
        if first_entry < len(block) and not block[first_entry].strip():
            first_entry += 1
        # Find the right position sorted by ticket number.
        insert_at = section_end
        if new_entry_num is not None:
            for i in range(first_entry, section_end):
                num = _entry_gh_number(block[i])
                if num is not None and num > new_entry_num:
                    insert_at = i
                    break
        else:
            insert_at = first_entry
        new_block = block[:insert_at] + [f"{entry}\n"] + block[insert_at:]

    lines[version_idx:next_version_idx] = new_block
    with open(CHANGELOG_FILE, "w") as f:
        f.writelines(lines)


def update_credits(credits_entry, author, author_name):
    """Insert credits entry and link definition into CREDITS_FILE."""
    with open(CREDITS_FILE) as f:
        lines = f.readlines()

    year = str(datetime.date.today().year)
    year_re = re.compile(r"^\d{4}$")

    def sort_key(e):
        m = re.match(r"\*\s+`([^`]+)`_", e.strip())
        return m.group(1).lower() if m else e.strip().lower()

    # Insert year entry
    section_idx = next(
        (
            i
            for i, ln in enumerate(lines)
            if ln.rstrip() == "Code contributors by year"
        ),
        None,
    )
    if section_idx is None:
        sys.exit(
            f"Could not find 'Code contributors by year' in {CREDITS_FILE}"
        )

    year_idx = next(
        (
            i
            for i in range(section_idx, len(lines))
            if lines[i].rstrip() == year
        ),
        None,
    )
    if year_idx is None:
        first_year = next(
            (
                i
                for i in range(section_idx, len(lines))
                if year_re.match(lines[i].rstrip())
            ),
            len(lines),
        )
        lines[first_year:first_year] = [
            f"{year}\n",
            "~" * len(year) + "\n",
            "\n",
            f"{credits_entry}\n",
            "\n",
        ]
    else:
        year_end = next(
            (
                i
                for i in range(year_idx + 2, len(lines))
                if year_re.match(lines[i].rstrip())
            ),
            len(lines),
        )
        new_key = sort_key(credits_entry)
        insert_idx = year_end
        skip = False
        for i in range(year_idx + 2, year_end):
            if lines[i].startswith("* "):
                k = sort_key(lines[i])
                if k == new_key:
                    print(
                        f"Credits entry for {new_key!r} already exists,"
                        " skipping"
                    )
                    skip = True
                    break
                if k > new_key:
                    insert_idx = i
                    break
        if not skip:
            # Don't back up past the blank line after the year
            # underline (year_idx + 2 = "~~~~\n", + 3 = first
            # content line).
            min_idx = year_idx + 3
            while insert_idx > min_idx and not lines[insert_idx - 1].strip():
                insert_idx -= 1
            lines.insert(insert_idx, f"{credits_entry}\n")

    # Insert link definition if missing
    target = f".. _`{author_name}`:"
    if not any(ln.startswith(target) for ln in lines):
        link_section = next(
            (
                i
                for i, ln in enumerate(lines)
                if ln.rstrip() == ".. Code contributors"
            ),
            None,
        )
        if link_section is None:
            sys.exit(
                "Could not find code contributors link section in"
                f" {CREDITS_FILE}"
            )
        definition = f".. _`{author_name}`: https://github.com/{author}\n"
        insert_idx = len(lines)
        for i in range(link_section, len(lines)):
            m = re.match(r"\.\. _`([^`]+)`:", lines[i])
            if m and m.group(1).lower() > author_name.lower():
                insert_idx = i
                break
        lines.insert(insert_idx, definition)

    with open(CREDITS_FILE, "w") as f:
        f.writelines(lines)


def post_comment(body):
    url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"
    data = json.dumps({"body": body}).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req):
        pass


def parse_cli():
    global PR_NUMBER, REPO, TOKEN
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pr-number", type=int, required=True)
    p.add_argument(
        "--repo", type=str, required=True, help="e.g. giampaolo/psutil"
    )
    p.add_argument("--token", type=str, required=True, help="GitHub token")
    args = p.parse_args()
    PR_NUMBER = args.pr_number
    REPO = args.repo
    TOKEN = args.token


def main():
    parse_cli()
    print(f"Fetching PR #{PR_NUMBER} from {REPO}...")
    pr = fetch_pr_metadata()
    diff = fetch_pr_diff()
    print("Asking Claude for changelog entry...")
    result = ask_claude(pr, diff)
    section = result["section"]
    changelog_entry = result["changelog_entry"]
    credits_entry = result["credits_entry"]
    print(f"Section: {section}")
    print(f"Entry:   {changelog_entry}")
    insert_changelog_entry(section, changelog_entry)
    print(f"Inserted entry into {CHANGELOG_FILE}")
    comment = (
        f"`{CHANGELOG_FILE}` entry added under **{section}**:\n\n"
        f"```rst\n{changelog_entry}\n```"
    )
    if credits_entry:
        print(f"Credits: {credits_entry}")
        update_credits(credits_entry, pr["author"], pr["author_name"])
        print(f"Updated {CREDITS_FILE}")
        comment += (
            f"\n\n`{CREDITS_FILE}` entry added:\n\n"
            f"```rst\n{credits_entry}\n```"
        )
    post_comment(comment)
    print("Posted confirmation comment on PR")


if __name__ == "__main__":
    main()
