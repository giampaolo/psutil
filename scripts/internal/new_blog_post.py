#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Create a skeleton RST file for a new blog post at
docs/blog/<year>/<slug>.rst. Invoke via `make blog-post` from docs/.
"""

import argparse
import datetime
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
AUTHOR = "Giampaolo Rodola"

SLUG = ""
TITLE = ""
TAGS = ""


def parse_cli():
    global SLUG, TITLE, TAGS

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "slug", help="URL slug, e.g. 'event-driven-process-waiting'"
    )
    parser.add_argument(
        "--title",
        default=None,
        help=(
            "Post title. If omitted, derived from the slug, e.g. "
            "'my-new-post' -> 'My new post'."
        ),
    )
    parser.add_argument(
        "--tags",
        default="",
        help="Comma-separated tags, e.g. 'performance, linux'",
    )
    args = parser.parse_args()

    SLUG = args.slug
    TITLE = args.title or args.slug.replace("-", " ").capitalize()
    TAGS = args.tags


SKELETON = """\
.. post:: {date}
   :tags: {tags}
   :author: {author}
   :exclude:

   One-line summary for listing cards and Atom feeds.

{title}
{underline}

Opening paragraph.

Section
-------

Body.
"""


def main():
    parse_cli()
    today = datetime.date.today()
    year_dir = REPO_ROOT / "docs" / "blog" / str(today.year)
    year_dir.mkdir(parents=True, exist_ok=True)
    path = year_dir / f"{SLUG}.rst"
    if path.exists():
        print(f"error: {path} already exists", file=sys.stderr)
        return 1
    content = SKELETON.format(
        date=today.isoformat(),
        tags=TAGS,
        author=AUTHOR,
        title=TITLE,
        underline="=" * len(TITLE),
    )
    path.write_text(content)
    print(f"created: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
