#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Prints releases' timeline in RST format.
"""

import subprocess


entry = """\
- {date}:
  `{ver} <https://pypi.org/project/psutil/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#{nodotver}>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/{prevtag}...{tag}#files_bucket>`__"""  # NOQA


def sh(cmd):
    return subprocess.check_output(
        cmd, shell=True, universal_newlines=True).strip()


def get_tag_date(tag):
    out = sh(r"git log -1 --format=%ai {}".format(tag))
    return out.split(' ')[0]


def main():
    releases = []
    out = sh("git tag")
    for line in out.split('\n'):
        tag = line.split(' ')[0]
        ver = tag.replace('release-', '')
        nodotver = ver.replace('.', '')
        date = get_tag_date(tag)
        releases.append((tag, ver, nodotver, date))
    releases.sort(reverse=True)

    for i, rel in enumerate(releases):
        tag, ver, nodotver, date = rel
        try:
            prevtag = releases[i + 1][0]
        except IndexError:
            # get first commit
            prevtag = sh("git rev-list --max-parents=0 HEAD")
        print(entry.format(**locals()))


if __name__ == '__main__':
    main()
