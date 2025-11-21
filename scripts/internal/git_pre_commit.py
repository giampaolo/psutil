#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This gets executed on 'git commit' and rejects the commit in case
the submitted code does not pass validation. Validation is run only
against the files which were modified in the commit. Install this with
"make install-git-hooks".
"""

import os
import shlex
import shutil
import subprocess
import sys

PYTHON = sys.executable
LINUX = sys.platform.startswith("linux")


def term_supports_colors():
    try:
        import curses

        assert sys.stderr.isatty()
        curses.setupterm()
        return curses.tigetnum("colors") > 0
    except Exception:  # noqa: BLE001
        return False


def hilite(s, ok=True, bold=False):
    """Return an highlighted version of 'string'."""
    if not term_supports_colors():
        return s
    attr = []
    if ok is None:  # no color
        pass
    elif ok:  # green
        attr.append("32")
    else:  # red
        attr.append("31")
    if bold:
        attr.append("1")
    return f"\x1b[{';'.join(attr)}m{s}\x1b[0m"


def exit_with(msg):
    print(hilite("Commit aborted. " + msg, ok=False), file=sys.stderr)
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
        print(stderr, file=sys.stderr)
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
    # XXX: we should escape spaces and possibly other amenities here
    new_rm_mv = sh(
        ["git", "diff", "--name-only", "--diff-filter=ADR", "--cached"]
    ).split()
    return py, c, rst, toml, new_rm_mv


def run_cmd(base_cmd, files, tool, fixer=""):
    if not files:
        return
    cmd = base_cmd + files
    if subprocess.call(cmd) != 0:
        msg = f"'{tool}' failed."
        if fixer:
            msg += f" Try running '{fixer}'."
        exit_with(msg)


def black(files):
    run_cmd(
        [PYTHON, "-m", "black", "--check", "--safe"],
        files,
        "black",
        fixer="fix-black",
    )


def ruff(files):
    run_cmd(
        [
            PYTHON,
            "-m",
            "ruff",
            "check",
            "--no-cache",
            "--output-format=concise",
        ],
        files,
        "ruff",
        fixer="fix-ruff",
    )


def clang_format(files):
    if not LINUX and not shutil.which("clang-format"):
        return print("clang-format not installed; skip lint check")
    run_cmd(
        ["clang-format", "--dry-run", "--Werror"],
        files,
        "clang-format",
        fixer="fix-c",
    )


def toml_sort(files):
    run_cmd(["toml-sort", "--check"], files, "toml-sort", fixer="fix-toml")


def rstcheck(files):
    run_cmd(["rstcheck", "--config=pyproject.toml"], files, "rstcheck")


def dprint():
    run_cmd(
        ["dprint", "check", "--list-different"],
        [],
        "dprint",
        fixer="fix-dprint",
    )


def lint_manifest():
    out = sh([PYTHON, "scripts/internal/generate_manifest.py"])
    with open("MANIFEST.in", encoding="utf8") as f:
        if out.strip() != f.read().strip():
            exit_with(
                "Some files were added, deleted or renamed. "
                "Run 'make generate-manifest' and commit again."
            )


def main():
    py, c, rst, toml, new_rm_mv = git_commit_files()

    black(py)
    ruff(py)
    clang_format(c)
    rstcheck(rst)
    toml_sort(toml)
    dprint()

    if new_rm_mv:
        lint_manifest()


if __name__ == "__main__":
    main()
