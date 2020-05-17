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

from psutil import __version__ as PSUTIL_VERSION
from psutil._common import bytes2human
from psutil._common import print_color


USER = ""
PROJECT = ""
TOKEN = ""
OUTFILE = "wheels.zip"


# --- GitHub API


def get_artifacts():
    base_url = "https://api.github.com/repos/%s/%s" % (USER, PROJECT)
    url = base_url + "/actions/artifacts"
    res = requests.get(url=url, headers={"Authorization": "token %s" % TOKEN})
    res.raise_for_status()
    data = json.loads(res.content)
    return data


def download_zip(url):
    print("downloading: " + url)
    res = requests.get(url=url, headers={"Authorization": "token %s" % TOKEN})
    res.raise_for_status()
    totbytes = 0
    with open(OUTFILE, 'wb') as f:
        for chunk in res.iter_content(chunk_size=16384):
            f.write(chunk)
            totbytes += len(chunk)
    print("got %s, size %s)" % (OUTFILE, bytes2human(totbytes)))


# --- extract


def rename_27_wheels():
    # See: https://github.com/giampaolo/psutil/issues/810
    src = 'dist/psutil-%s-cp27-cp27m-win32.whl' % PSUTIL_VERSION
    dst = 'dist/psutil-%s-cp27-none-win32.whl' % PSUTIL_VERSION
    print("rename: %s\n        %s" % (src, dst))
    os.rename(src, dst)
    src = 'dist/psutil-%s-cp27-cp27m-win_amd64.whl' % PSUTIL_VERSION
    dst = 'dist/psutil-%s-cp27-none-win_amd64.whl' % PSUTIL_VERSION
    print("rename: %s\n        %s" % (src, dst))
    os.rename(src, dst)


def extract():
    with zipfile.ZipFile(OUTFILE, 'r') as zf:
        zf.extractall('dist')


def print_wheels():
    def is64bit(name):
        return name.endswith(('x86_64.whl', 'amd64.whl'))

    groups = collections.defaultdict(list)
    for name in os.listdir('dist'):
        plat = name.split('-')[-1]
        pyimpl = name.split('-')[3]
        if 'linux' in plat:
            if 'pypy' in pyimpl:
                groups['pypy_on_linux'].append(name)
            else:
                groups['linux'].append(name)
        elif 'win' in plat:
            if 'pypy' in pyimpl:
                groups['pypy_on_windows'].append(name)
            else:
                groups['windows'].append(name)
        elif 'macosx' in plat:
            if 'pypy' in pyimpl:
                groups['pypy_on_macos'].append(name)
            else:
                groups['macos'].append(name)
        else:
            assert 0, name

    totsize = 0
    templ = "%-54s %7s %7s %7s"
    for platf, names in groups.items():
        ppn = "%s (total = %s)" % (platf.replace('_', ' '), len(names))
        s = templ % (ppn, "size", "arch", "pyver")
        print_color('\n' + s, color=None, bold=True)
        for name in sorted(names):
            path = os.path.join('dist', name)
            size = os.path.getsize(path)
            totsize += size
            arch = '64' if is64bit(name) else '32'
            pyver = 'pypy' if name.split('-')[3].startswith('pypy') else 'py'
            pyver += name.split('-')[2][2:]
            s = templ % (name, bytes2human(size), arch, pyver)
            if 'pypy' in pyver:
                print_color(s, color='violet')
            else:
                print_color(s, color='brown')


def run():
    if os.path.isdir('dist'):
        shutil.rmtree('dist')
    data = get_artifacts()
    download_zip(data['artifacts'][0]['archive_download_url'])
    os.mkdir('dist')
    extract()
    rename_27_wheels()
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
