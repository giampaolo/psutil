#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import venv

SITE_DIR = None
ONLY = None

ROOT = pathlib.Path(__file__).resolve().parents[3]
VERSIONS_JSON = ROOT / "docs" / "versions.json"
FONT_DIRS = ("_static/fonts", "_static/css/fonts")
LEGACY_FONTS = ("*.ttf", "*.eot", "*.svg", "*.woff")
DROP = ("blog", "_sources", "_images/social_previews", ".doctrees")


def run(cmd, cwd=None):
    print("+ " + " ".join(str(c) for c in cmd))
    subprocess.check_call(cmd, cwd=cwd)


def load_versions():
    data = json.loads(VERSIONS_JSON.read_text(encoding="utf-8"))
    entries = [
        entry
        for group in data["groups"]
        for entry in group["entries"]
        if entry.get("ref")
    ]
    return data["current"], entries


def banner(entry, current, root):
    return (
        f'<link rel="stylesheet" href="{root}_static/css/archived.css">'
        '<div class="psutil-archived">You are reading the documentation '
        f'for psutil <b>{entry["name"]}</b>. '
        f'The current version is <a href="{root}">{current}</a>.</div>'
    )


def inject(html_dir, entry, current):
    count = 0
    for path in sorted(html_dir.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        if "</head>" not in text:
            sys.stderr.write(f"warning: no </head> in {path}\n")
            continue
        depth = len(path.relative_to(html_dir).parts)
        root = "../" * depth
        snippet = banner(entry, current, root)
        path.write_text(
            text.replace("</head>", snippet + "</head>", 1), encoding="utf-8"
        )
        count += 1
    return count


def trim(html_dir):
    for rel in DROP:
        target = html_dir / rel
        if target.is_dir():
            shutil.rmtree(target)
    for rel in FONT_DIRS:
        font_dir = html_dir / rel
        if not font_dir.is_dir():
            continue
        for pattern in LEGACY_FONTS:
            for path in font_dir.rglob(pattern):
                path.unlink()


def build_one(entry, current, site_dir):
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="psutil-docs-"))
    worktree = tmp / "src"
    try:
        run(
            ["git", "worktree", "add", "--detach", worktree, entry["ref"]],
            cwd=ROOT,
        )
        env = tmp / "venv"
        venv.create(env, with_pip=True)
        python = env / "bin" / "python"
        run([
            python,
            "-m",
            "pip",
            "install",
            "--quiet",
            "-r",
            worktree / "docs" / "requirements.txt",
        ])
        run(["make", "html", f"PYTHON={python}"], cwd=worktree / "docs")
        html_dir = worktree / "docs" / "_build" / "html"
        pages = inject(html_dir, entry, current)
        trim(html_dir)
        dst = site_dir / entry["url"].strip("/")
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(html_dir, dst)
        size = sum(p.stat().st_size for p in dst.rglob("*") if p.is_file())
        print(f"  {entry['name']}: {pages} pages, {size / 1048576:.1f} MB")
    finally:
        subprocess.call(
            ["git", "worktree", "remove", "--force", worktree], cwd=ROOT
        )
        shutil.rmtree(tmp, ignore_errors=True)


def parse_cli():
    global SITE_DIR, ONLY
    parser = argparse.ArgumentParser(
        description="Build past doc releases into a built site."
    )
    parser.add_argument("site", help="built HTML dir, e.g. docs/_build/html")
    parser.add_argument(
        "--only", default=None, help="build just this version name"
    )
    args = parser.parse_args()
    SITE_DIR = pathlib.Path(args.site).resolve()
    ONLY = args.only


def main():
    parse_cli()
    if not SITE_DIR.is_dir():
        sys.exit(f"error: {SITE_DIR} does not exist; run `make html` first")
    current, entries = load_versions()
    if ONLY:
        entries = [e for e in entries if e["name"] == ONLY]
        if not entries:
            sys.exit(f"error: no version named {ONLY!r} with a ref")
    if not entries:
        print("no past versions to build")
        return
    for entry in entries:
        print(f"building {entry['name']} from {entry['ref']}")
        build_one(entry, current, SITE_DIR)


if __name__ == "__main__":
    main()
