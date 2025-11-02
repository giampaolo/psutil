#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Script which downloads wheel files hosted on GitHub:
https://github.com/giampaolo/psutil/actions
It needs an access token string generated from personal GitHub profile:
https://github.com/settings/tokens
The token must be created with at least "public_repo" scope/rights.
If you lose it, just generate a new token.
REST API doc:
https://developer.github.com/v3/actions/artifacts/.
"""

import argparse
import json
import os
import shutil
import sys
import zipfile

import requests

from psutil._common import bytes2human

USER = "giampaolo"
PROJECT = "psutil"
OUTFILE = "wheels-github.zip"
TOKEN = ""
TIMEOUT = 30


def safe_rmpath(path):
    """Convenience function for removing temporary test files or dirs."""
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def get_artifacts():
    base_url = f"https://api.github.com/repos/{USER}/{PROJECT}"
    url = base_url + "/actions/artifacts"
    res = requests.get(
        url=url, headers={"Authorization": f"token {TOKEN}"}, timeout=TIMEOUT
    )
    res.raise_for_status()
    data = json.loads(res.content)
    return data


def download_zip(url):
    print("downloading: " + url)
    res = requests.get(
        url=url, headers={"Authorization": f"token {TOKEN}"}, timeout=TIMEOUT
    )
    res.raise_for_status()
    totbytes = 0
    with open(OUTFILE, 'wb') as f:
        for chunk in res.iter_content(chunk_size=16384):
            f.write(chunk)
            totbytes += len(chunk)
    print(f"got {OUTFILE}, size {bytes2human(totbytes)})")


def run():
    data = get_artifacts()
    download_zip(data['artifacts'][0]['archive_download_url'])
    os.makedirs('dist', exist_ok=True)
    with zipfile.ZipFile(OUTFILE, 'r') as zf:
        zf.extractall('dist')


def main():
    global TOKEN
    parser = argparse.ArgumentParser(description='GitHub wheels downloader')
    parser.add_argument('--token')
    parser.add_argument('--tokenfile')
    args = parser.parse_args()

    if args.tokenfile:
        with open(os.path.expanduser(args.tokenfile)) as f:
            TOKEN = f.read().strip()
    elif args.token:
        TOKEN = args.token
    else:
        return sys.exit('specify --token or --tokenfile args')

    try:
        run()
    finally:
        safe_rmpath(OUTFILE)


if __name__ == '__main__':
    main()
