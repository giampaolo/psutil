#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Print PYPI statistics in MarkDown format.
Useful sites:
* https://pepy.tech/project/psutil
* https://pypistats.org/packages/psutil
* https://hugovk.github.io/top-pypi-packages/.
"""

import argparse
import collections
import datetime
import functools
import json
import os
import re
import shlex
import subprocess
import sys
import urllib.request

AUTH_FILE = os.path.expanduser("~/.pypinfo.json")
PKGNAME = 'psutil'
DAYS = 30
# pypinfo defaults to 10 rows, which would turn "%" into a share of the
# top 10. Raising it is free: BigQuery scans the same bytes either way.
LIMIT = 100
# pypinfo's own --all means "every installer, not just pip". Without it
# we'd miss the ~46% of downloads that come from uv.
PYPINFO = f"pypinfo --json --all --days {DAYS} --limit"
PYPISTATS_URL = "https://pypistats.org/api/packages/{}/{}"
TOP_PACKAGES_URL = (
    "https://hugovk.dev/top-pypi-packages/top-pypi-packages.min.json"
)
GITHUB_SCRIPT_URL = (
    "https://github.com/giampaolo/psutil/blob/master/"
    "scripts/internal/print_downloads.py"
)
LAST_UPDATE = None
bytes_billed = 0

# CLI args
ALL = False


def parse_cli():
    global ALL
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="print more info via BigQuery (expensive)",
    )
    args = parser.parse_args()
    ALL = args.all


# --- get (free: no credentials, no quota)


@functools.lru_cache
def pypistats(kind):
    """Return a {category: downloads} Counter for the last DAYS days.
    Mirror traffic is excluded.
    """
    global LAST_UPDATE
    url = PYPISTATS_URL.format(PKGNAME, kind)
    with urllib.request.urlopen(url, timeout=30) as resp:
        rows = json.load(resp)["data"]
    LAST_UPDATE = max(x["date"] for x in rows)
    start = datetime.date.fromisoformat(LAST_UPDATE) - datetime.timedelta(
        days=DAYS - 1
    )
    totals = collections.Counter()
    for row in rows:
        if datetime.date.fromisoformat(row["date"]) >= start:
            totals[row["category"]] += row["downloads"]
    return totals


def downloads():
    return sum(pypistats("python_minor").values())


def downloads_pyver():
    return pypistats("python_minor")


def downloads_by_system():
    return pypistats("system")


def ranking():
    with urllib.request.urlopen(TOP_PACKAGES_URL, timeout=60) as resp:
        rows = json.load(resp)["rows"]
    for i, row in enumerate(rows, start=1):
        if row["project"] == PKGNAME:
            return i
    raise ValueError(f"can't find {PKGNAME} in {TOP_PACKAGES_URL}")


# --- get (BigQuery, --all only)
#
# Everything below costs money. Sizes were measured with `pypinfo -n`.


@functools.lru_cache
def sh(cmd):
    assert os.path.exists(AUTH_FILE)
    env = os.environ.copy()
    env['GOOGLE_APPLICATION_CREDENTIALS'] = AUTH_FILE
    p = subprocess.Popen(
        shlex.split(cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        env=env,
    )
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        raise RuntimeError(stderr)
    assert not stderr, stderr
    return stdout.strip()


@functools.lru_cache
def query(cmd):
    global bytes_billed
    import pypinfo  # noqa: F401

    ret = json.loads(sh(cmd))
    bytes_billed += ret['query']['bytes_billed']
    return ret


def downloads_by_distro():
    # EXPENSIVE: ~11 GB scanned per call.
    return query(f"{PYPINFO} {LIMIT} {PKGNAME} distro")


def downloads_by_wheel():
    """Group downloads by the kind of file fetched. Only way to count
    free-threaded (no-GIL) usage: those interpreters report their base
    version (e.g. "3.14"), so pyversion can't tell them apart.
    """
    # EXPENSIVE: ~39 GB scanned per call, the priciest query here.
    # Every psutil file ever published gets a row, hence the big limit:
    # cutting the tail undercounts sdist and free-threaded.
    cmd = f"{PYPINFO} 5000 {PKGNAME} file"
    totals = collections.Counter()
    for row in query(cmd)['rows']:
        name = row['file']
        if name.endswith(".metadata"):
            continue  # PEP 658 sidecar, not an actual download
        num = row['download_count']
        if name.endswith((".tar.gz", ".zip")):
            totals["sdist (built from source)"] += num
        elif re.search(r"-cp\d+t-", name):
            totals["wheel (free-threaded)"] += num
        elif "-abi3-" in name:
            totals["wheel (abi3)"] += num
        else:
            totals["wheel (version specific)"] += num
    return totals


# --- print


templ = "| {:<30} | {:>15} |"
templ_pct = "| {:<30} | {:>15} | {:>7} |"


def print_row(left, right, pct=None):
    if isinstance(right, int):
        right = f"{right:,}"
    if pct is None:
        print(templ.format(left, right))
    else:
        print(templ_pct.format(left, right, pct))


def print_header(left, right="Downloads", percent=False):
    if percent:
        print_row(left, right, "%")
        s = templ_pct.format("-" * 30, "-" * 15, "-" * 7)
    else:
        print_row(left, right)
        s = templ.format("-" * 30, "-" * 15)
    print("|:" + s[2:-2] + ":|")


def print_markdown_table(title, left, rows, percent=True):
    pleft = left.replace('_', ' ').capitalize()
    total = sum(x['download_count'] for x in rows)
    print("### " + title)
    print()
    print_header(pleft, percent=percent)
    for row in rows:
        lval = row[left]
        num = row['download_count']
        if percent:
            print_row(lval, num, f"{100 * num / total:.2f}")
        else:
            print_row(lval, num)
    print()


def to_rows(totals, key):
    """Turn a Counter into the row dicts print_markdown_table wants."""
    return [
        {key: name, 'download_count': num}
        for name, num in totals.most_common()
    ]


def main():
    parse_cli()
    downs = downloads()

    print("# Download stats")
    print()
    s = f"psutil download statistics of the last {DAYS} days (last update "
    s += f"*{LAST_UPDATE}*).\n"
    s += f"Generated via [print_downloads.py]({GITHUB_SCRIPT_URL}) script.\n"
    print(s)

    data = [
        {'what': 'Per month', 'download_count': downs},
        {'what': 'Per day', 'download_count': int(downs / DAYS)},
        {'what': 'PYPI ranking', 'download_count': ranking()},
    ]
    print_markdown_table('Overview', 'what', data, percent=False)
    print_markdown_table(
        'Operating systems',
        'system_name',
        to_rows(downloads_by_system(), 'system_name'),
    )
    print_markdown_table(
        'Python versions',
        'python_version',
        to_rows(downloads_pyver(), 'python_version'),
    )
    if ALL:
        print_markdown_table(
            'Wheel types',
            'wheel_type',
            to_rows(downloads_by_wheel(), 'wheel_type'),
        )
        print_markdown_table(
            'Distros', 'distro_name', downloads_by_distro()['rows']
        )


if __name__ == '__main__':
    try:
        main()
    finally:
        if bytes_billed:
            print(f"bytes billed: {bytes_billed}", file=sys.stderr)
