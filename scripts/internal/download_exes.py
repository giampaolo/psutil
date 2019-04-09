#!/usr/bin/env python

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Script which downloads exe and wheel files hosted on AppVeyor:
https://ci.appveyor.com/project/giampaolo/psutil
Readapted from the original recipe of Ibarra Corretge'
<saghul@gmail.com>:
http://code.saghul.net/index.php/2015/09/09/
"""

from __future__ import print_function
import argparse
import concurrent.futures
import errno
import os
import requests
import shutil

from psutil import __version__ as PSUTIL_VERSION
from psutil._common import bytes2human
from scriptutils import printerr, exit


BASE_URL = 'https://ci.appveyor.com/api'
PY_VERSIONS = ['2.7', '3.5', '3.6', '3.7']
TIMEOUT = 30
COLORS = True


def safe_makedirs(path):
    try:
        os.makedirs(path)
    except OSError as err:
        if err.errno == errno.EEXIST:
            if not os.path.isdir(path):
                raise
        else:
            raise


def safe_rmtree(path):
    def onerror(fun, path, excinfo):
        exc = excinfo[1]
        if exc.errno != errno.ENOENT:
            raise

    shutil.rmtree(path, onerror=onerror)


def download_file(url):
    local_fname = url.split('/')[-1]
    local_fname = os.path.join('dist', local_fname)
    safe_makedirs('dist')
    r = requests.get(url, stream=True, timeout=TIMEOUT)
    tot_bytes = 0
    with open(local_fname, 'wb') as f:
        for chunk in r.iter_content(chunk_size=16384):
            if chunk:    # filter out keep-alive new chunks
                f.write(chunk)
                tot_bytes += len(chunk)
    return local_fname


def get_file_urls(options):
    with requests.Session() as session:
        data = session.get(
            BASE_URL + '/projects/' + options.user + '/' + options.project,
            timeout=TIMEOUT)
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
            exit("no artifacts found")
        else:
            for url in sorted(urls, key=lambda x: os.path.basename(x)):
                yield url


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


def run(options):
    safe_rmtree('dist')
    urls = get_file_urls(options)
    completed = 0
    exc = None
    with concurrent.futures.ThreadPoolExecutor() as e:
        fut_to_url = {e.submit(download_file, url): url for url in urls}
        for fut in concurrent.futures.as_completed(fut_to_url):
            url = fut_to_url[fut]
            try:
                local_fname = fut.result()
            except Exception:
                printerr("error while downloading %s" % (url))
                raise
            else:
                completed += 1
                print("downloaded %-45s %s" % (
                    local_fname, bytes2human(os.path.getsize(local_fname))))
    # 2 wheels (32 and 64 bit) per supported python version
    expected = len(PY_VERSIONS) * 2
    if expected != completed:
        return exit("expected %s files, got %s" % (expected, completed))
    if exc:
        return exit()
    rename_27_wheels()


def main():
    parser = argparse.ArgumentParser(
        description='AppVeyor artifact downloader')
    parser.add_argument('--user', required=True)
    parser.add_argument('--project', required=True)
    args = parser.parse_args()
    run(args)


if __name__ == '__main__':
    main()
