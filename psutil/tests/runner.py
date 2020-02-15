#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Unit test runner, providing new features on top of unittest module:
- colourized output (error, skip)
- print failures/tracebacks on CTRL+C
- re-run failed tests only (make test-failed)
"""

from __future__ import print_function
import optparse
import os
import sys
import unittest
from unittest import TestResult
from unittest import TextTestResult
from unittest import TextTestRunner
try:
    import ctypes
except ImportError:
    ctypes = None

import psutil
from psutil._common import hilite
from psutil._common import print_color
from psutil._common import term_supports_colors
from psutil.tests import safe_rmpath
from psutil.tests import TOX


HERE = os.path.abspath(os.path.dirname(__file__))
VERBOSITY = 1 if TOX else 2
FAILED_TESTS_FNAME = '.failed-tests.txt'


# =====================================================================
# --- unittest subclasses
# =====================================================================


class ColouredResult(TextTestResult):

    def _print_color(self, s, color, bold=False):
        file = sys.stderr if color == "red" else sys.stdout
        print_color(s, color, bold=bold, file=file)

    def addSuccess(self, test):
        TestResult.addSuccess(self, test)
        self._print_color("OK", "green")

    def addError(self, test, err):
        TestResult.addError(self, test, err)
        self._print_color("ERROR", "red", bold=True)

    def addFailure(self, test, err):
        TestResult.addFailure(self, test, err)
        self._print_color("FAIL", "red")

    def addSkip(self, test, reason):
        TestResult.addSkip(self, test, reason)
        self._print_color("skipped: %s" % reason, "brown")

    def printErrorList(self, flavour, errors):
        flavour = hilite(flavour, "red", bold=flavour == 'ERROR')
        TextTestResult.printErrorList(self, flavour, errors)


class ColouredRunner(TextTestRunner):
    resultclass = ColouredResult if term_supports_colors() else TextTestResult

    def _makeResult(self):
        # Store result instance so that it can be accessed on
        # KeyboardInterrupt.
        self.result = TextTestRunner._makeResult(self)
        return self.result


# =====================================================================
# --- public API
# =====================================================================


def setup_tests():
    if 'PSUTIL_TESTING' not in os.environ:
        # This won't work on Windows but set_testing() below will do it.
        os.environ['PSUTIL_TESTING'] = '1'
    psutil._psplatform.cext.set_testing()


def get_suite(name=None):
    suite = unittest.TestSuite()
    if name is None:
        testmods = [os.path.splitext(x)[0] for x in os.listdir(HERE)
                    if x.endswith('.py') and x.startswith('test_') and not
                    x.startswith('test_memory_leaks')]
        if "WHEELHOUSE_UPLOADER_USERNAME" in os.environ:
            testmods = [x for x in testmods if not x.endswith((
                        "osx", "posix", "linux"))]
        for tm in testmods:
            # ...so that the full test paths are printed on screen
            tm = "psutil.tests.%s" % tm
            suite.addTest(unittest.defaultTestLoader.loadTestsFromName(tm))
    else:
        name = os.path.splitext(os.path.basename(name))[0]
        suite.addTest(unittest.defaultTestLoader.loadTestsFromName(name))
    return suite


def get_suite_from_failed():
    # ...from previously failed test run
    suite = unittest.TestSuite()
    if not os.path.isfile(FAILED_TESTS_FNAME):
        return suite
    with open(FAILED_TESTS_FNAME, 'rt') as f:
        names = f.read().split()
    for n in names:
        suite.addTest(unittest.defaultTestLoader.loadTestsFromName(n))
    return suite


def save_failed_tests(result):
    if result.wasSuccessful():
        return safe_rmpath(FAILED_TESTS_FNAME)
    with open(FAILED_TESTS_FNAME, 'wt') as f:
        for t in result.errors + result.failures:
            tname = str(t[0])
            unittest.defaultTestLoader.loadTestsFromName(tname)
            f.write(tname + '\n')


def run(name=None, last_failed=False):
    setup_tests()
    runner = ColouredRunner(verbosity=VERBOSITY)
    suite = get_suite_from_failed() if last_failed else get_suite(name)
    try:
        result = runner.run(suite)
    except (KeyboardInterrupt, SystemExit) as err:
        print("received %s" % err.__class__.__name__, file=sys.stderr)
        runner.result.printErrors()
        sys.exit(1)
    else:
        save_failed_tests(result)
        success = result.wasSuccessful()
        sys.exit(0 if success else 1)


def main():
    usage = "python3 -m psutil.tests [opts]"
    parser = optparse.OptionParser(usage=usage, description="run unit tests")
    parser.add_option("--last-failed",
                      action="store_true", default=False,
                      help="only run last failed tests")
    opts, args = parser.parse_args()
    run(last_failed=opts.last_failed)


if __name__ == '__main__':
    main()
