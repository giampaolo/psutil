#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola', Himanshu Shekhar.
# All rights reserved. Use of this source code is governed by a
# BSD-style license that can be found in the LICENSE file.

"""
Checks for broken links in file names specified as command line
parameters.

There are a ton of a solutions available for validating URLs in string
using regex, but less for searching, of which very few are accurate.
This snippet is intended to just do the required work, and avoid
complexities. Django Validator has pretty good regex for validation,
but we have to find urls instead of validating them (REFERENCES [7]).
There's always room for improvement.

Method:
* Match URLs using regex (REFERENCES [1]])
* Some URLs need to be fixed, as they have < (or) > due to inefficient
  regex.
* Remove duplicates (because regex is not 100% efficient as of now).
* Check validity of URL, using HEAD request. (HEAD to save bandwidth)
  Uses requests module for others are painful to use. REFERENCES[9]
  Handles redirects, http, https, ftp as well.

REFERENCES:
Using [1] with some modificatons for including ftp
[1] http://stackoverflow.com/a/6883094/5163807
[2] http://stackoverflow.com/a/31952097/5163807
[3] http://daringfireball.net/2010/07/improved_regex_for_matching_urls
[4] https://mathiasbynens.be/demo/url-regex
[5] https://github.com/django/django/blob/master/django/core/validators.py
[6] https://data.iana.org/TLD/tlds-alpha-by-domain.txt
[7] https://codereview.stackexchange.com/questions/19663/http-url-validating
[8] https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/HEAD
[9] http://docs.python-requests.org/

Author: Himanshu Shekhar <https://github.com/himanshub16> (2017)
"""

from __future__ import print_function

import os
import re
import sys
import traceback
import concurrent.futures

import requests


HERE = os.path.abspath(os.path.dirname(__file__))
REGEX = r'(?:http|ftp|https)?://' \
        r'(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
REQUEST_TIMEOUT = 30
# There are some status codes sent by websites on HEAD request.
# Like 503 by Microsoft, and 401 by Apple
# They need to be sent GET request
RETRY_STATUSES = [503, 401, 403]


def get_urls(filename):
    """Extracts all URLs available in specified filename."""
    with open(filename) as fs:
        text = fs.read()
    urls = re.findall(REGEX, text)
    # remove duplicates, list for sets are not iterable
    urls = list(set(urls))
    # correct urls which are between < and/or >
    for i, url in enumerate(urls):
        urls[i] = re.sub("[\*<>\(\)\)]", '', url)
    return urls


def validate_url(url):
    """Validate the URL by attempting an HTTP connection.
    Makes an HTTP-HEAD request for each URL.
    """
    try:
        res = requests.head(url, timeout=REQUEST_TIMEOUT)
        # some websites deny 503, like Microsoft
        # and some send 401, like Apple, observations
        if (not res.ok) and (res.status_code in RETRY_STATUSES):
            res = requests.get(url, timeout=REQUEST_TIMEOUT)
        return res.ok
    except requests.exceptions.RequestException:
        return False


def parallel_validator(urls):
    """validates all urls in parallel
    urls: tuple(filename, url)
    """
    fails = []  # list of tuples (filename, url)
    current = 0
    total = len(urls)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        fut_to_url = {executor.submit(validate_url, url[1]): url
                      for url in urls}
        for fut in concurrent.futures.as_completed(fut_to_url):
            current += 1
            sys.stdout.write("\r%s / %s" % (current, total))
            sys.stdout.flush()
            fname, url = fut_to_url[fut]
            try:
                ok = fut.result()
            except Exception:
                fails.append((fname, url))
                print()
                print("warn: error while validating %s" % url, file=sys.stderr)
                traceback.print_exc()
            else:
                if not ok:
                    fails.append((fname, url))
    if fails:
        print()
    return fails


def main():
    files = sys.argv[1:]
    if not files:
        return sys.exit("usage: %s <FILES...>" % __name__)

    all_urls = []
    for fname in files:
        urls = get_urls(fname)
        for url in urls:
            all_urls.append((fname, url))

    fails = parallel_validator(all_urls)
    if not fails:
        print("all links are valid; cheers!")
    else:
        for fail in fails:
            fname, url = fail
            print("%s : %s " % (url, fname))
        print('-' * 20)
        print("total: %s fails!" % len(fails))
        sys.exit(1)


if __name__ == '__main__':
    main()
