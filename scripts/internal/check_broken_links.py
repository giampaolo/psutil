#!/usr/bin/env python

# Author : Himanshu Shekhar < https://github.com/himanshub16 > (2017)
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Checks for broken links in file names specified as command line parameters.

There are a ton of a solutions available for validating URLs in string using
regex, but less for searching, of which very few are accurate.
This snippet is intended to just do the required work, and avoid complexities.
Django Validator has pretty good regex for validation, but we have to find
urls instead of validating them. (REFERENCES [7])
There's always room for improvement.

Method:
* Match URLs using regex (REFERENCES [1]])
* Some URLs need to be fixed, as they have < (or) > due to inefficient regex.
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

"""

from __future__ import print_function

import os
import re
import sys

import requests


HERE = os.path.abspath(os.path.dirname(__file__))

REGEX = r'(?:http|ftp|https)?://' \
        r'(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'


def get_urls(filename):
    """Extracts all URLs available in specified filename
    """
    # fname = os.path.abspath(os.path.join(HERE, filename))
    # expecting absolute path
    fname = os.path.abspath(filename)
    print(fname)
    text = ''
    with open(fname) as f:
        text = f.read()

    urls = re.findall(REGEX, text)
    # remove duplicates, list for sets are not iterable
    urls = list(set(urls))
    # correct urls which are between < and/or >
    i = 0
    while i < len(urls):
        urls[i] = re.sub("[<>]", '', urls[i])
        i += 1

    return urls


def validate_url(url):
    """Validate the URL by attempting an HTTP connection.
    Makes an HTTP-HEAD request for each URL.
    Uses requests module.
    """
    try:
        res = requests.head(url)
        return res.ok
    except requests.exceptions.RequestException:
        return False


def main():
    """Main function
    """
    files = sys.argv[1:]
    fails = []
    for fname in files:
        urls = get_urls(fname)
        i = 0
        last = len(urls)
        for url in urls:
            i += 1
            if not validate_url(url):
                fails.append((url, fname))
            sys.stdout.write("\r " +
                             fname + " : " + str(i) + " / " + str(last))
            sys.stdout.flush()

    print()
    if len(fails) == 0:
        print("All URLs are valid. Cheers!")
    else:
        print("Total :", len(fails), "fails!")
        print("Writing failed urls to fails.txt")
        with open("../../fails.txt", 'w') as f:
            for fail in fails:
                f.write(fail[1] + ' : ' + fail[0] + os.linesep)
            f.write('-' * 20)
            f.write(os.linesep*2)


if __name__ == '__main__':
    main()
