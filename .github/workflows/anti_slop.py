#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Bot that closes and locks contributed PRs that break AI slop rules.

Usage:
    # dry run, nothing is written
    python3 .github/workflows/anti_slop.py 3093
    # close / label as you, with ~/.github.api.key
    python3 .github/workflows/anti_slop.py 3093 --apply
    # close / label as github-actions[bot], via triage.yml
    gh workflow run triage.yml -f numbers="3093 3094"
"""

import argparse
import datetime
import os
import re
import sys

import ghlib

LABEL = "ai-slop"

# Set by parse_cli().
NUMBERS = []
APPLY = False


def humantime(delta):
    secs = int(delta.total_seconds())
    if secs < 60:
        n, unit = secs, "second"
    elif secs < 3600:
        n, unit = secs // 60, "minute"
    elif secs < 86400:
        n, unit = secs // 3600, "hour"
    else:
        n, unit = secs // 86400, "day"
    return f"{n} {unit}" if n == 1 else f"{n} {unit}s"


# =====================================================================
# --- rules
# =====================================================================


class PRFarm:
    """Catch accounts that spam AI-generated PRs over lots of repos.
    Count the repos the author opened PRs in during the WINDOW before
    this PR, own repos included. MIN_REPOS or more looks like a farm.
    Farms also get lots of PRs rejected, so less than MAX_MERGE_RATIO
    percent of the account's closed PRs must be merged. The exception
    is accounts with MAX_FOLLOWERS or more: that's usually a known dev
    doing some cleanup across the ecosystem.
    """

    CLOSE = True
    WINDOW = datetime.timedelta(days=60)
    MIN_REPOS = 60
    MAX_MERGE_RATIO = 70
    MAX_FOLLOWERS = 300
    QUERY = """\
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    followers { totalCount }
    merged: pullRequests(states: MERGED) { totalCount }
    closed: pullRequests(states: CLOSED) { totalCount }
    contributionsCollection(from: $from, to: $to) {
      totalRepositoriesWithContributedPullRequests
    }
  }
}
"""
    REPLY = """\
## Anti AI slop bot

This PR was closed automatically, because in the {days} days before \
it this account opened PRs in {repos} repositories, and only {ratio}% \
of its closed PRs were merged. See \
https://github.com/giampaolo/psutil/blob/master/CONTRIBUTING.md#ai-policy. \
If you think this is a mistake, say so in a new issue.
"""

    def account(self, pr):
        until = datetime.datetime.fromisoformat(pr["created_at"])
        variables = {
            "login": pr["user"]["login"],
            "from": (until - self.WINDOW).isoformat(),
            "to": until.isoformat(),
        }
        user = ghlib.graphql(self.QUERY, variables)["user"]
        cc = user["contributionsCollection"]
        repos = cc["totalRepositoriesWithContributedPullRequests"]
        merged = user["merged"]["totalCount"]
        total = merged + user["closed"]["totalCount"]
        # nothing merged or closed yet: no evidence of rejections
        ratio = 100 * merged // total if total else None
        return user["followers"]["totalCount"], repos, ratio

    def check(self, pr):
        followers, repos, ratio = self.account(pr)
        print(
            f"  PRs in {repos} repos in {self.WINDOW.days} days, "
            f"{ratio}% of closed PRs merged, {followers} followers"
        )
        if (
            repos >= self.MIN_REPOS
            and ratio is not None
            and ratio < self.MAX_MERGE_RATIO
            and followers < self.MAX_FOLLOWERS
        ):
            return self.REPLY.format(
                days=self.WINDOW.days, repos=repos, ratio=ratio
            )
        return None


class IssueHunters:
    """Look for those a$$holes who subscribe to psutil tracker just to
    receive notifications when a new issue is opened, and create an
    AI-generated PR 5 minutes later for prestige.
    """

    CLOSE = True
    TOO_SOON = datetime.timedelta(hours=12)
    FIXES_RE = re.compile(
        r"\b(?:fix|fixes|fixed|close|closes|closed|resolve|resolves|"
        r"resolved):?\s+(?:https://github\.com/giampaolo/psutil/issues/|#)"
        r"(\d+)",
        re.IGNORECASE,
    )
    REPLY = """\
## Anti AI slop bot

This PR was closed automatically, because it was opened {delay} \
after #{issue}, an issue opened by someone else. See \
https://github.com/giampaolo/psutil/blob/master/CONTRIBUTING.md#ai-policy. \
If you think this is a mistake, say so on the issue.
"""

    def find_issue(self, pr):
        text = pr["title"] + "\n" + (pr["body"] or "")
        for num in self.FIXES_RE.findall(text):
            try:
                issue = ghlib.request(f"/repos/{ghlib.REPO}/issues/{num}")
            except ghlib.GitHubError as err:
                if err.code != 404:
                    raise
                print(f"  #{num} not found, skipping")
                continue
            if "pull_request" not in issue:
                return issue
        return None

    def delay(self, pr, issue):
        opened = datetime.datetime.fromisoformat(issue["created_at"])
        return datetime.datetime.fromisoformat(pr["created_at"]) - opened

    def maintainer_replied(self, issue, before):
        path = f"/repos/{ghlib.REPO}/issues/{issue['number']}/comments"
        return any(
            c["user"]["login"] in ghlib.MAINTAINERS
            and c["created_at"] < before
            for c in ghlib.request_all(path)
        )

    def is_sniped(self, pr, issue):
        # PR for an issue they opened themselves
        if issue["user"]["login"] == pr["user"]["login"]:
            return False
        if not datetime.timedelta(0) <= self.delay(pr, issue) < self.TOO_SOON:
            return False
        return not self.maintainer_replied(issue, pr["created_at"])

    def check(self, pr):
        issue = self.find_issue(pr)
        if issue and self.is_sniped(pr, issue):
            delay = humantime(self.delay(pr, issue))
            return self.REPLY.format(issue=issue["number"], delay=delay)
        return None


RULES = [PRFarm(), IssueHunters()]


# =====================================================================
# --- main
# =====================================================================


def check(pr):
    error = None
    for rule in RULES:
        try:
            reply = rule.check(pr)
        except (ghlib.GitHubError, OSError) as err:
            # try the other rules, re-raise if none of them match
            print(f"  {type(rule).__name__} failed: {err}", file=sys.stderr)
            error = err
            continue
        if reply:
            return rule, reply
    if error:
        raise error
    return None, None


def add_label(pr):
    path = f"/repos/{ghlib.REPO}/issues/{pr['number']}/labels"
    ghlib.request(path, {"labels": [LABEL]})


def close(pr, body):
    path = f"/repos/{ghlib.REPO}/issues/{pr['number']}"
    ghlib.request(f"{path}/comments", {"body": body})
    add_label(pr)
    ghlib.request(path, {"state": "closed"}, "PATCH")
    set_output("closed", "true")
    ghlib.request(f"{path}/lock", {}, "PUT")


def set_output(name, value):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            f.write(f"{name}={value}\n")


def handle(number):
    pr = ghlib.request(f"/repos/{ghlib.REPO}/issues/{number}")
    user = pr["user"]
    print(f"#{number} by {user['login']}: {pr['title']}")
    if "pull_request" not in pr:
        print("  not a PR, skipping")
        return
    if pr["state"] == "closed":
        print("  already closed, skipping")
        return
    if user["login"] in ghlib.MAINTAINERS or user["type"] == "Bot":
        print("  trusted, skipping")
        return
    rule, reply = check(pr)
    if not reply:
        print("  looks fine")
        return
    print(f"  {reply.strip()}")
    if not APPLY:
        print("  (--apply to act)")
        return
    if rule.CLOSE:
        close(pr, reply)
        print("  closed and locked")
    else:
        add_label(pr)
        print("  labelled only")


def parse_cli():
    global NUMBERS, APPLY
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("numbers", nargs="+", type=int, help="PR numbers")
    p.add_argument(
        "--apply",
        action="store_true",
        help="close or label on GitHub; without this nothing is written",
    )
    args = p.parse_args()
    ghlib.load_token()
    NUMBERS = args.numbers
    APPLY = args.apply


def main():
    parse_cli()
    for number in NUMBERS:
        handle(number)


if __name__ == "__main__":
    main()
