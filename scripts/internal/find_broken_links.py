#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Look for broken urls in files.

Usage:
    find_broken_urls.py [FILE, ...]
"""

from __future__ import print_function
import re
import socket
import sys
try:
    from urllib2 import urlopen, Request
except ImportError:
    from urllib.request import urlopen, Request


SOCKET_TIMEOUT = 5


def term_supports_colors():
    try:
        import curses
        assert sys.stderr.isatty()
        curses.setupterm()
        assert curses.tigetnum("colors") > 0
    except Exception:
        return False
    else:
        return True


if term_supports_colors():
    def hilite(s, ok=True, bold=False):
        """Return an highlighted version of 'string'."""
        attr = []
        if ok is None:  # no color
            pass
        elif ok:   # green
            attr.append('32')
        else:   # red
            attr.append('31')
        if bold:
            attr.append('1')
        return '\x1b[%sm%s\x1b[0m' % (';'.join(attr), s)
else:
    def hilite(s, *a, **kw):
        return s


def is_valid_url(url):
    regex = re.compile(
        r'^(?:http|ftp)s?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]'
        '{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(re.match(regex, url))


def find_urls(file):
    with open(file, 'r') as f:
        data = f.read()
    regex = 'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%' \
            '[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(regex, data)
    for url in urls:
        url = url.rstrip("/>")
        url = url.rstrip(".")
        url = url.rstrip(",")
        url = url.rstrip("'")
        url = url.rstrip(")")
        if is_valid_url(url):
            yield url


def try_url(url):
    class HeadRequest(Request):
        def get_method(self):
            return "HEAD"

    try:
        resp = urlopen(HeadRequest(url))
    except Exception as err:
        return str(err)
    else:
        if resp.code != 200:
            return "code == %s" % resp.code
    return None


def main(files):
    urls = set()
    socket.setdefaulttimeout(SOCKET_TIMEOUT)

    for file in files:
        for url in find_urls(file):
            urls.add(url)

    broken = []
    total = len(urls)
    for i, url in enumerate(sorted(urls), 1):
        print("%s/%s: %s" % (
            i, total, hilite(url, ok=None, bold=True)), end=" ")
        err = try_url(url)
        if err:
            print(hilite("%s" % err, ok=False))
            broken.append((url, err))
        else:
            print(hilite("OK"))
    if broken:
        print()
        print("broken urls:")
        for url, err in broken:
            print("%s %s" % (url, hilite(err, ok=False)))


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        sys.exit(__doc__)
    main(sys.argv[1:])
