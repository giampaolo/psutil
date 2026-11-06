# Copyright (c) 2009, Giampaolo Rodola. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Add a `.. soft-deprecated:: VERSION` directive."""

from docutils import nodes
from sphinx.domains.changeset import VersionChange
from sphinx.domains.changeset import versionlabel_classes
from sphinx.domains.changeset import versionlabels


class SoftDeprecated(VersionChange):
    def run(self):
        ret = super().run()
        node = ret[0]
        node["classes"].append("deprecated")  # reuse its CSS
        label = node[0][0]
        term, msgs = self.parse_inline(
            ":term:`Soft deprecated <soft deprecated>`"
        )
        label.insert(0, [*term, nodes.Text(" ")])
        return ret + msgs


def setup(app):
    # "Soft deprecated" is prepended by SoftDeprecated.run()
    versionlabels["soft-deprecated"] = "since version %s"
    versionlabel_classes["soft-deprecated"] = "deprecated"
    app.add_directive("soft-deprecated", SoftDeprecated)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
