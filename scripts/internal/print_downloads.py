#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Print PYPI download statistics.
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

from psutil._common import bytes2human
from psutil._common import hilite

AUTH_FILE = os.path.expanduser("~/.pypinfo.json")
CACHE_FILE = os.path.expanduser("~/.cache/psutil-print-downloads.json")
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
LAST_UPDATE = None
bytes_billed = 0
# Python versions that reached end-of-life.
EOL_PYTHONS = {"2.6", "2.7", "3.4", "3.5", "3.6", "3.7", "3.8", "3.9"}

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


def file_cache(fun):
    """Cache the decorated function's JSON-serializable return value on
    disk for the rest of the day.
    """

    @functools.wraps(fun)
    def wrapper(*args):
        key = repr((fun.__name__, args))
        today = str(datetime.date.today())
        try:
            with open(CACHE_FILE) as f:
                cache = json.load(f)
            if cache["date"] != today:
                raise ValueError("stale")
        except (FileNotFoundError, ValueError, KeyError):
            cache = {"date": today, "entries": {}}
        entries = cache.get("entries", {})
        if key in entries:
            return entries[key]
        ret = fun(*args)
        entries[key] = ret
        cache["entries"] = entries
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
        return ret

    return wrapper


# --- get (free: no credentials, no quota)


@file_cache
def pypistats_fetch(kind):
    url = PYPISTATS_URL.format(PKGNAME, kind)
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)["data"]


@functools.lru_cache
def pypistats(kind):
    """Return a {category: downloads} Counter for the last DAYS days.
    Mirror traffic is excluded.
    """
    global LAST_UPDATE
    rows = pypistats_fetch(kind)
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


@file_cache
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
@file_cache
def query(cmd):
    global bytes_billed
    import pypinfo  # noqa: F401

    ret = json.loads(sh(cmd))
    bytes_billed += ret['query']['bytes_billed']
    return ret


# EXPENSIVE: ~11 GB scanned per call.
def downloads_by_distro():
    return query(f"{PYPINFO} {LIMIT} {PKGNAME} distro")


# EXPENSIVE: ~17 GB scanned per call (only once: it's cached).
def downloads_by_system_release():
    """(system, release) rows, shared by the per-OS tables below.
    The high limit prevents the many distinct Linux kernel versions
    from crowding out the niche OSes.
    """
    cmd = f"{PYPINFO} 5000 {PKGNAME} system system-release"
    return query(cmd)['rows']


def downloads_by_release(system):
    totals = collections.Counter()
    for row in downloads_by_system_release():
        if row['system_name'] == system:
            totals[row['system_release']] += row['download_count']
    return totals


def downloads_by_windows_release():
    # "10" also includes Windows 11: older interpreters report both
    # as "10".
    return downloads_by_release("Windows")


# EXPENSIVE: ~18 GB scanned per call (only once: it's cached).
def downloads_by_dimension(key):
    """Aggregate one dimension (version, implementation,
    installer_name, cpu, libc_name) out of a single combined query.
    BigQuery bills by column, so one query costs less than five.
    Counts are near-exact: combos below the row limit are lost.
    """
    cmd = f"{PYPINFO} 20000 {PKGNAME} version impl installer cpu libc"
    totals = collections.Counter()
    for row in query(cmd)['rows']:
        totals[row[key]] += row['download_count']
    return totals


# platform.release() on macOS returns the Darwin kernel version
DARWIN_TO_MACOS = {
    "19": "10.15 Catalina",
    "20": "11 Big Sur",
    "21": "12 Monterey",
    "22": "13 Ventura",
    "23": "14 Sonoma",
    "24": "15 Sequoia",
    "25": "26 Tahoe",
}


def downloads_by_macos_release():
    totals = collections.Counter()
    for release, num in downloads_by_release("Darwin").items():
        major = release.split(".")[0]
        name = DARWIN_TO_MACOS.get(major, f"Darwin {release}")
        totals[name] += num
    return totals


def downloads_by_other_systems():
    """BSD, AIX, SunOS, etc. Excludes Linux, whose system-release is
    the kernel version (too many, not interesting).
    """
    skip = {"Windows", "Darwin", "Linux", "None", None}
    totals = collections.Counter()
    for row in downloads_by_system_release():
        if row['system_name'] not in skip:
            name = f"{row['system_name']} {row['system_release']}"
            totals[name] += row['download_count']
    return totals


def bq_monthly_usage():
    """Bytes billed to the BigQuery project since the start of the
    month. The free tier is 1 TiB. This query itself bills the 20 MiB
    minimum.
    """
    from google.cloud import bigquery

    os.environ.setdefault('GOOGLE_APPLICATION_CREDENTIALS', AUTH_FILE)
    client = bigquery.Client()
    sql = """
        SELECT COALESCE(SUM(total_bytes_billed), 0) AS billed
        FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_USER
        WHERE creation_time >= TIMESTAMP(DATE_TRUNC(CURRENT_DATE(), MONTH))
    """
    return next(iter(client.query(sql).result())).billed


def downloads_by_wheel():
    """Group downloads by the kind of file fetched. This is the only
    way to count free-threaded (no-GIL) usage: those interpreters
    report the same version as regular ones, so pyversion can't tell
    them apart.
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


def print_table(title, left, rows, percent=True):
    total = sum(x['download_count'] for x in rows)
    if percent:
        header = f"{title:<30}  {'Downloads':>15}  {'%':>7}"
    else:
        header = f"{title:<30}  {'Downloads':>15}"
    print(hilite(header, color="brown", bold=True))
    print(hilite("-" * len(header), color="grey"))
    for row in rows:
        num = row['download_count']
        lval = str(row[left] or "null")
        line = f"{lval:<30}  {num:>15,}"
        if percent:
            line += f"  {100 * num / total:>7.2f}"
        print(line)
    print()


def to_rows(totals, key):
    """Turn a Counter into the row dicts print_table wants."""
    return [
        {key: name, 'download_count': num}
        for name, num in totals.most_common()
    ]


def print_cheap():
    downs = downloads()

    title = f"psutil downloads in the last {DAYS} days"
    print(hilite(title, color="violet", bold=True))
    print(hilite(f"updated at {LAST_UPDATE}", color="grey"))
    overall = pypistats("overall")
    mirrors = overall["with_mirrors"] - overall["without_mirrors"]
    pct = 100 * mirrors / overall["with_mirrors"]
    s = f"mirror traffic (excluded from all tables): {pct:.1f}%"
    print(hilite(s, color="grey"))
    print()

    data = [
        {'what': 'Per month', 'download_count': downs},
        {'what': 'Per day', 'download_count': int(downs / DAYS)},
        {'what': 'PYPI ranking', 'download_count': ranking()},
    ]
    print_table('Overview', 'what', data, percent=False)
    print_table(
        'Operating systems',
        'system_name',
        to_rows(downloads_by_system(), 'system_name'),
    )
    print_table(
        'Python versions',
        'python_version',
        to_rows(downloads_pyver(), 'python_version'),
    )
    eol = sum(
        num for ver, num in downloads_pyver().items() if ver in EOL_PYTHONS
    )
    s = f"downloads from EOL Pythons: {eol:,} ({100 * eol / downs:.1f}%)"
    print(hilite(s, color="grey"))


def print_expensive():
    print_table(
        'psutil versions',
        'version',
        to_rows(downloads_by_dimension('version'), 'version')[:LIMIT],
    )
    print_table(
        'Wheel types',
        'wheel_type',
        to_rows(downloads_by_wheel(), 'wheel_type'),
    )
    print_table(
        'Implementations',
        'implementation',
        to_rows(downloads_by_dimension('implementation'), 'implementation'),
    )
    print_table(
        'Installers',
        'installer_name',
        to_rows(downloads_by_dimension('installer_name'), 'installer_name'),
    )
    print_table('CPUs', 'cpu', to_rows(downloads_by_dimension('cpu'), 'cpu'))
    print_table(
        'libc',
        'libc_name',
        to_rows(downloads_by_dimension('libc_name'), 'libc_name'),
    )
    print_table(
        'Windows versions',
        'windows_release',
        to_rows(downloads_by_windows_release(), 'windows_release'),
    )
    print_table(
        'macOS versions',
        'macos_release',
        to_rows(downloads_by_macos_release(), 'macos_release'),
    )
    print_table(
        'Other systems',
        'system_release',
        to_rows(downloads_by_other_systems(), 'system_release'),
    )
    print_table('Distros', 'distro_name', downloads_by_distro()['rows'])

    billed = bq_monthly_usage()
    pct = 100 * billed / 1024**4
    s = (
        f"BigQuery free tier used this month: {bytes2human(billed)} of 1"
        f" TiB ({pct:.0f}%)"
    )
    print(hilite(s, color="grey"))


def main():
    parse_cli()
    print_cheap()
    if ALL:
        print_expensive()


if __name__ == '__main__':
    try:
        main()
    finally:
        if bytes_billed:
            print(f"bytes billed: {bytes_billed}", file=sys.stderr)
