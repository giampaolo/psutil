# noqa: CPY001

# Slightly adapted from CPython's:
# https://github.com/python/cpython/blob/main/Doc/tools/extensions/availability.py
# Copyright (c) PSF
# Licensed under the Python Software Foundation License Version 2.

"""Support for `.. availability:: …` directive, to document platform
availability.
"""

from docutils import nodes
from sphinx.locale import _ as sphinx_gettext
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective

logger = logging.getLogger(__name__)

_PLATFORMS = frozenset({
    "AIX",
    "BSD",
    "FreeBSD",
    "Linux",
    "Linux with glibc",
    "macOS",
    "NetBSD",
    "OpenBSD",
    "POSIX",
    "SunOS",
    "UNIX",
    "Windows",
})

_LIBC = frozenset({
    "glibc",
    "musl",
})

KNOWN_PLATFORMS = _PLATFORMS | _LIBC


class Availability(SphinxDirective):
    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True

    def run(self):
        title = sphinx_gettext("Availability")
        sep = nodes.Text(": ")
        parsed, msgs = self.state.inline_text(self.arguments[0], self.lineno)
        pnode = nodes.paragraph(
            title, "", nodes.emphasis(title, title), sep, *parsed, *msgs
        )
        self.set_source_info(pnode)
        cnode = nodes.container("", pnode, classes=["availability"])
        self.set_source_info(cnode)
        if self.content:
            self.state.nested_parse(self.content, self.content_offset, cnode)
        self.parse_platforms()

        return [cnode]

    def parse_platforms(self):
        """Parse platform information from arguments

        Arguments is a comma-separated string of platforms. A platform may
        be prefixed with "not " to indicate that a feature is not available.
        Example:
           .. availability:: Windows, Linux >= 4.2, not glibc
        """
        platforms = {}
        for arg in self.arguments[0].rstrip(".").split(","):
            arg = arg.strip()
            platform, _, version = arg.partition(" >= ")
            if platform.startswith("not "):
                version = False
                platform = platform.removeprefix("not ")
            elif not version:
                version = True
            platforms[platform] = version

        unknown = set(platforms).difference(KNOWN_PLATFORMS)
        if unknown:
            logger.warning(
                "Unknown platform%s or syntax '%s' in '.. availability:: %s', "
                "see %s:KNOWN_PLATFORMS for a set of known platforms.",
                "s" if len(platforms) != 1 else "",
                " ".join(sorted(unknown)),
                self.arguments[0],
                __file__,
                location=self.get_location(),
            )

        return platforms


def setup(app):
    app.add_directive("availability", Availability)
    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
