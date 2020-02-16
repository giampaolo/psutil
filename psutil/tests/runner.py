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
import textwrap
import time
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
from psutil.tests import import_module_by_path
from psutil.tests import safe_rmpath
from psutil.tests import TOX


HERE = os.path.abspath(os.path.dirname(__file__))
VERBOSITY = 1 if TOX else 2
FAILED_TESTS_FNAME = '.failed-tests.txt'
loadTestsFromTestCase = unittest.defaultTestLoader.loadTestsFromTestCase


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


def _iter_testmod_classes():
    testmods = [os.path.join(HERE, x) for x in os.listdir(HERE)
                if x.endswith('.py') and x.startswith('test_') and not
                x.endswith('test_memory_leaks.py')]
    if "WHEELHOUSE_UPLOADER_USERNAME" in os.environ:
        testmods = [x for x in testmods if not x.endswith((
                    "osx.py", "posix.py", "linux.py"))]
    for path in testmods:
        mod = import_module_by_path(path)
        for name in dir(mod):
            obj = getattr(mod, name)
            if isinstance(obj, type) and issubclass(obj, unittest.TestCase):
                yield obj


def get_suite():
    suite = unittest.TestSuite()
    for obj in _iter_testmod_classes():
        test = loadTestsFromTestCase(obj)
        suite.addTest(test)
    return suite


def get_parallel_suite():
    ser = unittest.TestSuite()
    par = unittest.TestSuite()
    for obj in _iter_testmod_classes():
        test = loadTestsFromTestCase(obj)
        if getattr(obj, '_unittest_serial_run', False):
            ser.addTest(test)
        else:
            par.addTest(test)
    return (ser, par)


def get_failed_suite():
    # ...from previously failed test run
    suite = unittest.TestSuite()
    if not os.path.isfile(FAILED_TESTS_FNAME):
        return suite
    with open(FAILED_TESTS_FNAME, 'rt') as f:
        names = f.read().split()
    for n in names:
        suite.addTest(unittest.defaultTestLoader.loadTestsFromName(n))
    return suite


def _save_failed_tests(result):
    if result.wasSuccessful():
        return safe_rmpath(FAILED_TESTS_FNAME)
    with open(FAILED_TESTS_FNAME, 'at') as f:
        for t in result.errors + result.failures:
            tname = str(t[0])
            unittest.defaultTestLoader.loadTestsFromName(tname)
            f.write(tname + '\n')


def run(suite):
    runner = ColouredRunner(verbosity=VERBOSITY)
    try:
        result = runner.run(suite)
    except (KeyboardInterrupt, SystemExit) as err:
        print("received %s" % err.__class__.__name__, file=sys.stderr)
        runner.result.printErrors()
        sys.exit(1)
    else:
        _save_failed_tests(result)
        success = result.wasSuccessful()
        sys.exit(0 if success else 1)


def run_parallel(ser_suite, par_suite):
    # runner = ColouredRunner(verbosity=VERBOSITY)
    # serial, parallel = get_parallel_suite()
    from concurrencytest import ConcurrentTestSuite, fork_for_tests
    runner = ColouredRunner(verbosity=VERBOSITY)
    par_suite = ConcurrentTestSuite(par_suite, fork_for_tests(4))

    # # run parallel
    t = time.time()
    par = runner.run(par_suite)
    par_elapsed = time.time() - t

    # run serial
    t = time.time()
    ser = runner.run(ser_suite)
    ser_elapsed = time.time() - t

    # print
    par_fails, par_errs, par_skips = map(len, (par.failures,
                                               par.errors,
                                               par.skipped))
    ser_fails, ser_errs, ser_skips = map(len, (ser.failures,
                                               ser.errors,
                                               ser.skipped))
    print(textwrap.dedent("""
        +-----------+----------+----------+----------+----------+----------+
        |           |    total | failures |   errors |  skipped |     time |
        +-----------+----------+----------+----------+----------+----------+
        | parallel  |      %3s |      %3s |      %3s |      %3s |    %.2fs |
        +-----------+----------+----------+----------+----------+----------+
        | serial    |      %3s |      %3s |      %3s |      %3s |    %.2fs |
        +-----------+----------+----------+----------+----------+----------+
        """ % (par.testsRun, par_fails, par_errs, par_skips, par_elapsed,
               ser.testsRun, ser_fails, ser_errs, ser_skips, ser_elapsed,)))
    ok = par.wasSuccessful() and ser.wasSuccessful()
    msg = "%s (ran %s tests in %.3fs)" % (
        hilite("OK", "green") if ok else hilite("FAILED", "red"),
        par.testsRun + ser.testsRun,
        par_elapsed + ser_elapsed)
    print(msg)
    if not ok:
        sys.exit(1)


def _setup():
    if 'PSUTIL_TESTING' not in os.environ:
        # This won't work on Windows but set_testing() below will do it.
        os.environ['PSUTIL_TESTING'] = '1'
    psutil._psplatform.cext.set_testing()


def main():
    _setup()
    usage = "python3 -m psutil.tests [opts]"
    parser = optparse.OptionParser(usage=usage, description="run unit tests")
    parser.add_option("--last-failed",
                      action="store_true", default=False,
                      help="only run last failed tests")
    parser.add_option("--parallel",
                      action="store_true", default=False,
                      help="run tests in parallel")
    opts, args = parser.parse_args()

    if not opts.last_failed:
        safe_rmpath(FAILED_TESTS_FNAME)

    if opts.parallel and not opts.last_failed:
        run_parallel(*get_parallel_suite())
    else:
        if opts.last_failed:
            suite = get_failed_suite()
        else:
            suite = get_suite()
        run(suite)


if __name__ == '__main__':
    main()
