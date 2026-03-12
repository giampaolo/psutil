#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Search GitHub for notable projects that use psutil as a dependency.

Uses the GitHub search API to find Python repositories that mention
"psutil" in their README, then verifies each candidate by checking
its dependency files (pyproject.toml, setup.py, setup.cfg,
requirements.txt) for an actual psutil dependency declaration.

Output is RST formatted, ready to paste into docs/adoption.rst.

Requirements:
    pip install requests

Usage:
    python3 find_adopters.py --token /path/to/token/file
"""

import argparse
import base64
import re
import sys
import time

try:
    import requests
except ImportError:
    print(
        "error: 'requests' package is required: pip install requests",
        file=sys.stderr,
    )
    sys.exit(1)


GITHUB_API = "https://api.github.com"
# Files to check for psutil dependency declarations.
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
# Patterns that indicate psutil is a real dependency (not just a
# comment or a mention in a string).
PSUTIL_PATTERNS = [
    re.compile(r'^\s*["\']?psutil', re.MULTILINE),
    re.compile(r"install_requires\s*=.*psutil", re.DOTALL),
    re.compile(r"setup_requires\s*=.*psutil", re.DOTALL),
    re.compile(r"dependencies\s*=\s*\[.*psutil", re.DOTALL),
]


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
                print(
                    f"  search rate limit hit, sleeping {reset:.0f}s",
                    file=sys.stderr,
                )
                time.sleep(reset)
        if core["remaining"] < 10:
            reset = core["reset"] - time.time() + 2
            if reset > 0:
                print(
                    f"  core rate limit hit, sleeping {reset:.0f}s",
                    file=sys.stderr,
                )
                time.sleep(reset)


def search_github(session, min_stars=1000, max_pages=5):
    """Search for Python repos mentioning psutil in their README."""
    results = []
    for page in range(1, max_pages + 1):
        wait_for_rate_limit(session)
        url = (
            f"{GITHUB_API}/search/repositories"
            "?q=psutil+in:readme+language:Python"
            f"+stars:>={min_stars}"
            "&sort=stars&order=desc"
            f"&per_page=100&page={page}"
        )
        resp = session.get(url)
        if resp.status_code != 200:
            print(
                f"  search API error: {resp.status_code} {resp.text}",
                file=sys.stderr,
            )
            break
        data = resp.json()
        items = data.get("items", [])
        if not items:
            break
        for item in items:
            results.append({  # noqa: PERF401
                "full_name": item["full_name"],
                "owner": item["full_name"].split("/")[0],
                "repo": item["full_name"].split("/")[1],
                "stars": item["stargazers_count"],
                "description": item["description"] or "",
                "html_url": item["html_url"],
            })
        print(
            f"  search page {page}: got {len(items)} results "
            f"(total so far: {len(results)})",
            file=sys.stderr,
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
    """Check if a repo actually depends on psutil.

    Returns a tuple (status, detail) where status is one of:
    - "direct"    : psutil in install/runtime dependencies
    - "build"     : psutil in build/setup dependencies only
    - "test"      : psutil in test/dev dependencies only
    - "optional"  : psutil in optional/extras dependencies
    - "no"        : not found in any dependency file
    """
    found_in = []
    for dep_file in DEP_FILES:
        wait_for_rate_limit(session)
        content = get_file_content(session, owner, repo, dep_file)
        if content is None:
            continue
        # Check if psutil appears in this file.
        if not re.search(r"\bpsutil\b", content):
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
                r"\[project\].*?dependencies\s*=\s*\[.*?psutil",
                content,
                re.DOTALL,
            ):
                return "direct", f
            if content and re.search(
                r"\[tool\.poetry\.dependencies\].*?psutil", content, re.DOTALL
            ):
                return "direct", f
            if content and re.search(
                r"\[build-system\].*?requires\s*=\s*\[.*?psutil",
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
                r"install_requires.*?psutil", content, re.DOTALL
            ):
                return "direct", f
            if content and re.search(
                r"setup_requires.*?psutil", content, re.DOTALL
            ):
                return "build", f
            if content and re.search(
                r"tests_require.*?psutil", content, re.DOTALL
            ):
                return "test", f
            if content and re.search(
                r"extras_require.*?psutil", content, re.DOTALL
            ):
                return "optional", f
            return "direct", f
        elif f == "setup.cfg":
            content = get_file_content(session, owner, repo, f)
            if content and re.search(
                r"install_requires.*?psutil", content, re.DOTALL
            ):
                return "direct", f
            if content and re.search(
                r"extras_require.*?psutil", content, re.DOTALL
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
        lines.append("     - psutil usage")

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
            star_badges.append(f"   :target: https://github.com/{full}")

            logo_images.append(
                f".. |{name}-logo| image:: https://github.com/{owner}.png?s=28"
            )
            logo_images.append("   :height: 28")
            logo_images.append(f"   :target: https://github.com/{full}")

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


def main():
    parser = argparse.ArgumentParser(
        description="Find notable GitHub projects using psutil."
    )
    parser.add_argument(
        "--min-stars",
        type=int,
        default=300,
        help="Minimum GitHub stars to consider (default: 300).",
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
        help="Repos to skip (e.g. 'giampaolo/psutil').",
    )
    args = parser.parse_args()

    with open(args.token) as f:
        token = f.read().strip()
    session = get_session(token)

    # Always skip psutil itself and meta-lists.
    skip = set(args.skip)
    skip.add("giampaolo/psutil")
    skip.add("vinta/awesome-python")

    print(
        "Searching GitHub for Python repos mentioning psutil "
        f"(>={args.min_stars} stars)...",
        file=sys.stderr,
    )
    candidates = search_github(
        session, min_stars=args.min_stars, max_pages=args.max_pages
    )
    print(f"Found {len(candidates)} candidates.", file=sys.stderr)

    # Filter out skipped repos.
    candidates = [c for c in candidates if c["full_name"] not in skip]
    print(
        f"After filtering: {len(candidates)} candidates.",
        file=sys.stderr,
    )

    # Verify each candidate.
    confirmed = []
    for i, c in enumerate(candidates, 1):
        owner = c["owner"]
        repo = c["repo"]
        print(
            f"  [{i}/{len(candidates)}] Checking {c['full_name']} "
            f"({c['stars']} stars)...",
            file=sys.stderr,
        )
        status, detail = check_dependency(session, owner, repo)
        if status != "no":
            c["dep_type"] = status
            c["dep_detail"] = detail
            confirmed.append(c)
            print(
                f"    -> {status} dependency (via {detail})",
                file=sys.stderr,
            )
        else:
            print("    -> not a dependency, skipping", file=sys.stderr)

    print(file=sys.stderr)
    print(
        f"Confirmed {len(confirmed)} projects with psutil dependency.",
        file=sys.stderr,
    )

    # Generate RST.
    rst = generate_rst(confirmed)
    print(rst)


if __name__ == "__main__":
    main()
