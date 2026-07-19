# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Smoke tests against the live docs site.

Run with:

  PSUTIL_DOCS_ONLINE=1 python3 -m pytest docs/test_docs_online.py
"""

import http.client
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import conf  # noqa: E402

BASE = conf.html_baseurl.rstrip("/") + "/"
_parts = urlsplit(BASE)
ORIGIN = f"{_parts.scheme}://{_parts.netloc}/"

pytestmark = pytest.mark.skipif(
    not os.environ.get("PSUTIL_DOCS_ONLINE"),
    reason="set PSUTIL_DOCS_ONLINE=1 to run live-site smoke tests",
)


def fetch(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "psutil-docs-test"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, resp.read()


class TestLiveSite:

    def test_homepage_ok(self):
        status, _ = fetch(BASE)
        assert status == 200

    def test_key_endpoints_reachable(self, subtests):
        urls = [
            BASE + "sitemap.xml",
            BASE + "objects.inv",
            BASE + "blog/atom.xml",
            ORIGIN + "robots.txt",
        ]
        for url in urls:
            with subtests.test(url=url):
                status, _ = fetch(url)
                assert status == 200

    def test_sitemap_has_many_urls(self):
        _, body = fetch(BASE + "sitemap.xml")
        assert body.count(b"<url>") >= 20

    def test_fonts_are_self_hosted(self, subtests):
        for name in ("inter-400.woff2", "fa-solid-subset.woff2"):
            with subtests.test(font=name):
                status, _ = fetch(BASE + "_static/fonts/" + name)
                assert status == 200

    def test_homepage_canonical_matches_baseurl(self):
        html = fetch(BASE)[1].decode("utf-8", "replace")
        m = re.search(
            r'<link rel="canonical" href="([^"]+)"'
            r'|<link href="([^"]+)" rel="canonical"',
            html,
        )
        assert m is not None
        assert (m.group(1) or m.group(2)).startswith(BASE)

    def test_homepage_has_og_tags(self, subtests):
        html = fetch(BASE)[1].decode("utf-8", "replace")
        for prop in ("og:title", "og:image"):
            with subtests.test(prop=prop):
                assert f'property="{prop}"' in html

    def test_og_urls_match_baseurl(self, subtests):
        html = fetch(BASE)[1].decode("utf-8", "replace")
        og_url = re.search(r'<meta[^>]*property="og:url"[^>]*>', html)
        with subtests.test(prop="og:url"):
            assert og_url is not None
            m = re.search(r'content="([^"]*)"', og_url.group(0))
            assert m is not None
            assert m.group(1).startswith(BASE)
        og_img = re.search(r'<meta[^>]*property="og:image"[^>]*>', html)
        with subtests.test(prop="og:image"):
            assert og_img is not None
            m = re.search(r'content="([^"]*)"', og_img.group(0))
            assert m is not None
            assert m.group(1).startswith(ORIGIN)

    def test_search_index_reachable(self):
        status, _ = fetch(BASE + "searchindex.js")
        assert status == 200

    def test_http_redirects_to_https(self):
        # Enforce-HTTPS: http must redirect to https.
        conn = http.client.HTTPConnection(urlsplit(BASE).netloc, timeout=30)
        try:
            conn.request(
                "GET", "/", headers={"User-Agent": "psutil-docs-test"}
            )
            resp = conn.getresponse()
            assert resp.status in {301, 302, 307, 308}
            assert resp.getheader("Location", "").startswith("https://")
        finally:
            conn.close()

    def test_custom_404_page(self):
        # A missing path returns the custom 404, not a bare error.
        with pytest.raises(urllib.error.HTTPError) as exc:
            fetch(BASE + "no-such-page-zzz.html")
        assert exc.value.code == 404
        assert b"psutil" in exc.value.read().lower()

    def test_content_pages_reachable(self, subtests):
        for page in ("api.html", "faq.html"):
            with subtests.test(page=page):
                status, body = fetch(BASE + page)
                assert status == 200
                assert b"psutil" in body.lower()

    def test_atom_feed_rooted_at_baseurl(self):
        body = fetch(BASE + "blog/atom.xml")[1]
        ns = {"a": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(body)
        urls = [link.get("href") for link in root.findall("a:link", ns)]
        urls.extend(
            e.find("a:id", ns).text for e in root.findall("a:entry", ns)
        )
        bad = [u for u in urls if u and not u.startswith(BASE)]
        assert bad == []

    def test_no_readthedocs_in_metadata(self):
        html = fetch(BASE)[1].decode("utf-8", "replace")
        head = html.split("</head>", 1)[0]
        assert "readthedocs" not in head.lower()
