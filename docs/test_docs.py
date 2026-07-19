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
from datetime import datetime
from datetime import timezone

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


def read_html(*parts):
    return HTML_DIR.joinpath(*parts).read_text()


def post_title(rst):
    """First H1 in a .rst file (the line above a `===` underline)."""
    lines = rst.read_text().splitlines()
    for i in range(1, len(lines)):
        if re.fullmatch(r"=+", lines[i].strip()):
            return lines[i - 1].strip()
    raise ValueError(f"no RST H1 found in {rst}")


def post_tags(rst):
    """Tags from a blog post's `:tags:` line, or [] if absent."""
    m = re.search(r":tags:\s*(.+)", rst.read_text())
    if not m:
        return []
    return [t.strip() for t in m.group(1).split(",")]


def blog_html(rst):
    """Read the built HTML for a blog post given its source .rst."""
    rel = rst.relative_to(BLOG).with_suffix(".html")
    return (HTML_DIR / "blog" / rel).read_text()


def source_rst_for(html_path):
    """Return the .rst source for an HTML page, or None for pages
    generated without a source (ablog archives, sphinx auto-pages
    like genindex/search/py-modindex).
    """
    rel = html_path.relative_to(HTML_DIR).with_suffix(".rst")
    src = DOCS / rel
    return src if src.is_file() else None


def og_value(html, prop):
    """Pull the `content` of a `<meta property="og:..." ...>` tag.
    Sphinx and ablog don't agree on attribute order, so accept both.
    """
    m = re.search(
        rf'<meta (?:property="{prop}" content="([^"]*)"'
        rf'|content="([^"]*)" property="{prop}")',
        html,
    )
    return (m.group(1) or m.group(2)) if m else None


def all_html_pages():
    """Every "real content" HTML page in the build."""
    for p in sorted(HTML_DIR.rglob("*.html")):
        rel_parts = p.relative_to(HTML_DIR).parts
        if any(part.startswith("_") for part in rel_parts):
            continue
        if source_rst_for(p) is None:
            continue
        yield p


class TestBlogPostFiles:

    def test_every_file_has_directives(self):
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

    def test_date_year_matches_path_year(self):
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
            bad = [t for t in post_tags(p) if t not in VALID_BLOG_TAGS]
            if bad:
                invalid[str(p.relative_to(ROOT))] = bad
        assert not invalid, f"invalid tags: {invalid}"


@pytest.mark.usefixtures("build_html")
class TestHtmlBuild:
    """Build sanity: pages exist, extensions wire up, footer dates."""

    def test_files_exist(self):
        assert (HTML_DIR / "index.html").exists()
        assert (HTML_DIR / "blog.html").exists()

    def test_changelog_anchors(self):
        # Indirectly test _ext/changelog_anchors.py. Every X.Y.Z
        # version heading in changelog.rst must get an `id="XYZ"`
        # anchor in the rendered HTML.
        source = (DOCS / "changelog.rst").read_text()
        html = read_html("changelog.html")
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
        html = read_html("changelog.html")
        assert 'href="https://github.com/giampaolo/psutil/issues/' in html

    def test_intersphinx_resolves(self):
        # Check intersphinx_mapping["python"] in conf.py. If it does
        # not work, :mod:`func` refs to the stdlib silently render as
        # plain text instead of links.
        html = read_html("api.html")
        assert 'href="https://docs.python.org/3/' in html

    def test_footer_last_updated_matches_git(self, subtests):
        # Skip pages that pull in external files via `.. include::`
        # or `.. raw:: <fmt> :file:`. sphinx-last-updated-by-git
        # walks those deps and picks the latest commit timestamp,
        # which we don't replicate here.
        dep_pat = re.compile(r"^\.\. (?:include|raw)::", re.MULTILINE)
        date_pat = re.compile(r"<span>Updated: (\d{4}-\d{2}-\d{2})</span>")
        for html in all_html_pages():
            src = source_rst_for(html)
            if dep_pat.search(src.read_text()):
                continue
            m = date_pat.search(html.read_text())
            if m is None:
                continue  # page doesn't render the footer date
            cmd = ["git", "log", "-1", "--format=%ct", "--", str(src)]
            ts = subprocess.check_output(cmd).strip()
            if not ts:
                continue  # untracked source file
            expected = datetime.fromtimestamp(
                int(ts), tz=timezone.utc
            ).strftime("%Y-%m-%d")
            with subtests.test(page=html.relative_to(HTML_DIR)):
                assert m.group(1) == expected


@pytest.mark.usefixtures("build_html")
class TestSitemap:

    def test_known_pages_listed(self, subtests):
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

    def test_has_every_blog_post(self, subtests):
        # Catches drift between ablog's post registry and
        # sphinx-sitemap. If sphinx-sitemap stops listing some posts
        # (e.g. due to an ablog version bump), search engines stop
        # discovering them.
        sitemap = HTML_DIR / "sitemap.xml"
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = {
            u.text
            for u in ET.parse(sitemap).getroot().findall("s:url/s:loc", ns)
        }
        for rst in blog_posts():
            rel = rst.relative_to(BLOG).with_suffix(".html")
            expected = conf.html_baseurl + "blog/" + rel.as_posix()
            with subtests.test(rst=rst):
                assert expected in urls


@pytest.mark.usefixtures("build_html")
class TestCanonicalUrl:

    def test_link_on_pages(self, subtests):
        # Sphinx emits <link rel="canonical"> using html_baseurl. If
        # html_baseurl is misconfigured (e.g. lacks the /latest/
        # prefix while the deploy is version-pathed), every shared
        # URL points at a 404.
        pattern = re.compile(
            r'<link (?:rel="canonical" href="([^"]*)"'
            r'|href="([^"]*)" rel="canonical")'
        )
        for page in (
            "index.html",
            "api.html",
            "blog/2026/event-driven-process-waiting.html",
        ):
            m = pattern.search(read_html(page))
            with subtests.test(page=page):
                assert m is not None
                url = m.group(1) or m.group(2)
                assert url.startswith(conf.html_baseurl)

    def test_og_urls_rooted_at_baseurl(self, subtests):
        # og:url + og:image must point at the deployed domain; they
        # once lagged html_baseurl and pointed at the old host.
        html = read_html("api.html")
        for prop in ("og:url", "og:image"):
            tag = re.search(rf'<meta[^>]*property="{prop}"[^>]*>', html)
            with subtests.test(prop=prop):
                assert tag is not None
                m = re.search(r'content="([^"]*)"', tag.group(0))
                assert m is not None
                assert m.group(1).startswith(conf.html_baseurl)


@pytest.mark.usefixtures("build_html")
class TestRightToc:

    def test_visibility(self, subtests):
        has_toc = ("api.html", "faq.html", "glossary.html", "blog.html")
        no_toc = ("index.html", "genindex.html", "search.html")
        pat = re.compile(r'<aside[^>]*\bclass="[^"]*\bright-sidebar\b')
        for file in has_toc:
            with subtests.test(file=file):
                assert pat.search(read_html(file))
        for file in no_toc:
            with subtests.test(file=file):
                assert not pat.search(read_html(file))

    def test_hash_targets_resolve(self, subtests):
        # Every <a href="#..."> inside the right-sidebar must point to
        # an id that exists on the same page. Otherwise the JS
        # hash-match path in right-toc.js silently misses on direct
        # URL load.
        html = read_html("api.html")
        m = re.search(
            r'<aside[^>]*\bclass="[^"]*\bright-sidebar\b[^"]*"[^>]*>(.*?)</aside>',
            html,
            re.DOTALL,
        )
        assert m
        hrefs = re.findall(r'href="#([^"]+)"', m.group(1))
        assert hrefs
        ids_on_page = set(re.findall(r'\bid="([^"]+)"', html))
        for href in hrefs:
            with subtests.test(href=href):
                assert href in ids_on_page

    def test_glossary_mode(self):
        # Tests docs/_ext/glossary_toc.py, which injects
        # glossary_terms into the Jinja context.
        html = read_html("glossary.html")
        assert 'data-toc-mode="glossary"' in html
        m = re.search(
            r'<aside class="right-sidebar'
            r' right-sidebar--glossary"[^>]*>(.*?)</aside>',
            html,
            re.DOTALL,
        )
        assert m, "right-sidebar--glossary aside not found"
        terms = re.findall(r'<a href="#term-[^"]*">([^<]+)</a>', m.group(1))
        assert terms
        assert terms == sorted(terms, key=str.lower)


@pytest.mark.usefixtures("build_html")
class TestCodeAutoLink:
    """Checks sphinx-codeautolink integration."""

    def test_enabled(self):
        html = read_html("api-overview.html")
        assert "sphinx-codeautolink-a" in html

    def test_resolves_process_instance_methods(self):
        # Check that things like `p.name()`are resolved.
        html = read_html("api-overview.html")
        assert (
            '<a class="sphinx-codeautolink-a" '
            'href="api.html#psutil.Process.name"'
            in html
        )


@pytest.mark.usefixtures("build_html")
class TestAtomFeed:

    def test_entry_count(self):
        feed = HTML_DIR / "blog" / "atom.xml"
        ns = {"a": "http://www.w3.org/2005/Atom"}
        entries = ET.parse(feed).getroot().findall("a:entry", ns)
        assert len(entries) == len(blog_posts())

    def test_uses_utc(self):
        feed = HTML_DIR / "blog" / "atom.xml"
        ns = {"a": "http://www.w3.org/2005/Atom"}
        entries = ET.parse(feed).getroot().findall("a:entry", ns)
        assert entries
        non_utc = []
        for e in entries:
            for tag in ("a:updated", "a:published"):
                el = e.find(tag, ns)
                assert el is not None
                if not (el.text.endswith("+00:00") or el.text.endswith("Z")):
                    non_utc.append(el.text)
        assert non_utc == []

    def test_uses_canonical_url(self):
        # Regression: feed-level + per-entry URLs must be rooted at
        # html_baseurl so they match the deployed location. Without
        # it, feed readers 404.
        feed = HTML_DIR / "blog" / "atom.xml"
        ns = {"a": "http://www.w3.org/2005/Atom"}
        root = ET.parse(feed).getroot()
        urls = [link.get("href") for link in root.findall("a:link", ns)]
        for e in root.findall("a:entry", ns):
            urls.append(e.find("a:id", ns).text)
            urls.extend(link.get("href") for link in e.findall("a:link", ns))
        bad = [u for u in urls if u and not u.startswith(conf.html_baseurl)]
        assert bad == []

    def test_link_on_every_page_exactly_once(self, subtests):
        # Every page must auto-discover the atom feed (so feed readers
        # find it from any post URL), and the <link> must appear only
        # once. layout.html used to inject it unconditionally,
        # duplicating ablog's auto-injection.
        needle = 'type="application/atom+xml"'
        for html in all_html_pages():
            with subtests.test(page=html.relative_to(HTML_DIR)):
                head = html.read_text()[:8192]
                assert head.count(needle) == 1


@pytest.mark.usefixtures("build_html")
class TestOpenGraph:
    """og:* and twitter:* social-preview meta tags."""

    def test_tags_on_source_pages(self, subtests):
        for rst in sorted(DOCS.rglob("*.rst")):
            if rst.name == "blog.rst":
                continue
            rel = rst.relative_to(DOCS).with_suffix(".html")
            html_path = HTML_DIR / rel
            html = html_path.read_text()
            with subtests.test(rst=rst):
                for needle in (
                    "og:title",
                    "og:site_name",
                    "og:description",
                    "og:image",
                ):
                    assert needle in html

    def test_tags_on_blog_posts(self, subtests):
        # sphinxext-opengraph should emit og:* meta tags on every
        # post page so that shared URLs render as rich previews.
        properties = (
            "og:title",
            "og:url",
            "og:site_name",
            "og:description",
            "og:image",
        )
        for rst in blog_posts():
            html = blog_html(rst)
            for prop in properties:
                with subtests.test(rst=rst, prop=prop):
                    assert f'property="{prop}"' in html

    def test_type(self, subtests):
        # For blog posts it must be og:type="article" else "website".
        for rst in blog_posts():
            with subtests.test(rst=rst, expected="article"):
                assert og_value(blog_html(rst), "og:type") == "article"
        for page in ("index.html", "api.html", "install.html"):
            with subtests.test(page=page, expected="website"):
                assert og_value(read_html(page), "og:type") == "website"

    def test_blog_index_metadata(self, subtests):
        # Regression: ablog renders blog.html without a doctree, so
        # sphinxext-opengraph skips emitting og:* tags. Our
        # opengraph_override extension synthesizes them.
        html = read_html("blog.html")
        for tag in (
            'name="description"',
            'property="og:title"',
            'property="og:type"',
            'property="og:url"',
            'property="og:site_name"',
            'property="og:description"',
            'property="og:image"',
            'name="twitter:card"',
        ):
            with subtests.test(tag=tag):
                assert tag in html

    def test_description_uses_post_excerpt(self):
        # Blog post og:description (and the social card PNG sourced
        # from the same value) should be the curated excerpt from the
        # `.. post::` directive body, not the page body's first
        # paragraph. Spot-check on a known post.
        html = read_html("blog", "2026", "event-driven-process-waiting.html")
        desc = og_value(html, "og:description")
        # Excerpt opens with "Replacing"; the page body opens with
        # "One of the less fun aspects of process management ...".
        assert desc is not None
        assert desc.startswith("Replacing")

    def test_description_excludes_post_banner(self, subtests):
        # Regression: the post banner (author/date/readtime/tags)
        # used to leak into og:description, making social previews
        # start with "Giampaolo Rodola 2026-01-28 5 min read ...".
        for rst in blog_posts():
            desc = og_value(blog_html(rst), "og:description")
            with subtests.test(rst=rst):
                assert desc is not None
                assert not desc.startswith("Giampaolo")
                assert "min read" not in desc[:80]


@pytest.mark.usefixtures("build_html")
class TestBlogPosts:
    """Rendered blog post pages and the blog index listing."""

    def test_banner_on_every_post(self, subtests):
        css_names = (
            "post-meta-banner",
            "post-meta-author",
            "post-meta-date",
            "post-meta-readtime",
            "post-meta-tags",
        )
        for rst in blog_posts():
            html = blog_html(rst)
            for css in css_names:
                with subtests.test(rst=rst, css=css):
                    assert css in html

    def test_listing_has_all_posts(self, subtests):
        # blog.html should list all posts, each containing the post's
        # title.
        posts = blog_posts()
        html = read_html("blog.html")
        assert len(re.findall(r'<li class="blog-card[^"]*"', html)) == len(
            posts
        )
        for rst in posts:
            with subtests.test(rst=rst):
                assert post_title(rst) in html

    def test_listing_shows_summary(self, subtests):
        # Each post should have a summary below the title.
        html = read_html("blog.html")
        summaries = re.findall(
            r'<div class="blog-card-summary">(.*?)</div>', html, re.DOTALL
        )
        posts = blog_posts()
        assert len(summaries) == len(posts)
        for i, summary in enumerate(summaries):
            plain = re.sub(r"<[^>]+>", "", summary).strip()
            with subtests.test(card=i):
                assert plain

    def test_featured_pill(self, subtests):
        # Posts with the "featured" tag show a "Featured" pill in
        # their post-meta banner via _ext/post_banner.py. Other posts
        # must not.
        for rst in blog_posts():
            is_featured = "featured" in post_tags(rst)
            html = blog_html(rst)
            with subtests.test(rst=rst, is_featured=is_featured):
                if is_featured:
                    assert "post-meta-featured" in html
                else:
                    assert "post-meta-featured" not in html


@pytest.mark.usefixtures("build_html")
class TestNoExternalAssets:
    """Stylesheets and fonts are self-hosted, not pulled from a CDN."""

    ASSET_LINK_RE = re.compile(
        r'<link\b[^>]*\brel="(?:stylesheet|preload)"[^>]*>', re.IGNORECASE
    )
    HREF_RE = re.compile(r'\bhref="([^"]+)"')

    @staticmethod
    def is_external(url):
        return url.startswith(("http://", "https://", "//"))

    def test_no_external_stylesheets(self, subtests):
        # Analytics <script>s are deliberately external; only links count.
        for page in all_html_pages():
            urls = []
            for tag in self.ASSET_LINK_RE.findall(page.read_text()):
                urls += self.HREF_RE.findall(tag)
            external = [u for u in urls if self.is_external(u)]
            with subtests.test(page=page.relative_to(HTML_DIR)):
                assert external == []

    def test_no_external_css_urls(self, subtests):
        css_dir = HTML_DIR / "_static" / "css"
        for css in sorted(css_dir.glob("*.css")):
            urls = re.findall(r'url\(\s*["\']?([^"\')]+)', css.read_text())
            external = [u for u in urls if self.is_external(u)]
            with subtests.test(css=css.name):
                assert external == []


@pytest.mark.usefixtures("build_html")
class TestFonts:
    """Every @font-face points at a font file that ships in the build."""

    def test_font_face_files_exist(self, subtests):
        css_dir = HTML_DIR / "_static" / "css"
        face_re = re.compile(r"@font-face\s*\{[^}]*\}", re.DOTALL)
        url_re = re.compile(r'url\(\s*["\']?([^"\')]+)')
        found = 0
        for css in sorted(css_dir.glob("*.css")):
            for block in face_re.findall(css.read_text()):
                for url in url_re.findall(block):
                    found += 1
                    resolved = (css.parent / url).resolve()
                    with subtests.test(css=css.name, url=url):
                        assert resolved.is_file()
        assert found > 0


@pytest.mark.usefixtures("build_html")
class TestNoIndex:
    """Utility pages are noindex'd (layout.html); content pages aren't."""

    NOINDEX_RE = re.compile(
        r'<meta[^>]*name="robots"[^>]*content="noindex"', re.IGNORECASE
    )

    def test_utility_pages_noindex(self, subtests):
        for name in ("genindex.html", "py-modindex.html", "404.html"):
            path = HTML_DIR / name
            if not path.is_file():
                continue
            with subtests.test(page=name):
                assert self.NOINDEX_RE.search(path.read_text())

    def test_content_pages_indexable(self, subtests):
        for name in ("index.html", "api.html", "install.html"):
            with subtests.test(page=name):
                assert not self.NOINDEX_RE.search(read_html(name))
