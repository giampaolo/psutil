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
import json
import os
import requests
import zipfile

from psutil import __version__ as PSUTIL_VERSION
from psutil._common import bytes2human
from psutil.tests import safe_rmpath


USER = ""
PROJECT = ""
TOKEN = ""
OUTFILE = "wheels-github.zip"


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


def rename_win27_wheels():
    # See: https://github.com/giampaolo/psutil/issues/810
    src = 'dist/psutil-%s-cp27-cp27m-win32.whl' % PSUTIL_VERSION
    dst = 'dist/psutil-%s-cp27-none-win32.whl' % PSUTIL_VERSION
    if os.path.exists(src):
        print("rename: %s\n        %s" % (src, dst))
        os.rename(src, dst)
    src = 'dist/psutil-%s-cp27-cp27m-win_amd64.whl' % PSUTIL_VERSION
    dst = 'dist/psutil-%s-cp27-none-win_amd64.whl' % PSUTIL_VERSION
    if os.path.exists(src):
        print("rename: %s\n        %s" % (src, dst))
        os.rename(src, dst)


def run():
    data = get_artifacts()
    download_zip(data['artifacts'][0]['archive_download_url'])
    os.makedirs('dist', exist_ok=True)
    with zipfile.ZipFile(OUTFILE, 'r') as zf:
        zf.extractall('dist')
    rename_win27_wheels()


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
    try:
        run()
    finally:
        safe_rmpath(OUTFILE)


if __name__ == '__main__':
    main()
