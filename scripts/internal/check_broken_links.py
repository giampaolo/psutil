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

import concurrent.futures
import functools
import os
import re
import sys
import traceback

import requests


HERE = os.path.abspath(os.path.dirname(__file__))
REGEX = re.compile(
    r'(?:http|ftp|https)?://'
    r'(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
REQUEST_TIMEOUT = 15
# There are some status codes sent by websites on HEAD request.
# Like 503 by Microsoft, and 401 by Apple
# They need to be sent GET request
RETRY_STATUSES = [503, 401, 403]


def memoize(fun):
    """A memoize decorator."""
    @functools.wraps(fun)
    def wrapper(*args, **kwargs):
        key = (args, frozenset(sorted(kwargs.items())))
        try:
            return cache[key]
        except KeyError:
            ret = cache[key] = fun(*args, **kwargs)
            return ret

    cache = {}
    return wrapper


def sanitize_url(url):
    url = url.rstrip(',')
    url = url.rstrip('.')
    url = url.lstrip('(')
    url = url.rstrip(')')
    url = url.lstrip('[')
    url = url.rstrip(']')
    url = url.lstrip('<')
    url = url.rstrip('>')
    return url


def find_urls(s):
    matches = REGEX.findall(s) or []
    return list(set([sanitize_url(x) for x in matches]))


def parse_rst(fname):
    """Look for links in a .rst file."""
    with open(fname) as f:
        text = f.read()
    urls = find_urls(text)
    # HISTORY file has a lot of dead links.
    if fname == 'HISTORY.rst' and urls:
        urls = [
            x for x in urls if
            not x.startswith('https://github.com/giampaolo/psutil/issues')]
    return urls


def parse_py(fname):
    """Look for links in a .py file."""
    with open(fname) as f:
        lines = f.readlines()
    urls = set()
    for i, line in enumerate(lines):
        for url in find_urls(line):
            # comment block
            if line.lstrip().startswith('# '):
                subidx = i + 1
                while True:
                    nextline = lines[subidx].strip()
                    if re.match('^#     .+', nextline):
                        url += nextline[1:].strip()
                    else:
                        break
                    subidx += 1
            urls.add(url)
    return list(urls)


def parse_c(fname):
    """Look for links in a .py file."""
    with open(fname) as f:
        lines = f.readlines()
    urls = set()
    for i, line in enumerate(lines):
        for url in find_urls(line):
            # comment block //
            if line.lstrip().startswith('// '):
                subidx = i + 1
                while True:
                    nextline = lines[subidx].strip()
                    if re.match('^//     .+', nextline):
                        url += nextline[2:].strip()
                    else:
                        break
                    subidx += 1
            # comment block /*
            elif line.lstrip().startswith('* '):
                subidx = i + 1
                while True:
                    nextline = lines[subidx].strip()
                    if re.match(r'^\*     .+', nextline):
                        url += nextline[1:].strip()
                    else:
                        break
                    subidx += 1
            urls.add(url)
    return list(urls)


def parse_generic(fname):
    with open(fname) as f:
        text = f.read()
    return find_urls(text)


def get_urls(fname):
    """Extracts all URLs in fname and return them as a list."""
    if fname.endswith('.rst'):
        return parse_rst(fname)
    elif fname.endswith('.py'):
        return parse_py(fname)
    elif fname.endswith('.c') or fname.endswith('.h'):
        return parse_c(fname)
    else:
        with open(fname) as f:
            if f.readline().strip().startswith('#!/usr/bin/env python'):
                return parse_py(fname)
        return parse_generic(fname)


@memoize
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

    print()
    return fails


def main():
    files = sys.argv[1:]
    if not files:
        print("usage: %s <FILES...>" % sys.argv[0], file=sys.stderr)
        return sys.exit(1)

    all_urls = []
    for fname in files:
        urls = get_urls(fname)
        if urls:
            print("%4s %s" % (len(urls), fname))
            for url in urls:
                all_urls.append((fname, url))

    fails = parallel_validator(all_urls)
    if not fails:
        print("all links are valid; cheers!")
    else:
        for fail in fails:
            fname, url = fail
            print("%-30s: %s " % (fname, url))
        print('-' * 20)
        print("total: %s fails!" % len(fails))
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        os._exit(0)
