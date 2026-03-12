#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

r"""Search GitHub for notable projects that use a given project
as a dependency.

Works in two stages:

1. Search (--search): discover candidate repos.
   - "readme": find Python repos mentioning PROJECT in their
     README via GitHub GraphQL API (fast, ~15 queries).
   - "depfile": enumerate all popular Python repos, then
     batch-check their dep files (pyproject.toml, setup.py,
     setup.cfg, requirements.txt, requirements/*.txt) for
     PROJECT via GraphQL (thorough, ~100 queries).

2. Filter (--filter): verify candidates.
   - "dependency": batch-fetch dependency files and check
     for an actual dependency declaration (skipped when
     --search=depfile, since it already checks dep files).
   - "null": no filtering; all candidates pass through.

Output is RsT formatted, ready to paste into docs/adoption.rst.

Usage:
    python3 scripts/internal/find_adopters.py \
        --project=psutil \
        --token=~/.github.api.key \
        --skip-file-urls=docs/adoption.rst \
        --min-stars=10000 --search=readme
"""

import argparse
import os
import re
import sys
import time

import requests

from psutil._common import hilite
from psutil._common import print_color

GITHUB_GRAPHQL = "https://api.github.com/graphql"

# Set by parse_cli().
PROJECT = ""
MIN_STARS = 0
MAX_STARS = 0
MAX_PAGES = 0
TOKEN = ""
SKIP = set()
SEARCH = ""
FILTER = ""

# Fixed files to check for dependency declarations.
_FIXED_DEP_FILES = {
    "pyproject.toml": "pyprojectToml",
    "setup.py": "setupPy",
    "setup.cfg": "setupCfg",
    "requirements.txt": "requirementsTxt",
}

# Max repos to batch in a single GraphQL query.
_BATCH_SIZE = 5


green = lambda msg: hilite(msg, color="green")  # noqa: E731
yellow = lambda msg: hilite(msg, color="yellow")  # noqa: E731
blue = lambda msg: hilite(msg, color="blue")  # noqa: E731


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
    try:
        resp = session.post(GITHUB_GRAPHQL, json=payload)
    except requests.exceptions.RequestException as err:
        stderr(f"  GraphQL request error: {err}")
        return None
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


def search_github_depfile(session):
    """Enumerate popular Python repos and check their dep files
    for PROJECT. Uses GraphQL for both repo enumeration and dep
    file fetching (no REST rate limits).

    Steps:
    1. Fetch all Python repos with >=MIN_STARS via GraphQL
       search (paginated, 100 per page).
    2. Batch-fetch dep files (pyproject.toml, setup.py, etc.)
       for all repos via GraphQL.
    3. Return only repos where PROJECT appears in a dep file.
    """
    stars_q = f"stars:>={MIN_STARS}"
    if MAX_STARS:
        stars_q = f"stars:{MIN_STARS}..{MAX_STARS}"
    search_q = f"language:Python {stars_q}"
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
    # Step 1: enumerate all matching repos.
    all_repos = []
    cursor = None
    page = 0
    while True:
        page += 1
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
            all_repos.append({
                "full_name": node["nameWithOwner"],
                "owner": node["owner"]["login"],
                "repo": node["name"],
                "stars": node["stargazerCount"],
                "description": node.get("description") or "",
                "html_url": node["url"],
                "archived": node["isArchived"],
            })
        stderr(
            f"  enum page {page}: got {len(edges)} repos "
            f"(total so far: {len(all_repos)})"
        )
        page_info = search_data["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]
        time.sleep(1)

    stderr(
        f"  enumerated {len(all_repos)} Python repos, checking dep files..."
    )

    # Step 2: batch-fetch dep files.
    all_dep_files = fetch_dep_files(session, all_repos)

    # Step 3: filter to repos that declare PROJECT.
    results = []
    for repo in all_repos:
        file_contents = all_dep_files.get(repo["full_name"], {})
        status, detail = classify_dependency(file_contents)
        if status != "no":
            repo["dep_type"] = status
            repo["dep_detail"] = detail
            results.append(repo)

    stderr(f"  found {len(results)} repos with {PROJECT} in dep files")
    return results


def _build_fixed_dep_fragment():
    """Build GraphQL fields for fetching fixed dep files
    + requirements/ dir listing.
    """
    fields = []
    for dep_file, alias in _FIXED_DEP_FILES.items():
        fields.append(
            f"    {alias}: object("
            f'expression: "HEAD:{dep_file}") {{\n'
            f"      ... on Blob {{ text }}\n"
            f"    }}"
        )
    # Also fetch the requirements/ directory listing.
    fields.append(
        "    requirementsDir: object("
        "expression: \"HEAD:requirements\") {\n"
        "      ... on Tree { entries { name } }\n"
        "    }"
    )
    return "\n".join(fields)


def _make_req_alias(filename):
    """Turn a requirements/*.txt filename into a GraphQL alias."""
    base = filename.replace(".txt", "")
    base = re.sub(r"[^a-zA-Z0-9]", "_", base)
    return f"req_{base}"


def fetch_dep_files(session, candidates):
    """Batch-fetch dependency files for a list of candidates.

    Phase 1: fetch fixed dep files + requirements/ dir listing.
    Phase 2: for repos with a requirements/ dir, fetch all *.txt
    files found there.

    Returns a dict mapping full_name to a dict of
    {dep_file: content_or_None}.
    """
    fixed_fragment = _build_fixed_dep_fragment()
    result = {}
    # Track which repos have requirements/ entries.
    req_dir_entries = {}  # full_name -> [filename, ...]

    # --- Phase 1: fixed files + dir listing ---
    total = len(candidates)
    stderr(
        "  phase 1: fixed files + requirements/ dir listing "
        f"({total} repos)..."
    )
    for start in range(0, total, _BATCH_SIZE):
        batch = candidates[start : start + _BATCH_SIZE]
        stderr(f"    batch {start + 1}-{start + len(batch)}/{total}...")
        repo_parts = []
        for i, c in enumerate(batch):
            repo_parts.append(
                f"  repo{i}: repository("
                f'owner: "{c["owner"]}", '
                f'name: "{c["repo"]}") {{\n'
                f"{fixed_fragment}\n"
                f"  }}"
            )
        query = "query {\n" + "\n".join(repo_parts) + "\n}"
        data = graphql(session, query)
        if data is None:
            for c in batch:
                result[c["full_name"]] = {}
            continue
        for i, c in enumerate(batch):
            repo_data = data.get(f"repo{i}")
            files = {}
            if repo_data:
                for dep_file, alias in _FIXED_DEP_FILES.items():
                    obj = repo_data.get(alias)
                    if obj and "text" in obj:
                        files[dep_file] = obj["text"]
                # Check for requirements/ directory.
                req_obj = repo_data.get("requirementsDir")
                if req_obj and "entries" in req_obj:
                    txt_files = [
                        e["name"]
                        for e in req_obj["entries"]
                        if e["name"].endswith(".txt")
                    ]
                    if txt_files:
                        req_dir_entries[c["full_name"]] = txt_files
            result[c["full_name"]] = files

    # --- Phase 2: fetch discovered requirements/*.txt files ---
    if req_dir_entries:
        # Collect candidates that need follow-up.
        need_fetch = [
            c for c in candidates if c["full_name"] in req_dir_entries
        ]
        stderr(
            "  phase 2: fetching requirements/*.txt from "
            f"{len(need_fetch)} repos..."
        )
        for start in range(0, len(need_fetch), _BATCH_SIZE):
            batch = need_fetch[start : start + _BATCH_SIZE]
            repo_parts = []
            for i, c in enumerate(batch):
                txt_files = req_dir_entries[c["full_name"]]
                file_fields = []
                for fname in txt_files:
                    alias = _make_req_alias(fname)
                    path = f"requirements/{fname}"
                    file_fields.append(
                        f"      {alias}: object("
                        f'expression: "HEAD:{path}") {{\n'
                        f"        ... on Blob {{ text }}\n"
                        f"      }}"
                    )
                repo_parts.append(
                    f"  repo{i}: repository("
                    f'owner: "{c["owner"]}", '
                    f'name: "{c["repo"]}") {{\n'
                    + "\n".join(file_fields)
                    + "\n  }"
                )
            query = "query {\n" + "\n".join(repo_parts) + "\n}"
            data = graphql(session, query)
            if data is None:
                continue
            for i, c in enumerate(batch):
                repo_data = data.get(f"repo{i}")
                if not repo_data:
                    continue
                txt_files = req_dir_entries[c["full_name"]]
                for fname in txt_files:
                    alias = _make_req_alias(fname)
                    obj = repo_data.get(alias)
                    if obj and "text" in obj:
                        path = f"requirements/{fname}"
                        result[c["full_name"]][path] = obj["text"]

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
    for dep_file, content in file_contents.items():
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
    global PROJECT, MIN_STARS, MAX_STARS, MAX_PAGES, TOKEN, SKIP, SEARCH, FILTER  # noqa: E501

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
        help="Repos URLs to skip (e.g. 'https://github.com/foo/bar').",
    )
    parser.add_argument(
        "--skip-file-urls",
        default=None,
        help="Path to file with GitHub repo URLs to skip (found via regex)",
    )
    parser.add_argument(
        "--search",
        required=True,
        choices=["readme", "depfile"],
        help=(
            "Search strategy: 'readme' searches for "
            "PROJECT in README (fast), 'depfile' enumerates "
            "all popular Python repos and checks their "
            "dep files (thorough, slower)."
        ),
    )
    parser.add_argument(
        "--filter",
        default="dependency",
        choices=["dependency", "null"],
        help=(
            "Filter strategy: 'dependency' checks dep "
            "files (default), 'null' accepts all candidates."
        ),
    )
    args = parser.parse_args()

    PROJECT = args.project
    MIN_STARS = args.min_stars
    MAX_STARS = args.max_stars
    MAX_PAGES = args.max_pages
    with open(os.path.expanduser(args.token)) as f:
        TOKEN = f.read().strip()
    SEARCH = args.search
    FILTER = args.filter

    SKIP = set(args.skip)
    SKIP.add("https://github.com/vinta/awesome-python")
    if args.skip_file_urls:
        path = args.skip_file_urls
        with open(path) as f:
            text = f.read()
        urls = [
            m.group(1)
            for m in re.finditer(
                r"(https://github\.com/[\w.-]+/[\w.-]+)", text
            )
        ]
        SKIP.update(urls)


def main():
    parse_cli()
    session = get_session(TOKEN)

    # --- Step 1: Search ---
    if SEARCH == "readme":
        stderr(
            "Searching GitHub for Python repos mentioning "
            f"{PROJECT} (>={MIN_STARS} stars)..."
        )
        candidates = search_github(session)
    elif SEARCH == "depfile":
        stderr(
            f"Enumerating Python repos (>={MIN_STARS} stars) "
            f"and checking dep files for {PROJECT}..."
        )
        candidates = search_github_depfile(session)
    stderr(f"Found {len(candidates)} candidates.")

    # Filter out skipped and archived repos.
    filtered = []
    for c in candidates:
        if c["html_url"] in SKIP:
            stderr(
                f"  skipping (from skip list) {yellow(c['html_url'])}",
            )
            continue
        if c["archived"]:
            stderr(
                f"  skipping {c['full_name']} (archived)",
                color="yellow",
            )
            continue
        filtered.append(c)
    candidates = filtered
    stderr(f"After filtering: {len(candidates)} candidates.")

    # --- Step 2: Filter ---
    # depfile search already checked dep files, so skip
    # redundant dep-file verification.
    if FILTER == "dependency" and SEARCH != "depfile":
        stderr("Fetching dependency files...")
        all_dep_files = fetch_dep_files(session, candidates)
        confirmed = []
        for i, c in enumerate(candidates, 1):
            stderr(
                f"  [{i}/{len(candidates)}] Checking"
                f" {blue(c['html_url'])}"
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
    else:
        confirmed = []
        for c in candidates:
            if "dep_type" not in c:
                c["dep_type"] = "direct"
                c["dep_detail"] = ""
            confirmed.append(c)

    stderr()
    stderr(f"Confirmed {len(confirmed)} projects with {PROJECT} dependency:")
    for c in confirmed:
        stderr(f"  {c['stars']:,} stars: {green(c['html_url'])}")

    # Generate RST.
    if confirmed:
        ans = input("\nGenerate RsT content? [y/N] ").strip().lower()
        if ans in {"y", "yes", "Y"}:
            rst = generate_rst(confirmed)
            print(rst)


if __name__ == "__main__":
    main()
