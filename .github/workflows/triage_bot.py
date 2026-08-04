#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Bot triggered by Github Actions every time a new issue, PR or comment
is created. Replies to common mistakes and closes what it can answer on
its own. Labelling is scripts/internal/triage_labels.py's job.
"""

import functools
import json
import os
import pathlib
from pprint import pprint as pp

from github import Github

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
MAINTAINERS = {"giampaolo"}

# --- replies

REPLY_MISSING_PYTHON_HEADERS = """\
It looks like you're missing `Python.h` headers. This usually means you have \
to install them first, then retry psutil installation.
Please read \
[install](https://psutil.io/install/) \
instructions for your platform. \
This is an auto-generated response based on the text you submitted. \
If this was a mistake or you think there's a bug with psutil installation \
process, please add a comment to reopen this issue.
"""

REPLY_MAINTAINER_OWNED_FILES = """\
⚠️ Please **remove** your changes to `docs/changelog.rst` and / or \
`docs/credits.rst`. ⚠️
These two files are maintained by the project, and a \
maintainer edits them before the PR is merged. \
Editing them in a PR tends to cause merge conflicts. \
This is an auto-generated response.
"""


# --- github API utils


def is_pr(issue):
    return issue.pull_request is not None


def get_repo():
    repo = os.environ['GITHUB_REPOSITORY']
    token = os.environ['GITHUB_TOKEN']
    return Github(token).get_repo(repo)


# --- event utils


@functools.lru_cache
def _get_event_data():
    with open(os.environ["GITHUB_EVENT_PATH"]) as f:
        ret = json.load(f)
        pp(ret)
        return ret


def is_event_new_issue():
    data = _get_event_data()
    try:
        return data['action'] == 'opened' and 'issue' in data
    except KeyError:
        return False


def is_event_new_pr():
    data = _get_event_data()
    try:
        return data['action'] == 'opened' and 'pull_request' in data
    except KeyError:
        return False


def get_issue():
    data = _get_event_data()
    try:
        num = data['issue']['number']
    except KeyError:
        num = data['pull_request']['number']
    return get_repo().get_issue(number=num)


# --- actions


def log(msg):
    if '\n' in msg or "\r\n" in msg:
        print(f">>>\n{msg}\n<<<", flush=True)
    else:
        print(f">>> {msg} <<<", flush=True)


def on_new_issue(issue):
    def has_text(text):
        return text in issue.title.lower() or (
            issue.body and text in issue.body.lower()
        )

    def body_mentions_python_h():
        if not issue.body:
            return False
        body = issue.body.replace(' ', '')
        return (
            "#include<Python.h>\n^~~~" in body
            or "#include<Python.h>\r\n^~~~" in body
        )

    log("searching for missing Python.h")
    if (
        has_text("missing python.h")
        or has_text("python.h: no such file or directory")
        or body_mentions_python_h()
    ):
        log("found mention of Python.h")
        issue.create_comment(REPLY_MISSING_PYTHON_HEADERS)
        issue.edit(state='closed')
        return


def on_new_pr(issue):
    if issue.user.login in MAINTAINERS:
        return
    pr = get_repo().get_pull(issue.number)
    files = [x.filename for x in pr.get_files()]

    # changelog.rst / credits.rst are maintainer-owned; ask to drop them.
    owned = ("docs/changelog.rst", "docs/credits.rst")
    if any(f in files for f in owned):
        log("PR edits maintainer-owned changelog/credits files")
        issue.create_comment(REPLY_MAINTAINER_OWNED_FILES)


def main():
    issue = get_issue()
    stype = "PR" if is_pr(issue) else "issue"
    log(f"running issue bot for {stype} {issue!r}")

    if is_event_new_issue():
        log(f"created new issue {issue}")
        on_new_issue(issue)
    elif is_event_new_pr():
        log(f"created new PR {issue}")
        on_new_pr(issue)
    else:
        log("unhandled event")


if __name__ == '__main__':
    main()
