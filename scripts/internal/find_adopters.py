#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

r"""Search GitHub for notable projects that use a given project
as a dependency.

How it works:

1. Enumerate all popular Python repos on GitHub via GraphQL
   (paginated, >=MIN_STARS).
2. Batch-fetch data needed for the requested filters
   (README content, dependency files).
3. Apply filters. Only repos passing ALL specified filters
   are confirmed. Available filters:
   - --inreadme : PROJECT mentioned in the README
   - --indeps   : PROJECT mentioned in dep files
     (pyproject.toml, setup.py, setup.cfg, requirements*.txt)

At least one filter must be specified.

Output is RsT formatted, ready to paste into docs/adoption.rst.

Usage:
    python3 scripts/internal/find_adopters.py \
        --project=psutil \
        --token=~/.github.api.key \
        --skip-file-urls=docs/adoption.rst \
        --min-stars=10000 --indeps
"""

import argparse
import os
import pickle
import re
import sys
import time

import requests

from psutil._common import hilite
from psutil._common import print_color

GITHUB_GRAPHQL = "https://api.github.com/graphql"
_CACHE_FILE = ".find_adopters.cache"

# Set by parse_cli().
PROJECT = ""
MIN_STARS = 0
MAX_STARS = 0
TOKEN = ""
SKIP = set()
INREADME = False
INDEPS = False
NO_CACHE = False

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


# --- Enumerate repos ---


def enumerate_repos(session):
    """Enumerate all Python repos with >=MIN_STARS on GitHub."""
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
    results = []
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
            f"  page {page}: got {len(edges)} repos "
            f"(total so far: {len(results)})"
        )
        page_info = search_data["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]
        time.sleep(1)
    return results


# --- Fetch README ---


def fetch_readmes(session, repos):
    """Batch-fetch README content for a list of repos.

    Returns a dict mapping full_name to README text
    (or empty string if not found).
    """
    result = {}
    total = len(repos)
    stderr(f"  fetching READMEs ({total} repos)...")
    for start in range(0, total, _BATCH_SIZE):
        batch = repos[start : start + _BATCH_SIZE]
        stderr(f"    batch {start + 1}-{start + len(batch)}/{total}...")
        repo_parts = []
        for i, c in enumerate(batch):
            # Try both README.md and README.rst.
            repo_parts.append(
                f"  repo{i}: repository("
                f'owner: "{c["owner"]}", '
                f'name: "{c["repo"]}") {{\n'
                f"    readmeMd: object("
                f'expression: "HEAD:README.md") {{\n'
                f"      ... on Blob {{ text }}\n"
                f"    }}\n"
                f"    readmeRst: object("
                f'expression: "HEAD:README.rst") {{\n'
                f"      ... on Blob {{ text }}\n"
                f"    }}\n"
                f"  }}"
            )
        query = "query {\n" + "\n".join(repo_parts) + "\n}"
        data = graphql(session, query)
        if data is None:
            for c in batch:
                result[c["full_name"]] = ""
            continue
        for i, c in enumerate(batch):
            repo_data = data.get(f"repo{i}")
            text = ""
            if repo_data:
                for key in ("readmeMd", "readmeRst"):
                    obj = repo_data.get(key)
                    if obj and "text" in obj:
                        text = obj["text"]
                        break
            result[c["full_name"]] = text
    return result


# --- Fetch dep files ---


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


def fetch_dep_files(session, repos):
    """Batch-fetch dependency files for a list of repos.

    Phase 1: fetch fixed dep files + requirements/ dir listing.
    Phase 2: for repos with a requirements/ dir, fetch all *.txt
    files found there.

    Returns a dict mapping full_name to a dict of
    {dep_file: content}.
    """
    fixed_fragment = _build_fixed_dep_fragment()
    result = {}
    # Track which repos have requirements/ entries.
    req_dir_entries = {}  # full_name -> [filename, ...]

    # --- Phase 1: fixed files + dir listing ---
    total = len(repos)
    stderr(
        "  phase 1: fixed files + requirements/ dir listing "
        f"({total} repos)..."
    )
    for start in range(0, total, _BATCH_SIZE):
        batch = repos[start : start + _BATCH_SIZE]
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
        # Collect repos that need follow-up.
        need_fetch = [c for c in repos if c["full_name"] in req_dir_entries]
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


# --- Classify ---


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


# --- Misc ---


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
                f"https://github.com/{owner}.png?s=28 :height: 28"
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


# --- Cache ---


def load_cache():
    """Load cached data from disk.

    Returns a dict with keys: min_stars, repos, readmes, dep_files.
    Returns None if cache is missing, stale, or --no-cache is set.
    The cache is invalidated if the current MIN_STARS is lower
    than the min_stars used to build the cache (we'd be missing
    repos).
    """
    if NO_CACHE:
        return None
    if not os.path.exists(_CACHE_FILE):
        return None
    try:
        with open(_CACHE_FILE, "rb") as f:
            data = pickle.load(f)
    except (OSError, pickle.UnpicklingError, EOFError) as err:
        stderr(f"  cache load error: {err}")
        return None
    cached_min_stars = data.get("min_stars", 0)
    if cached_min_stars > MIN_STARS:
        stderr(
            f"  cache built with min_stars={cached_min_stars}, "
            f"but current min_stars={MIN_STARS}; ignoring cache"
        )
        return None
    stderr(
        f"  loaded cache ({len(data.get('repos', []))} repos, "
        f"min_stars={cached_min_stars})"
    )
    return data


def save_cache(repos, readmes, dep_files):
    """Save fetched data to disk."""
    data = {
        "min_stars": MIN_STARS,
        "repos": repos,
        "readmes": readmes,
        "dep_files": dep_files,
    }
    with open(_CACHE_FILE, "wb") as f:
        pickle.dump(data, f)
    stderr(f"  saved cache to {_CACHE_FILE}")


# --- CLI ---


def parse_cli():
    """Parse CLI arguments and set global constants."""
    global PROJECT, MIN_STARS, MAX_STARS, TOKEN, SKIP, INREADME, INDEPS, NO_CACHE  # noqa: E501

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
        help="Maximum GitHub stars (default: no limit).",
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
        help="Repos URLs to skip.",
    )
    parser.add_argument(
        "--skip-file-urls",
        default=None,
        help="Path to file with GitHub repo URLs to skip (found via regex).",
    )
    parser.add_argument(
        "--inreadme",
        action="store_true",
        default=False,
        help="Filter: PROJECT must be mentioned in README.",
    )
    parser.add_argument(
        "--indeps",
        action="store_true",
        default=False,
        help=(
            "Filter: PROJECT must be mentioned in dep files "
            "(pyproject.toml, setup.py, setup.cfg, "
            "requirements*.txt)."
        ),
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        default=False,
        help="Force fresh fetch, ignoring cached data.",
    )
    args = parser.parse_args()

    if not args.inreadme and not args.indeps:
        parser.error("at least one of --inreadme, --indeps is required")

    PROJECT = args.project
    MIN_STARS = args.min_stars
    MAX_STARS = args.max_stars
    with open(os.path.expanduser(args.token)) as f:
        TOKEN = f.read().strip()
    INREADME = args.inreadme
    INDEPS = args.indeps

    SKIP = set(args.skip)
    SKIP.add("https://github.com/vinta/awesome-python")
    NO_CACHE = args.no_cache
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


# --- Main ---


def main():
    parse_cli()
    session = get_session(TOKEN)

    cached = load_cache()
    if cached is not None:
        repos = cached["repos"]
        readmes = cached.get("readmes", {})
        dep_files = cached.get("dep_files", {})
        need_save = False
    else:
        repos = None
        readmes = {}
        dep_files = {}
        need_save = True

    # Step 1: enumerate all popular Python repos.
    if repos is None:
        stderr(f"Enumerating Python repos (>={MIN_STARS} stars)...")
        repos = enumerate_repos(session)
        stderr(f"Found {len(repos)} repos.")

    # Filter out skipped and archived repos.
    filtered = []
    for repo in repos:
        if repo["html_url"] in SKIP:
            print(f"skipping {yellow(repo['html_url'])}")
            continue
        if repo["archived"]:
            print(f"skipping {yellow(repo['html_url'])}")
            continue
        filtered.append(repo)
    active_repos = filtered
    stderr(f"After skip/archive filtering: {len(active_repos)} repos.")

    # Step 2: fetch data needed for the requested filters.
    # Only fetch what's missing from cache.
    if INREADME and not readmes:
        stderr("Fetching READMEs...")
        readmes = fetch_readmes(session, active_repos)
        need_save = True
    if INDEPS and not dep_files:
        stderr("Fetching dependency files...")
        dep_files = fetch_dep_files(session, active_repos)
        need_save = True

    if need_save:
        save_cache(repos, readmes, dep_files)

    # Step 3: apply filters.
    confirmed = []
    for repo in active_repos:
        name = repo["full_name"]
        pat = re.escape(PROJECT)

        if INREADME:
            readme = readmes.get(name, "")
            if not re.search(r"\b" + pat + r"\b", readme):
                continue

        if INDEPS:
            files = dep_files.get(name, {})
            status, detail = classify_dependency(files)
            if status == "no":
                continue
            repo["dep_type"] = status
            repo["dep_detail"] = detail

        confirmed.append(repo)

    stderr()
    stderr(f"Confirmed {len(confirmed)} projects:")
    for c in confirmed:
        stderr(f"  {c['stars']:,} stars: {green(c['html_url'])}")

    # Generate RST.
    if confirmed:
        ans = input("\nGenerate RsT content? [y/N] ").strip().lower()
        if ans in {"y", "yes"}:
            rst = generate_rst(confirmed)
            print(rst)


if __name__ == "__main__":
    main()
