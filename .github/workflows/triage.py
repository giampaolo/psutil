#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Bot triggered by Github Actions every time a new issue or PR is
created. Replies to common mistakes. Labelling is
.github/workflows/triage_labels.py's job.
"""

import functools
import json
import os
from pprint import pprint as pp

import ghlib

# --- replies

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
    return "pull_request" in issue


# --- event utils


@functools.lru_cache
def _get_event_data():
    with open(os.environ["GITHUB_EVENT_PATH"]) as f:
        ret = json.load(f)
        pp(ret)
        return ret


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
    return ghlib.request(f"/repos/{ghlib.REPO}/issues/{num}")


# --- actions


def log(msg):
    if '\n' in msg or "\r\n" in msg:
        print(f">>>\n{msg}\n<<<", flush=True)
    else:
        print(f">>> {msg} <<<", flush=True)


def on_new_pr(issue):
    if issue["user"]["login"] in ghlib.MAINTAINERS:
        return
    path = f"/repos/{ghlib.REPO}/pulls/{issue['number']}/files"
    files = [x["filename"] for x in ghlib.request_all(path)]

    # changelog.rst / credits.rst are maintainer-owned; ask to drop them.
    owned = ("docs/changelog.rst", "docs/credits.rst")
    if any(f in files for f in owned):
        log("PR edits maintainer-owned changelog/credits files")
        path = f"/repos/{ghlib.REPO}/issues/{issue['number']}/comments"
        ghlib.request(path, {"body": REPLY_MAINTAINER_OWNED_FILES})


def main():
    ghlib.load_token()
    issue = get_issue()
    stype = "PR" if is_pr(issue) else "issue"
    log(f"running issue bot for {stype} #{issue['number']}")

    if is_event_new_pr():
        log(f"created new PR #{issue['number']}")
        on_new_pr(issue)
    else:
        log("unhandled event")


if __name__ == '__main__':
    main()
