#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Script which downloads wheel files hosted on AppVeyor:
https://ci.appveyor.com/project/giampaolo/psutil
Re-adapted from the original recipe of Ibarra Corretge'
<saghul@gmail.com>:
http://code.saghul.net/index.php/2015/09/09/.
"""

from __future__ import print_function

import concurrent.futures
import os
import sys

import requests

from psutil import __version__
from psutil._common import bytes2human
from psutil._common import print_color


USER = "giampaolo"
PROJECT = "psutil"
PROJECT_VERSION = __version__
BASE_URL = 'https://ci.appveyor.com/api'
PY_VERSIONS = ['2.7']
TIMEOUT = 30


def download_file(url):
    local_fname = url.split('/')[-1]
    local_fname = os.path.join('dist', local_fname)
    os.makedirs('dist', exist_ok=True)
    r = requests.get(url, stream=True, timeout=TIMEOUT)
    with open(local_fname, 'wb') as f:
        for chunk in r.iter_content(chunk_size=16384):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
    return local_fname


def get_file_urls():
    with requests.Session() as session:
        data = session.get(
            BASE_URL + '/projects/' + USER + '/' + PROJECT, timeout=TIMEOUT
        )
        data = data.json()

        urls = []
        for job in (job['jobId'] for job in data['build']['jobs']):
            job_url = BASE_URL + '/buildjobs/' + job + '/artifacts'
            data = session.get(job_url, timeout=TIMEOUT)
            data = data.json()
            for item in data:
                file_url = job_url + '/' + item['fileName']
                urls.append(file_url)
        if not urls:
            print_color("no artifacts found", 'red')
            sys.exit(1)
        else:
            for url in sorted(urls, key=os.path.basename):
                yield url


def rename_win27_wheels():
    # See: https://github.com/giampaolo/psutil/issues/810
    src = 'dist/psutil-%s-cp27-cp27m-win32.whl' % PROJECT_VERSION
    dst = 'dist/psutil-%s-cp27-none-win32.whl' % PROJECT_VERSION
    print("rename: %s\n        %s" % (src, dst))
    os.rename(src, dst)
    src = 'dist/psutil-%s-cp27-cp27m-win_amd64.whl' % PROJECT_VERSION
    dst = 'dist/psutil-%s-cp27-none-win_amd64.whl' % PROJECT_VERSION
    print("rename: %s\n        %s" % (src, dst))
    os.rename(src, dst)


def run():
    urls = get_file_urls()
    completed = 0
    exc = None
    with concurrent.futures.ThreadPoolExecutor() as e:
        fut_to_url = {e.submit(download_file, url): url for url in urls}
        for fut in concurrent.futures.as_completed(fut_to_url):
            url = fut_to_url[fut]
            try:
                local_fname = fut.result()
            except Exception:
                print_color("error while downloading %s" % (url), 'red')
                raise
            else:
                completed += 1
                print(
                    "downloaded %-45s %s"
                    % (local_fname, bytes2human(os.path.getsize(local_fname)))
                )
    # 2 wheels (32 and 64 bit) per supported python version
    expected = len(PY_VERSIONS) * 2
    if expected != completed:
        return sys.exit("expected %s files, got %s" % (expected, completed))
    if exc:
        return sys.exit()
    rename_win27_wheels()


def main():
    run()


if __name__ == '__main__':
    main()
