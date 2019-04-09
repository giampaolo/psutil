#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Run unit tests. This is invoked by:

$ python -m psutil.tests
"""

import contextlib
import optparse
import os
import sys
import tempfile
try:
    from urllib.request import urlopen  # py3
except ImportError:
    from urllib2 import urlopen

from psutil.tests import PYTHON_EXE
from psutil.tests.runner import run


HERE = os.path.abspath(os.path.dirname(__file__))
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
TEST_DEPS = []
if sys.version_info[:2] == (2, 6):
    TEST_DEPS.extend(["ipaddress", "unittest2", "argparse", "mock==1.0.1"])
elif sys.version_info[:2] == (2, 7) or sys.version_info[:2] <= (3, 2):
    TEST_DEPS.extend(["ipaddress", "mock"])


def install_pip():
    try:
        import pip  # NOQA
    except ImportError:
        import ssl
        f = tempfile.NamedTemporaryFile(suffix='.py')
        with contextlib.closing(f):
            print("downloading %s to %s" % (GET_PIP_URL, f.name))
            if hasattr(ssl, '_create_unverified_context'):
                ctx = ssl._create_unverified_context()
            else:
                ctx = None
            kwargs = dict(context=ctx) if ctx else {}
            req = urlopen(GET_PIP_URL, **kwargs)
            data = req.read()
            f.write(data)
            f.flush()

            print("installing pip")
            code = os.system('%s %s --user' % (PYTHON_EXE, f.name))
            return code


def install_test_deps(deps=None):
    """Install test dependencies via pip."""
    if deps is None:
        deps = TEST_DEPS
    deps = set(deps)
    if deps:
        is_venv = hasattr(sys, 'real_prefix')
        opts = "--user" if not is_venv else ""
        install_pip()
        code = os.system('%s -m pip install %s --upgrade %s' % (
            PYTHON_EXE, opts, " ".join(deps)))
        return code


def main():
    usage = "%s -m psutil.tests [opts]" % PYTHON_EXE
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
                sys.exit("%r lib is not installed; run %s -m psutil.tests "
                         "--install-deps" % (dep, PYTHON_EXE))
        run()


main()
