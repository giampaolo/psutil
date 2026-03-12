#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Search GitHub for notable projects that use a given project
as a dependency.

Uses the GitHub GraphQL API to find Python repositories that
mention the project in their README, then verifies each candidate
by batch-fetching its dependency files (pyproject.toml, setup.py,
setup.cfg, requirements.txt) for an actual dependency declaration.

Output is RsT formatted, ready to paste into docs/adoption.rst.

Usage:
    python3 find_adopters.py --project psutil --token ~/.github.api.key
"""

import argparse
import re
import sys
import time

import requests

from psutil._common import print_color

GITHUB_GRAPHQL = "https://api.github.com/graphql"

# Set by parse_cli().
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

# GraphQL alias names for each dep file (must be valid
# identifiers).
_DEP_FILE_ALIASES = {
    "pyproject.toml": "pyprojectToml",
    "setup.py": "setupPy",
    "setup.cfg": "setupCfg",
    "requirements.txt": "requirementsTxt",
    "requirements/base.txt": "requirementsBase",
    "requirements/main.txt": "requirementsMain",
    "requirements/install.txt": "requirementsInstall",
    "requirements/production.txt": "requirementsProduction",
}

# Max repos to batch in a single GraphQL query.
_BATCH_SIZE = 10


def stderr(msg="", color=None):
    if color:
        print_color(msg, color=color, file=sys.stderr)
    else:
        print(msg, file=sys.stderr)


def graphql(session, query, variables=None):
    """Execute a GraphQL query. Returns the 'data' dict."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = session.post(GITHUB_GRAPHQL, json=payload)
    if resp.status_code != 200:
        stderr(f"  GraphQL HTTP error: {resp.status_code} {resp.text}")
        return None
    body = resp.json()
    if "errors" in body:
        for err in body["errors"]:
            stderr(f"  GraphQL error: {err.get('message', err)}")
        return None
    return body.get("data")


def get_session(token):
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {token}"
    s.headers["Content-Type"] = "application/json"
    return s


def search_github(session):
    """Search for Python repos mentioning PROJECT in README."""
    stars_q = f"stars:>={MIN_STARS}"
    if MAX_STARS:
        stars_q = f"stars:{MIN_STARS}..{MAX_STARS}"
    search_q = f"{PROJECT} in:readme language:Python {stars_q}"
    query = """
    query($q: String!, $first: Int!, $after: String) {
      search(query: $q, type: REPOSITORY,
             first: $first, after: $after) {
        repositoryCount
        edges {
          node {
            ... on Repository {
              nameWithOwner
              owner { login }
              name
              url
              description
              stargazerCount
              isArchived
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """
    results = []
    cursor = None
    for page in range(1, MAX_PAGES + 1):
        variables = {
            "q": search_q,
            "first": 100,
            "after": cursor,
        }
        data = graphql(session, query, variables)
        if data is None:
            break
        search_data = data["search"]
        edges = search_data["edges"]
        if not edges:
            break
        for edge in edges:
            node = edge["node"]
            if not node:
                continue
            results.append({
                "full_name": node["nameWithOwner"],
                "owner": node["owner"]["login"],
                "repo": node["name"],
                "stars": node["stargazerCount"],
                "description": node.get("description") or "",
                "html_url": node["url"],
                "archived": node["isArchived"],
            })
        stderr(
            f"  search page {page}: got {len(edges)} results "
            f"(total so far: {len(results)})"
        )
        page_info = search_data["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]
        time.sleep(1)
    return results


def _build_dep_files_fragment():
    """Build GraphQL fields for fetching all dep files."""
    fields = []
    for dep_file, alias in _DEP_FILE_ALIASES.items():
        fields.append(
            f"    {alias}: object("
            f'expression: "HEAD:{dep_file}") {{\n'
            f"      ... on Blob {{ text }}\n"
            f"    }}"
        )
    return "\n".join(fields)


def fetch_dep_files(session, candidates):
    """Batch-fetch dependency files for a list of candidates.

    Returns a dict mapping full_name to a dict of
    {dep_file: content_or_None}.
    """
    dep_fragment = _build_dep_files_fragment()
    result = {}
    for start in range(0, len(candidates), _BATCH_SIZE):
        batch = candidates[start : start + _BATCH_SIZE]
        repo_parts = []
        for i, c in enumerate(batch):
            repo_parts.append(
                f"  repo{i}: repository("
                f'owner: "{c["owner"]}", '
                f'name: "{c["repo"]}") {{\n'
                f"{dep_fragment}\n"
                f"  }}"
            )
        query = "query {\n" + "\n".join(repo_parts) + "\n}"
        data = graphql(session, query)
        if data is None:
            for c in batch:
                result[c["full_name"]] = dict.fromkeys(DEP_FILES)
            continue
        for i, c in enumerate(batch):
            repo_data = data.get(f"repo{i}")
            files = {}
            if repo_data:
                for dep_file, alias in _DEP_FILE_ALIASES.items():
                    obj = repo_data.get(alias)
                    if obj and "text" in obj:
                        files[dep_file] = obj["text"]
                    else:
                        files[dep_file] = None
            else:
                for dep_file in DEP_FILES:
                    files[dep_file] = None
            result[c["full_name"]] = files
    return result


def classify_dependency(file_contents):
    """Classify the dependency type from fetched file contents.

    Returns a tuple (status, detail) where status is one of:
    - "direct"    : PROJECT in install/runtime dependencies
    - "build"     : PROJECT in build/setup dependencies only
    - "test"      : PROJECT in test/dev dependencies only
    - "optional"  : PROJECT in optional/extras dependencies
    - "no"        : not found in any dependency file
    """
    pat = re.escape(PROJECT)
    found_in = []
    for dep_file in DEP_FILES:
        content = file_contents.get(dep_file)
        if content is None:
            continue
        if not re.search(r"\b" + pat + r"\b", content):
            continue
        found_in.append(dep_file)

    if not found_in:
        return "no", ""

    # Classify the dependency type based on which files it was
    # found in.
    for f in found_in:
        content = file_contents[f]
        if f == "pyproject.toml":
            if re.search(
                r"\[project\].*?dependencies\s*=\s*\[.*?" + pat,
                content,
                re.DOTALL,
            ):
                return "direct", f
            if re.search(
                r"\[tool\.poetry\.dependencies\].*?" + pat,
                content,
                re.DOTALL,
            ):
                return "direct", f
            if re.search(
                r"\[build-system\].*?requires\s*=\s*\[.*?" + pat,
                content,
                re.DOTALL,
            ):
                return "build", f
            if r"optional-dependencies" in content:
                return "optional", f
            if re.search(r"test|dev", content):
                return "test", f
            return "direct", f
        elif f == "setup.py":
            if re.search(r"install_requires.*?" + pat, content, re.DOTALL):
                return "direct", f
            if re.search(r"setup_requires.*?" + pat, content, re.DOTALL):
                return "build", f
            if re.search(r"tests_require.*?" + pat, content, re.DOTALL):
                return "test", f
            if re.search(r"extras_require.*?" + pat, content, re.DOTALL):
                return "optional", f
            return "direct", f
        elif f == "setup.cfg":
            if re.search(r"install_requires.*?" + pat, content, re.DOTALL):
                return "direct", f
            if re.search(r"extras_require.*?" + pat, content, re.DOTALL):
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
                f".. |{name}-logo| image:: "
                f"https://github.com/{owner}.png?s=28"
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

    # Filter out skipped and archived repos.
    filtered = []
    for c in candidates:
        if c["full_name"] in SKIP:
            continue
        if c["archived"]:
            stderr(f"  skipping {c['full_name']} (archived)")
            continue
        filtered.append(c)
    candidates = filtered
    stderr(f"After filtering: {len(candidates)} candidates.")

    # Batch-fetch dependency files for all candidates.
    stderr("Fetching dependency files...")
    all_dep_files = fetch_dep_files(session, candidates)

    # Verify each candidate.
    confirmed = []
    for i, c in enumerate(candidates, 1):
        stderr(
            f"  [{i}/{len(candidates)}] Checking"
            f" https://github.com/{c['full_name']}"
            f" ({c['stars']} stars)..."
        )
        file_contents = all_dep_files.get(c["full_name"], {})
        status, detail = classify_dependency(file_contents)
        if status != "no":
            c["dep_type"] = status
            c["dep_detail"] = detail
            confirmed.append(c)
            stderr(
                f"    -> {status} dependency (via {detail})",
                color="green",
            )
        else:
            stderr(
                "    -> not a dependency, skipping",
                color="yellow",
            )

    stderr()
    stderr(f"Confirmed {len(confirmed)} projects with {PROJECT} dependency.")

    # Generate RST.
    rst = generate_rst(confirmed)
    print(rst)


if __name__ == "__main__":
    main()
