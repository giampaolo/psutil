#!/usr/bin/env python

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Script which downloads exe and wheel files hosted on AppVeyor:
https://ci.appveyor.com/project/giampaolo/psutil
Copied and readapted from the original recipe of Ibarra Corretge'
<saghul@gmail.com>:
http://code.saghul.net/index.php/2015/09/09/
"""

from __future__ import print_function
import argparse
import errno
import multiprocessing
import os
import requests
import shutil

from concurrent.futures import ThreadPoolExecutor


BASE_URL = 'https://ci.appveyor.com/api'


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
    local_filename = url.split('/')[-1]
    local_filename = os.path.join('dist', local_filename)
    print(local_filename)
    safe_makedirs('dist')
    r = requests.get(url, stream=True)
    with open(local_filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:    # filter out keep-alive new chunks
                f.write(chunk)


def get_file_urls(options):
    session = requests.Session()
    data = session.get(
        BASE_URL + '/projects/' + options.user + '/' + options.project)
    data = data.json()

    urls = []
    for job in (job['jobId'] for job in data['build']['jobs']):
        job_url = BASE_URL + '/buildjobs/' + job + '/artifacts'
        data = session.get(job_url)
        data = data.json()
        for item in data:
            file_url = job_url + '/' + item['fileName']
            urls.append(file_url)
    for url in sorted(urls, key=lambda x: os.path.basename(x)):
        yield url


def main(options):
    safe_rmtree('dist')
    with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as e:
        for url in get_file_urls(options):
            e.submit(download_file, url)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='AppVeyor artifact downloader')
    parser.add_argument('--user', required=True)
    parser.add_argument('--project', required=True)
    args = parser.parse_args()
    main(args)
