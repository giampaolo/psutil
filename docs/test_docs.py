# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Sanity checks for the Sphinx docs and blog posts."""

import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import pytest

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
DOCS = ROOT / "docs"
BLOG = DOCS / "blog"

VALID_BLOG_TAGS = frozenset({
    # platforms
    "bsd",
    "linux",
    "macos",
    "sunos",
    "windows",
    # API / compatibility
    "api-design",
    "compatibility",
    "new-api",
    "new-platform",
    # editorial
    "featured",
    # topics
    "c",
    "community",
    "memory",
    "performance",
    "personal",
    "python-core",
    "release",
    "tests",
    "wheels",
})

sys.path.insert(0, str(HERE))  # so that "import conf" wins
import conf  # noqa: E402

HTML_DIR = None


@pytest.fixture(scope="module")
def build_html():
    """Build the site once. `make html` already turns warnings into
    errors by default.
    """
    global HTML_DIR

    tmp = tempfile.mkdtemp()
    subprocess.check_call([
        "make",
        "-C",
        str(DOCS),
        "html",
        f"BUILDDIR={tmp}",
        f"PYTHON={sys.executable}",
    ])
    HTML_DIR = pathlib.Path(tmp) / "html"
    yield
    shutil.rmtree(tmp)
    HTML_DIR = None


def blog_posts():
    return sorted(BLOG.rglob("*.rst"))


def blog_html(rst):
    """Read the built HTML for a blog post given its source .rst."""
    rel = rst.relative_to(BLOG).with_suffix(".html")
    return (HTML_DIR / "blog" / rel).read_text()


class TestBlogPostFiles:

    def test_every_post_has_directives(self):
        missing = []
        for p in blog_posts():
            text = p.read_text()
            missed = [
                k for k in (".. post::", ":author:", ":tags:") if k not in text
            ]
            if missed:
                rel = p.relative_to(ROOT)
                missing.append(f"{rel}: missing {missed}")
        assert missing == []

    def test_post_date_year_matches_path_year(self):
        mismatches = []
        for p in blog_posts():
            m = re.search(r"\.\. post:: (\d{4})-", p.read_text())
            if m and m.group(1) != p.parent.name:
                rel = p.relative_to(ROOT)
                mismatches.append(
                    f"{rel}: date-year={m.group(1)} dir={p.parent.name}"
                )
        assert mismatches == []

    def test_valid_tags(self):
        invalid = {}
        for p in blog_posts():
            m = re.search(r":tags:\s*(.+)", p.read_text())
            if not m:
                continue
            bad = [
                t
                for t in (x.strip() for x in m.group(1).split(","))
                if t not in VALID_BLOG_TAGS
            ]
            if bad:
                invalid[str(p.relative_to(ROOT))] = bad
        assert not invalid, f"invalid tags: {invalid}"


@pytest.mark.usefixtures("build_html")
class TestHtmlBuildSite:
    """Checks on the Sphinx site (non-blog pages)."""

    def test_files_exist(self):
        assert (HTML_DIR / "index.html").exists()
        assert (HTML_DIR / "blog.html").exists()

    def test_changelog_anchors(self):
        # Indirectly test _ext/changelog_anchors.py. Every X.Y.Z
        # version heading in changelog.rst must get an `id="XYZ"`
        # anchor in the rendered HTML.
        source = (DOCS / "changelog.rst").read_text()
        html = (HTML_DIR / "changelog.html").read_text()
        missing = []
        for m in re.finditer(r"^(\d+)\.(\d+)\.(\d+)", source, re.MULTILINE):
            anchor = "".join(m.groups())
            if f'id="{anchor}"' not in html:
                missing.append(m.group(0))
        assert missing == []

    def test_gh_role_resolves(self):
        # Checks extlinks = {"gh": ...} in conf.py. Without it, every
        # :gh:`NNN` in the docs silently renders as plain text instead
        # of links.
        html = (HTML_DIR / "changelog.html").read_text()
        assert 'href="https://github.com/giampaolo/psutil/issues/' in html

    def test_intersphinx_resolves(self):
        # Check intersphinx_mapping["python"] in conf.py. If it does
        # not work, :mod:`func` refs to the stdlib silently render as
        # plain text instead of links.
        html = (HTML_DIR / "api.html").read_text()
        assert 'href="https://docs.python.org/3/' in html

    def test_sitemap(self, subtests):
        # sphinx-sitemap should emit one <url> per built HTML page
        # (source docs + blog posts + ablog-generated pages),
        # rooted at html_baseurl.
        sitemap = HTML_DIR / "sitemap.xml"
        assert sitemap.exists()
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        tree = ET.parse(sitemap)
        urls = {u.text for u in tree.getroot().findall("s:url/s:loc", ns)}
        for page in (
            "index.html",
            "api.html",
            "changelog.html",
            "blog/2026/event-driven-process-waiting.html",
        ):
            with subtests.test(page=page):
                assert conf.html_baseurl + page in urls

    def test_og_tags_on_source_pages(self, subtests):
        for rst in sorted(DOCS.rglob("*.rst")):
            if rst.name == "blog.rst":
                continue
            rel = rst.relative_to(DOCS).with_suffix(".html")
            html_path = HTML_DIR / rel
            if not html_path.exists():
                continue  # excluded from build (e.g. _globals.rst)
            html = html_path.read_text()
            with subtests.test(rst=rst):
                for needle in (
                    "og:title",
                    "og:site_name",
                    "og:description",
                    "og:image",
                ):
                    assert needle in html


@pytest.mark.usefixtures("build_html")
class TestCodeAutoLink:
    """Checks sphinx-codeautolink integration."""

    def test_enabled(self):
        html = (HTML_DIR / "api-overview.html").read_text()
        assert "sphinx-codeautolink-a" in html

    def test_resolves_process_instance_methods(self):
        # Check that things like `p.name()`are resolved.
        html = (HTML_DIR / "api-overview.html").read_text()
        assert (
            '<a class="sphinx-codeautolink-a" '
            'href="api.html#psutil.Process.name"'
            in html
        )


@pytest.mark.usefixtures("build_html")
class TestHtmlBuildBlog:
    """Checks on blog pages."""

    def test_post_banner_on_every_post(self, subtests):
        css_names = (
            "post-meta-banner",
            "post-meta-author",
            "post-meta-date",
            "post-meta-readtime",
            "post-meta-tags",
            "post-nav",
        )
        for rst in blog_posts():
            html = blog_html(rst)
            for css in css_names:
                with subtests.test(rst=rst):
                    assert css in html

    def test_listing_has_all_posts(self, subtests):
        # blog.html should list all posts, each containing the post's
        # title.

        def post_title(rst):
            lines = rst.read_text().splitlines()
            for i in range(1, len(lines)):
                if re.fullmatch(r"=+", lines[i].strip()):
                    return lines[i - 1].strip()
            pytest.fail(f"no RST H1 found in {rst}")

        posts = blog_posts()
        html = (HTML_DIR / "blog.html").read_text()
        assert len(re.findall(r'<li class="blog-card[^"]*"', html)) == len(
            posts
        )
        for rst in posts:
            with subtests.test(rst=rst):
                assert post_title(rst) in html

    def test_listing_shows_summary(self, subtests):
        # Each post should have a summary below the title.
        html = (HTML_DIR / "blog.html").read_text()
        summaries = re.findall(
            r'<div class="blog-card-summary">(.*?)</div>', html, re.DOTALL
        )
        posts = blog_posts()
        assert len(summaries) == len(posts)
        for i, summary in enumerate(summaries):
            plain = re.sub(r"<[^>]+>", "", summary).strip()
            with subtests.test(card=i):
                assert plain

    def test_listing_years(self):
        # blog.html should list every year that has at least one post.
        expected = sorted({p.parent.name for p in blog_posts()}, reverse=True)
        html = (HTML_DIR / "blog.html").read_text()
        m = re.search(
            r">Years</span>\s*<ul class=\"blog-facet-list\">(.*?)</ul>",
            html,
            re.DOTALL,
        )
        assert m
        years = re.findall(r">(\d{4})</a>", m.group(1))
        assert years == expected

    def test_atom_feed(self):
        feed = HTML_DIR / "blog" / "atom.xml"
        ns = {"a": "http://www.w3.org/2005/Atom"}
        entries = ET.parse(feed).getroot().findall("a:entry", ns)
        assert len(entries) == len(blog_posts())

    def test_atom_on_every_page(self, subtests):
        # Without it, feed readers can't auto-find the feed from post
        # URLs. The tag lives in <head>, so only scan the first chunk.
        needle = 'type="application/atom+xml"'
        for html in sorted(HTML_DIR.rglob("*.html")):
            with subtests.test(page=html.relative_to(HTML_DIR)):
                with open(html, encoding="utf-8") as f:
                    head = f.read(8192)
                assert needle in head

    def test_og_tags_on_blog_posts(self, subtests):
        # sphinxext-opengraph should emit og:* meta tags on every
        # post page so that shared URLs render as rich previews.
        properties = ("og:title", "og:url", "og:site_name", "og:description")
        for rst in blog_posts():
            html = blog_html(rst)
            for prop in properties:
                with subtests.test(rst=rst, prop=prop):
                    assert f'property="{prop}"' in html

    def test_og_description_excludes_post_banner(self, subtests):
        # Regression: the post banner (author/date/readtime/tags)
        # used to leak into og:description, making social previews
        # start with "Giampaolo Rodola 2026-01-28 5 min read ...".
        pattern = re.compile(
            r'<meta (?:property="og:description" content="([^"]*)"'
            r'|content="([^"]*)" property="og:description")'
        )
        for rst in blog_posts():
            html = blog_html(rst)
            m = pattern.search(html)
            with subtests.test(rst=rst):
                assert m is not None
                desc = m.group(1) or m.group(2)
                assert not desc.startswith("Giampaolo")
                assert "min read" not in desc[:80]

    def test_featured_pill_on_post_page(self, subtests):
        # Posts with the "featured" tag show a "Featured" pill in
        # their post-meta banner via _ext/post_banner.py. Other posts
        # must not.
        for rst in blog_posts():
            text = rst.read_text()
            m = re.search(r":tags:\s*(.+)", text)
            tags = [t.strip() for t in m.group(1).split(",")] if m else []
            is_featured = "featured" in tags
            html = blog_html(rst)
            with subtests.test(rst=rst, is_featured=is_featured):
                if is_featured:
                    assert "post-meta-featured" in html
                else:
                    assert "post-meta-featured" not in html
