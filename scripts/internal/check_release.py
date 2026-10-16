#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Checks that we're ready to release."""

import argparse
import json
import pathlib
import re
import shlex
import subprocess
import sys
import urllib.request

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))
from _bootstrap import get_version  # noqa: E402

TAG = None


def fail(msg):
    sys.exit(f"ERR: {msg}")


def sh(cmd):
    return subprocess.check_output(
        shlex.split(cmd), cwd=ROOT_DIR, text=True
    ).strip()


def parse_version(s):
    return tuple(int(x) for x in s.split("."))


def check_git():
    # Release from master only.
    branch = sh("git rev-parse --abbrev-ref HEAD")
    if branch != "master":
        fail(f"on branch {branch!r}, not master")
    # No uncommitted changes, untracked files are fine.
    if sh("git status --porcelain --untracked-files=no"):
        fail("there are uncommitted changes")
    # What we tag must be what's on GitHub.
    sh("git fetch -q origin master")
    if sh("git rev-parse HEAD") != sh("git rev-parse origin/master"):
        fail("HEAD is not in sync with origin/master")


def check_tag(version):
    # The pushed tag must match __version__.
    if f"v{version}" != TAG:
        fail(f"tag {TAG} doesn't match version {version}")


def check_pypi(version):
    url = "https://pypi.org/pypi/psutil/json"
    with urllib.request.urlopen(url, timeout=10) as f:
        releases = json.load(f)["releases"]
    # Not released already.
    if version in releases:
        fail(f"version {version} already exists on PyPI")
    # Higher than the latest release, so a typo can't publish an old one.
    latest = max(releases, key=parse_version)
    if parse_version(version) <= parse_version(latest):
        fail(f"version {version} is not higher than {latest} on PyPI")


def check_docs(version):
    # The changelog entry has a release date, not "(IN DEVELOPMENT)".
    text = (ROOT_DIR / "docs" / "changelog.rst").read_text(encoding="utf-8")
    pattern = rf"^{re.escape(version)} — \d{{4}}-\d{{2}}-\d{{2}}$"
    if not re.search(pattern, text, re.MULTILINE):
        fail(f"no dated {version} entry in docs/changelog.rst")
    # The timeline lists it.
    text = (ROOT_DIR / "docs" / "timeline.rst").read_text(encoding="utf-8")
    if f":pypi:`{version}`" not in text:
        fail(f"version {version} not found in docs/timeline.rst")


def parse_cli():
    global TAG
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tag", help="check this tag instead of the local git state"
    )
    args = parser.parse_args()
    TAG = args.tag


def main():
    parse_cli()
    version = get_version()
    if TAG is None:
        check_git()
    else:
        check_tag(version)
    check_pypi(version)
    check_docs(version)
    print(f"ready to release {version}")


if __name__ == "__main__":
    main()
