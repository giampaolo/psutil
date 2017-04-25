#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Run unit tests. This is invoked by:

$ python -m psutil.tests
"""

import optparse
import os
import sys

from psutil.tests import install_pip
from psutil.tests import install_test_deps
from psutil.tests import run_suite
from psutil.tests import TEST_DEPS


PYTHON = os.path.basename(sys.executable)


def main():
    usage = "%s -m psutil.tests [opts]" % PYTHON
    parser = optparse.OptionParser(usage=usage, description="run unit tests")
    parser.add_option("-i", "--install-deps",
                      action="store_true", default=False,
                      help="don't print status messages to stdout")

    opts, args = parser.parse_args()
    if opts.install_deps:
        install_pip()
        install_test_deps()
    else:
        for dep in TEST_DEPS:
            try:
                __import__(dep.split("==")[0])
            except ImportError:
                sys.exit("%r lib is not installed; run:\n"
                         "%s -m psutil.tests --install-deps" % (dep, PYTHON))
        run_suite()


main()
