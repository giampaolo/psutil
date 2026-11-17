# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Sphinx extension that bans bare ``::`` literal blocks, so code goes
through ``.. code-block:: <lang>`` and gets the right highlighting. A
``.. code-block::`` with no language is not caught.
"""

import docutils.nodes
from sphinx.util import logging

logger = logging.getLogger(__name__)


def check_literal_blocks(app, doctree):
    # Sphinx assigns a default language later (post-transform), so at
    # this point only ``::`` blocks lack one
    for node in doctree.findall(docutils.nodes.literal_block):
        if "language" not in node:
            logger.warning(
                "bare '::' literal block, use '.. code-block:: <lang>'",
                location=node,
            )


def setup(app):
    app.connect("doctree-read", check_literal_blocks)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
