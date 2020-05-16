#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Script which downloads wheel files hosted on GitHub:
https://github.com/giampaolo/psutil/actions
It needs an access token string generated from personal GitHub profile:
https://github.com/settings/tokens
The token must be created with at least "public_repo" scope/rights.
If you lose it, just generate a new token.
REST API doc:
https://developer.github.com/v3/actions/artifacts/
"""

import argparse
import collections
import json
import os
import requests
import shutil
import zipfile

from psutil._common import bytes2human
from psutil._common import print_color


USER = ""
PROJECT = ""
TOKEN = ""
OUTFILE = "wheels.zip"


# --- GitHub API

def list_artifacts():
    base_url = "https://api.github.com/repos/%s/%s" % (USER, PROJECT)
    url = base_url + "/actions/artifacts"
    res = requests.get(
        url=url,
        headers={"Authorization": "token %s" % TOKEN})
    res.raise_for_status()
    data = json.loads(res.content)
    return data


def download_zip(url):
    print("downloading: " + url)
    res = requests.get(
        url=url,
        headers={"Authorization": "token %s" % TOKEN})
    res.raise_for_status()
    totbytes = 0
    with open(OUTFILE, 'wb') as f:
        for chunk in res.iter_content(chunk_size=16384):
            f.write(chunk)
            totbytes += len(chunk)
    print("got %s, size %s)" % (OUTFILE, bytes2human(totbytes)))


# --- extract


def extract():
    with zipfile.ZipFile(OUTFILE, 'r') as zf:
        zf.extractall('dist')


def print_wheels():
    groups = collections.defaultdict(list)
    for name in os.listdir('dist'):
        plat = name.split('-')[-1]
        if 'linux' in plat:
            groups['LINUX'].append(name)
        elif 'win' in plat:
            groups['WINDOWS'].append(name)
        elif 'macosx' in plat:
            groups['MACOS'].append(name)
        else:
            assert 0, name

    totsize = 0
    for osname, names in groups.items():
        print_color("%s (%s)" % (osname, len(names)),
                    color=None, bold=True)
        for name in sorted(names):
            path = os.path.join('dist', name)
            size = os.path.getsize(path)
            totsize += size
            is64 = name.endswith('x86_64.whl')
            # is32 = name.endswith('i686.whl')
            arch = '32' if is64 else '64'
            s = "  %-55s %-8s %s" % (name, bytes2human(size), arch)
            if '-pypy' not in name:
                print_color(s + '   py  ', color='brown')
            else:
                print_color(s + '   pypy', color='grey')


def run():
    if os.path.isdir('dist'):
        shutil.rmtree('dist')
    data = list_artifacts()
    download_zip(data['artifacts'][0]['archive_download_url'])
    os.mkdir('dist')
    extract()
    print_wheels()


def main():
    global USER, PROJECT, TOKEN
    parser = argparse.ArgumentParser(description='GitHub wheels downloader')
    parser.add_argument('--user', required=True)
    parser.add_argument('--project', required=True)
    parser.add_argument('--tokenfile', required=True)
    args = parser.parse_args()
    USER = args.user
    PROJECT = args.project
    with open(os.path.expanduser(args.tokenfile)) as f:
        TOKEN = f.read().strip()
    run()


if __name__ == '__main__':
    main()
