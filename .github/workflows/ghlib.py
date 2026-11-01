# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""GitHub API helpers shared by the bot scripts in this dir.

The scripts import it as `import ghlib`, which works because Python
puts the script's own dir on sys.path.
"""

import json
import os
import sys
import urllib.error
import urllib.request

REPO = "giampaolo/psutil"
MAINTAINERS = {"giampaolo"}
TIMEOUT = 30

# Set by load_token().
TOKEN = ""


def load_token(path="~/.github.api.key"):
    global TOKEN
    TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
    if not TOKEN:
        with open(os.path.expanduser(path)) as f:
            TOKEN = f.read().strip()


def request(path, post=None, method=None):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        data=json.dumps(post).encode() if post is not None else None,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read()
            return json.loads(data) if data else None
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        sys.exit(f"GitHub API {err.code} for {path}: {body}")
