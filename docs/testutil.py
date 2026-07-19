# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Shared HTML/feed parsing helpers for the docs test suites.

Imported by both test_docs.py (offline, on the built HTML) and
test_docs_online.py (live site), so the two can't drift on how they
extract the same things.
"""

import re

ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}


def find_canonical(html):
    """The <link rel="canonical"> href, or None. Attribute order
    varies between Sphinx versions, so match both.
    """
    m = re.search(
        r'<link rel="canonical" href="([^"]+)"'
        r'|<link href="([^"]+)" rel="canonical"',
        html,
    )
    return (m.group(1) or m.group(2)) if m else None


def og_value(html, prop):
    """The `content` of a `<meta property="og:...">` tag, or None.
    Sphinx and ablog don't agree on attribute order, so accept both.
    """
    m = re.search(
        rf'<meta (?:property="{prop}" content="([^"]*)"'
        rf'|content="([^"]*)" property="{prop}")',
        html,
    )
    return (m.group(1) or m.group(2)) if m else None


def feed_urls(root):
    """All feed-level + per-entry URLs (link hrefs + entry ids) from a
    parsed atom feed root element.
    """
    urls = [link.get("href") for link in root.findall("a:link", ATOM_NS)]
    for entry in root.findall("a:entry", ATOM_NS):
        idel = entry.find("a:id", ATOM_NS)
        if idel is not None:
            urls.append(idel.text)
        urls.extend(
            link.get("href") for link in entry.findall("a:link", ATOM_NS)
        )
    return [u for u in urls if u]
