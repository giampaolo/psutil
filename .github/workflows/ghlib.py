# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""GitHub API helpers shared by the bot scripts in this dir.

The scripts import it as `import ghlib`, which works because Python
puts the script's own dir on sys.path.
"""

import json
import os
import urllib.error
import urllib.request

REPO = "giampaolo/psutil"
MAINTAINERS = {"giampaolo"}
TIMEOUT = 30
PER_PAGE = 100
ACCEPT_JSON = "application/vnd.github+json"

# Set by load_token().
TOKEN = ""


class GitHubError(Exception):
    def __init__(self, code, path, body):
        super().__init__(f"GitHub API {code} for {path}: {body}")
        self.code = code


def load_token(path="~/.github.api.key"):
    global TOKEN
    TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
    if not TOKEN:
        with open(os.path.expanduser(path)) as f:
            TOKEN = f.read().strip()


def request(path, post=None, method=None, accept=ACCEPT_JSON):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        data=json.dumps(post).encode() if post is not None else None,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": accept,
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read()
    except urllib.error.HTTPError as err:
        # Surface GitHub's error body; a bare "HTTP Error 404" hides it.
        body = err.read().decode("utf-8", errors="replace")
        raise GitHubError(err.code, path, body) from None
    if accept != ACCEPT_JSON:
        return data.decode("utf-8", errors="replace")
    return json.loads(data) if data else None


def request_all(path):
    items = []
    page = 1
    while True:
        batch = request(f"{path}?per_page={PER_PAGE}&page={page}")
        items.extend(batch)
        if len(batch) < PER_PAGE:
            return items
        page += 1
