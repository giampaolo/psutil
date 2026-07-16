# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Sphinx role linking `/proc/<file>` paths to Debian's man-pages.
E.g. :proc:`/proc/meminfo`, :proc:`/proc/pid/statm`.
"""

from docutils import nodes

URL = "https://manpages.debian.org/{}(5)"


def proc_role(
    name, rawtext, text, lineno, inliner, options=None, content=None
):
    path = text.strip()
    # /proc/[pid]/stat -> proc_pid_stat
    parts = []
    for seg in path.lstrip("/").split("/"):
        s = seg.strip("[]").lower()
        parts.append("pid" if s == "pid" else s)
    page = "_".join(parts)
    url = URL.format(page)
    ref = nodes.reference(rawtext, "", refuri=url, classes=["proc"])
    ref += nodes.literal(text=path)
    return [ref], []


def setup(app):
    app.add_role("proc", proc_role)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
