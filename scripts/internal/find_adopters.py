#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Search GitHub for notable projects that use a given project
as a dependency.

Uses the GitHub search API to find Python repositories that mention
the project in their README, then verifies each candidate by
checking its dependency files (pyproject.toml, setup.py, setup.cfg,
requirements.txt) for an actual dependency declaration.

Output is RST formatted, ready to paste into docs/adoption.rst.

Requirements:
    pip install requests

Usage:
    python3 find_adopters.py --project psutil --token ~/.github.api.key
"""

import argparse
import base64
import re
import sys
import time

import requests

from psutil._common import print_color

GITHUB_API = "https://api.github.com"

# Set by parse_cli()
PROJECT = ""
MIN_STARS = 0
MAX_STARS = 0
MAX_PAGES = 0
TOKEN = ""
SKIP = set()

# Files to check for dependency declarations.
DEP_FILES = [
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "requirements.txt",
    "requirements/base.txt",
    "requirements/main.txt",
    "requirements/install.txt",
    "requirements/production.txt",
]


def stderr(msg=""):
    print(msg, file=sys.stderr)


def get_session(token):
    s = requests.Session()
    s.headers["Accept"] = "application/vnd.github.v3+json"
    s.headers["Authorization"] = f"Bearer {token}"
    return s


def wait_for_rate_limit(session):
    """Sleep until the rate limit resets if we're close to hitting it."""
    resp = session.get(f"{GITHUB_API}/rate_limit")
    if resp.status_code == 200:
        data = resp.json()
        core = data["resources"]["core"]
        search = data["resources"]["search"]
        if search["remaining"] < 2:
            reset = search["reset"] - time.time() + 2
            if reset > 0:
                stderr(f"  search rate limit hit, sleeping {reset:.0f}s")
                time.sleep(reset)
        if core["remaining"] < 10:
            reset = core["reset"] - time.time() + 2
            if reset > 0:
                stderr(f"  core rate limit hit, sleeping {reset:.0f}s")
                time.sleep(reset)


def search_github(session):
    """Search for Python repos mentioning PROJECT in their README."""
    results = []
    stars_q = f"stars:>={MIN_STARS}"
    if MAX_STARS:
        stars_q = f"stars:{MIN_STARS}..{MAX_STARS}"
    for page in range(1, MAX_PAGES + 1):
        wait_for_rate_limit(session)
        url = (
            f"{GITHUB_API}/search/repositories"
            f"?q={PROJECT}+in:readme+language:Python"
            f"+{stars_q}"
            "&sort=stars&order=desc"
            f"&per_page=100&page={page}"
        )
        resp = session.get(url)
        if resp.status_code != 200:
            stderr(f"  search API error: {resp.status_code} {resp.text}")
            break
        data = resp.json()
        items = data.get("items", [])
        if not items:
            break
        for item in items:
            results.append({
                "full_name": item["full_name"],
                "owner": item["full_name"].split("/")[0],
                "repo": item["full_name"].split("/")[1],
                "stars": item["stargazers_count"],
                "description": item["description"] or "",
                "html_url": item["html_url"],
                "archived": item.get("archived", False),
            })
        stderr(
            f"  search page {page}: got {len(items)} results "
            f"(total so far: {len(results)})"
        )
        if len(items) < 100:
            break
        # GitHub search API requires a pause between requests.
        time.sleep(2)
    return results


def get_file_content(session, owner, repo, path):
    """Fetch a file from a GitHub repo. Returns content or None."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
    resp = session.get(url)
    if resp.status_code != 200:
        return None
    data = resp.json()
    if data.get("encoding") == "base64":
        return base64.b64decode(data["content"]).decode(
            "utf-8", errors="replace"
        )
    return None


def check_dependency(session, owner, repo):
    """Check if a repo actually depends on PROJECT.

    Returns a tuple (status, detail) where status is one of:
    - "direct"    : PROJECT in install/runtime dependencies
    - "build"     : PROJECT in build/setup dependencies only
    - "test"      : PROJECT in test/dev dependencies only
    - "optional"  : PROJECT in optional/extras dependencies
    - "no"        : not found in any dependency file
    """
    found_in = []
    pat = re.escape(PROJECT)
    for dep_file in DEP_FILES:
        wait_for_rate_limit(session)
        content = get_file_content(session, owner, repo, dep_file)
        if content is None:
            continue
        # Check if PROJECT appears in this file.
        if not re.search(r"\b" + pat + r"\b", content):
            continue
        found_in.append(dep_file)

    if not found_in:
        return "no", ""

    # Classify the dependency type based on which files it was
    # found in.
    for f in found_in:
        if f == "pyproject.toml":
            content = get_file_content(session, owner, repo, f)
            if content and re.search(
                r"\[project\].*?dependencies\s*=\s*\[.*?" + pat,
                content,
                re.DOTALL,
            ):
                return "direct", f
            if content and re.search(
                r"\[tool\.poetry\.dependencies\].*?" + pat,
                content,
                re.DOTALL,
            ):
                return "direct", f
            if content and re.search(
                r"\[build-system\].*?requires\s*=\s*\[.*?" + pat,
                content,
                re.DOTALL,
            ):
                return "build", f
            if content and r"optional-dependencies" in content:
                return "optional", f
            if content and re.search(r"test|dev", content):
                return "test", f
            return "direct", f  # default if found in pyproject.toml
        elif f == "setup.py":
            content = get_file_content(session, owner, repo, f)
            if content and re.search(
                r"install_requires.*?" + pat, content, re.DOTALL
            ):
                return "direct", f
            if content and re.search(
                r"setup_requires.*?" + pat, content, re.DOTALL
            ):
                return "build", f
            if content and re.search(
                r"tests_require.*?" + pat, content, re.DOTALL
            ):
                return "test", f
            if content and re.search(
                r"extras_require.*?" + pat, content, re.DOTALL
            ):
                return "optional", f
            return "direct", f
        elif f == "setup.cfg":
            content = get_file_content(session, owner, repo, f)
            if content and re.search(
                r"install_requires.*?" + pat, content, re.DOTALL
            ):
                return "direct", f
            if content and re.search(
                r"extras_require.*?" + pat, content, re.DOTALL
            ):
                return "optional", f
            return "direct", f
        elif "requirements" in f:
            return "direct", f

    return "direct", ", ".join(found_in)


def make_subst_name(full_name):
    """Turn 'owner/repo' into a substitution-safe base name."""
    name = full_name.split("/")[1]
    # Replace underscores and dots with hyphens.
    name = re.sub(r"[_.]", "-", name)
    return name.lower()


def tier_label(stars):
    if stars >= 40000:
        return 1
    elif stars >= 10000:
        return 2
    else:
        return 3


def generate_rst(projects):
    """Generate RST output for adoption.rst."""
    tiers = {1: [], 2: [], 3: []}
    for p in projects:
        t = tier_label(p["stars"])
        tiers[t].append(p)

    lines = []
    star_badges = []
    logo_images = []

    tier_headers = {
        1: "Tier 1 (>40k GitHub stars)",
        2: "Tier 2 (10k-40k GitHub stars)",
        3: "Tier 3 (1k-10k GitHub stars)",
    }

    for tier_num in (1, 2, 3):
        tier_projects = sorted(tiers[tier_num], key=lambda x: -x["stars"])
        if not tier_projects:
            continue

        header = tier_headers[tier_num]
        lines.append(header)
        lines.append("-" * len(header))
        lines.append("")
        lines.append(".. list-table::")
        lines.append("   :header-rows: 1")
        lines.append("   :widths: 18 42 12 28")
        lines.append("")
        lines.append("   * - Project")
        lines.append("     - Description")
        lines.append("     - Stars")
        lines.append("     - Usage")

        for p in tier_projects:
            name = make_subst_name(p["full_name"])
            owner = p["owner"]
            repo = p["repo"]
            full = p["full_name"]
            desc = p["description"]
            # Truncate description to fit RST table.
            if len(desc) > 60:
                desc = desc[:57] + "..."
            dep_type = p.get("dep_type", "")
            usage = ""
            if dep_type == "build":
                usage = "build-time dependency"
            elif dep_type == "test":
                usage = "test dependency"
            elif dep_type == "optional":
                usage = "optional dependency"

            proj_link = f"|{name}-logo| `{repo} <https://github.com/{full}>`__"
            lines.append(f"   * - {proj_link}")
            lines.append(f"     - {desc}")
            lines.append(f"     - |{name}-stars|")
            lines.append(f"     - {usage}")

            star_badges.append(
                f".. |{name}-stars| image:: "
                "https://img.shields.io/github/stars/"
                f"{full}.svg?style=plastic"
            )

            logo_images.append(
                f".. |{name}-logo| image:: https://github.com/{owner}.png?s=28"
                " :height: 28"
            )

        lines.append("")

    # Combine everything.
    output = []
    output.extend(lines)
    output.extend([
        "",
        ".. Star badges",
        "",
    ])
    output.extend(star_badges)
    output.extend([
        "",
        ".. Logo images",
        "",
    ])
    output.extend(logo_images)
    return "\n".join(output)


def parse_cli():
    """Parse CLI arguments and set global constants."""
    global PROJECT, MIN_STARS, MAX_STARS, MAX_PAGES, TOKEN, SKIP

    parser = argparse.ArgumentParser(
        description=(
            "Find notable GitHub projects using a given "
            "project as a dependency."
        )
    )
    parser.add_argument(
        "--project",
        required=True,
        help="Project name to search for (e.g. 'psutil').",
    )
    parser.add_argument(
        "--min-stars",
        type=int,
        default=300,
        help="Minimum GitHub stars to consider (default: 300).",
    )
    parser.add_argument(
        "--max-stars",
        type=int,
        default=0,
        help="Maximum GitHub stars to consider (default: no limit).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=5,
        help="Max search result pages to fetch (default: 5).",
    )
    parser.add_argument(
        "--token",
        required=True,
        help="Path to a file containing the GitHub token.",
    )
    parser.add_argument(
        "--skip",
        nargs="*",
        default=[],
        help="Repos to skip (e.g. 'owner/repo').",
    )
    args = parser.parse_args()

    PROJECT = args.project
    MIN_STARS = args.min_stars
    MAX_STARS = args.max_stars
    MAX_PAGES = args.max_pages
    with open(args.token) as f:
        TOKEN = f.read().strip()
    SKIP = set(args.skip)
    SKIP.add("vinta/awesome-python")


def main():
    parse_cli()
    session = get_session(TOKEN)

    stderr(
        f"Searching GitHub for Python repos mentioning {PROJECT} "
        f"(>={MIN_STARS} stars)..."
    )
    candidates = search_github(session)
    stderr(f"Found {len(candidates)} candidates.")

    # Filter out skipped repos.
    candidates = [c for c in candidates if c["full_name"] not in SKIP]
    stderr(f"After filtering: {len(candidates)} candidates.")

    # Verify each candidate.
    confirmed = []
    for i, c in enumerate(candidates, 1):
        owner = c["owner"]
        repo = c["repo"]
        stderr(
            f"  [{i}/{len(candidates)}] Checking"
            f" https://github.com/{c['full_name']} ({c['stars']} stars)..."
        )
        if c["archived"]:
            print_color(
                "    -> archived, skipping", color="yellow", file=sys.stderr
            )
            continue
        status, detail = check_dependency(session, owner, repo)
        if status != "no":
            c["dep_type"] = status
            c["dep_detail"] = detail
            confirmed.append(c)
            print_color(
                f"    -> {status} dependency (via {detail})",
                color="green",
                file=sys.stderr,
            )
        else:
            print_color(
                "    -> not a dependency, skipping",
                color="yellow",
                file=sys.stderr,
            )

    stderr()
    stderr(f"Confirmed {len(confirmed)} projects with {PROJECT} dependency.")

    # Generate RST.
    rst = generate_rst(confirmed)
    print(rst)


if __name__ == "__main__":
    main()
