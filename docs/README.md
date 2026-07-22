# psutil documentation

This directory is a self-contained Sphinx project that builds the psutil docs
published at https://psutil.io/. It has grown well past a plain API reference
(custom theme, a blog, social cards, its own test suite and deploy pipeline),
so this file is the map.

## Build & preview

    make html          # one-off build into _build/html
    make autoreload    # live-reload server at 127.0.0.1:8000

`make html` turns warnings into errors, same as CI.

## Layout

- `*.rst`: the doc sources. `api.rst` is the hand-written API reference;
  `index.rst` is the home page.
- `blog/`: blog posts, managed by the ablog extension + comments provided via
  giscus.
- `conf.py`: Sphinx config: extensions, the theme, `html_baseurl`, OpenGraph /
  sitemap / feed settings.
- `_templates/`: the custom theme, built on Sphinx's `basic` theme (topbar,
  sidebar, footer, layout).
- `_static/css/`, `_static/js/`: styles and vanilla JS (no framework).
- `_ext/`: small local Sphinx extensions.
- `_extra/robots.txt`: copied verbatim to the site root.

## Notable choices

- Single version, served at the site root (no `/en/`, no `/latest/`).
- Built with the `dirhtml` builder, so URLs are extensionless directories
  (`psutil.io/faq/`, no `.html`).
- Self-hosted on GitHub Pages under the custom domain psutil.io.
- Fonts, CSS and JS are all self-hosted; no external assets.
- Social cards, sitemap and Atom feed are generated at build time and rooted at
  `html_baseurl`.

## Tests

- `test_docs.py`: offline checks on the built HTML (canonical / OG tags,
  sitemap, feed, blog metadata, no external assets, ...). Run with `make test`.
- `test_docs_online.py`: smoke tests against the live site (reachability,
  http->https, 404 page, metadata). Run with `make test-online-doc` (sets
  `PSUTIL_DOCS_ONLINE=1`).

## Deploy

`.github/workflows/docs.yml` runs on pushes / PRs that touch `docs/`: lint
(`make lint-rst`) -> offline tests -> build -> deploy to GitHub Pages ->
live-site tests. Deploy and the live tests run only on push to master, never on
PRs.
