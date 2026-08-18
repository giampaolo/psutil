#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This gets executed on 'git commit' and rejects the commit in case
the submitted code does not pass validation. Validation is run only
against the files which were modified in the commit.
"""

import os
import pathlib
import shlex
import subprocess
import sys

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
from _bootstrap import load_module  # noqa: E402

_common = load_module(ROOT_DIR / "psutil" / "_common.py")
hilite = _common.hilite

PYTHON = sys.executable


def log(msg="", color=None, bold=None):
    msg = "Git pre-commit > " + msg
    if msg:
        msg = hilite(msg, color=color, bold=bold, force_color=True)
    print(msg, flush=True)


def exit_with(msg):
    log(msg + " Commit aborted.", color="red")
    sys.exit(1)


def sh(cmd):
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        raise RuntimeError(stderr)
    if stderr:
        log(stderr)
    return stdout.rstrip()


def git_commit_files():
    out = [
        f
        for f in sh(["git", "diff", "--cached", "--name-only"]).splitlines()
        if os.path.exists(f)
    ]

    py = [f for f in out if f.endswith(".py")]
    c = [f for f in out if f.endswith((".c", ".h"))]
    rst = [f for f in out if f.endswith(".rst")]
    toml = [f for f in out if f.endswith(".toml")]
    new_rm_mv = sh(
        ["git", "diff", "--name-only", "--diff-filter=ADR", "--cached"]
    ).split()
    return py, c, rst, toml, new_rm_mv


def lint_manifest():
    out = sh([PYTHON, "scripts/internal/generate_manifest.py"])
    with open("MANIFEST.in", encoding="utf8") as f:
        if out.strip() != f.read().strip():
            exit_with(
                "Some files were added, deleted or renamed. "
                "Run 'make generate-manifest' and commit again."
            )


def run_make(target, files):
    ls = ", ".join([os.path.basename(x) for x in files])
    plural = "s" if len(files) > 1 else ""
    msg = f"Running 'make {target}' against {len(files)} file{plural}: {ls}"
    log(msg, color="lightblue")
    files = "FILES=" + " ".join(shlex.quote(f) for f in files)
    if subprocess.call(["make", target, files]) != 0:
        exit_with(f"'make {target}' failed.")


def main():
    py, c, rst, toml, new_rm_mv = git_commit_files()
    if py:
        run_make("black", py)
        run_make("ruff", py)
    if c:
        run_make("lint-c", c)
    if rst:
        run_make("lint-rst", rst)
    if toml:
        run_make("lint-toml", toml)
    if new_rm_mv:
        lint_manifest()


if __name__ == "__main__":
    main()
