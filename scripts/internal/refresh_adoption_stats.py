#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola. All rights reserved.
# Use of this source code is governed by a BSD-style license that can
# be found in the LICENSE file.

"""Refresh the dynamic numbers in docs/adoption.rst and README.rst
(monthly downloads and GitHub repository dependents).

Intended to run locally before tagging a release. The docs build does
NOT call this.
"""

import json
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
TARGETS = [
    ROOT / "docs/adoption.rst",
    ROOT / "docs/index.rst",
    ROOT / "README.rst",
]
DEPENDENTS_URL = "https://github.com/giampaolo/psutil/network/dependents"
DOWNLOADS_URL = "https://pypistats.org/api/packages/psutil/recent"


def fetch(url, accept="text/html"):
    # GitHub serves a stripped page (without the dependent-counts
    # markup) to non-browser User-Agents, so we pretend to be one.
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            ),
            "Accept": accept,
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")


def round_millions(n):
    """338018876 -> '330+ million'. Floor to 10M."""
    millions = (n // 10_000_000) * 10
    return f"{millions}+ million"


def floor_to(n, bucket):
    """Floor n to a multiple of `bucket`. 769412, 10_000 -> 760000."""
    return (n // bucket) * bucket


def fetch_monthly_downloads():
    data = json.loads(fetch(DOWNLOADS_URL, accept="application/json"))
    return data["data"]["last_month"]


def fetch_github_dependents():
    """Scrape the 'Used by' repository count from GitHub's dependents
    graph.
    """
    html = fetch(DEPENDENTS_URL)
    # The page renders the count as:
    #   <number>
    #     Repositories
    # ...with the number on one line and the label on the next.
    repos_re = re.search(r"([\d,]+)\s+Repositories", html)
    if not repos_re:
        sys.exit("could not parse GitHub dependents page")
    return int(repos_re.group(1).replace(",", ""))


def main():
    print(f"fetching {DOWNLOADS_URL} ...")
    monthly = fetch_monthly_downloads()
    print(f"  monthly downloads: {monthly:,}")

    print(f"fetching {DEPENDENTS_URL} ...")
    repos = fetch_github_dependents()
    print(f"  repos:    {repos:,}")

    # Repos are at the 100k+ scale. Floor to a bucket size that hides
    # week-to-week noise but still moves visibly between releases.
    new_downloads = round_millions(monthly)  # "330+ million"
    new_repos = f"{floor_to(repos, 10_000):,}+"  # "760,000+"

    # In adoption.rst and README.rst the numbers are wrapped in
    # **bold**; in index.rst they live inside a <span class=
    # "home-stat-num">. Patterns match both forms so re-runs preserve
    # the markup.
    subs = [
        # adoption.rst / README.rst: **330+ million** downloads ...
        (
            re.compile(r"\*\*\d+\+\s+million\*\*"),
            f"**{new_downloads}**",
        ),
        (
            re.compile(r"\*\*[\d,]+\+\*\*(?=\s+`?GitHub repositories)"),
            f"**{new_repos}**",
        ),
        # index.rst home-stats banner.
        (
            re.compile(
                r'(<span class="home-stat-num">)\d+\+\s+million(</span>)'
            ),
            rf"\g<1>{new_downloads}\g<2>",
        ),
        (
            re.compile(
                r'(<span class="home-stat-num">)[\d,]+\+(</span>\s*\n\s*'
                r'<span class="home-stat-label">GitHub)'
            ),
            rf"\g<1>{new_repos}\g<2>",
        ),
    ]

    # Apply each sub to each file and count global matches per pattern.
    # Each pattern is file-specific (some only match the **bold**
    # prose form, some only match the index.rst HTML form), so we
    # only require >= 1 match across all files combined.
    totals = [0] * len(subs)
    for path in TARGETS:
        text = path.read_text()
        new_text = text
        for i, (pat, repl) in enumerate(subs):
            new_text, n = pat.subn(repl, new_text)
            totals[i] += n
        if new_text == text:
            print(f"  {path.relative_to(ROOT)}: already current")
        else:
            path.write_text(new_text)
            print(f"  {path.relative_to(ROOT)}: updated")

    for i, (pat, _) in enumerate(subs):
        if totals[i] == 0:
            sys.exit(
                f"no file matched {pat.pattern!r} "
                "(expected at least 1 match across all targets)"
            )


if __name__ == "__main__":
    main()
