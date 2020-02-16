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


class _Runner:

    def __init__(self):
        self.suite = unittest.TestSuite()

    def _iter_testmod_classes(self):
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
                if isinstance(obj, type) and \
                        issubclass(obj, unittest.TestCase):
                    yield obj

    def get_suite(self):
        suite = unittest.TestSuite()
        for obj in self._iter_testmod_classes():
            test = loadTestsFromTestCase(obj)
            suite.addTest(test)
        return suite

    def get_parallel_suite(self):
        ser = unittest.TestSuite()
        par = unittest.TestSuite()
        for obj in self._iter_testmod_classes():
            test = loadTestsFromTestCase(obj)
            if getattr(obj, '_unittest_serial_run', False):
                ser.addTest(test)
            else:
                par.addTest(test)
        return (ser, par)

    def get_lastfail_suite(self):
        # ...from previously failed test run
        suite = unittest.TestSuite()
        if not os.path.isfile(FAILED_TESTS_FNAME):
            return suite
        with open(FAILED_TESTS_FNAME, 'rt') as f:
            names = f.read().split()
        for n in names:
            suite.addTest(unittest.defaultTestLoader.loadTestsFromName(n))
        return suite

    def _save_failed_tests(self, result):
        with open(FAILED_TESTS_FNAME, 'at') as f:
            for t in result.errors + result.failures:
                tname = str(t[0])
                unittest.defaultTestLoader.loadTestsFromName(tname)
                f.write(tname + '\n')

    # --- runners

    def _run(self, suite):
        runner = ColouredRunner(verbosity=VERBOSITY)
        try:
            result = runner.run(suite)
        except (KeyboardInterrupt, SystemExit) as err:
            print("received %s" % err.__class__.__name__, file=sys.stderr)
            result = runner.result
        if not result.wasSuccessful():
            self._save_failed_tests(result)
        return result

    def _finalize(self, success):
        if success:
            safe_rmpath(FAILED_TESTS_FNAME)
        else:
            sys.exit(1)

    def run(self, suite=None):
        if suite is None:
            suite = self.get_suite()
        res = self._run(suite)
        self._finalize(res.wasSuccessful())

    def run_failed(self):
        self.run(self.get_lastfail_suite())

    def run_parallel(self):
        from concurrencytest import ConcurrentTestSuite, fork_for_tests

        ser_suite, par_suite = self.get_parallel_suite()
        par_suite = ConcurrentTestSuite(par_suite, fork_for_tests(4))

        # # run parallel
        t = time.time()
        par = self._run(par_suite)
        par_elapsed = time.time() - t

        # run serial
        t = time.time()
        ser = self._run(ser_suite)
        ser_elapsed = time.time() - t

        # print
        par_fails, par_errs, par_skips = map(len, (par.failures,
                                                   par.errors,
                                                   par.skipped))
        ser_fails, ser_errs, ser_skips = map(len, (ser.failures,
                                                   ser.errors,
                                                   ser.skipped))
        print("-" * 70)
        print(textwrap.dedent("""
            +----------+----------+----------+----------+----------+----------+
            |          |    total | failures |   errors |  skipped |     time |
            +----------+----------+----------+----------+----------+----------+
            | parallel |      %3s |      %3s |      %3s |      %3s |    %.2fs |
            +----------+----------+----------+----------+----------+----------+
            | serial   |      %3s |      %3s |      %3s |      %3s |    %.2fs |
            +----------+----------+----------+----------+----------+----------+
            """ % (par.testsRun, par_fails, par_errs, par_skips, par_elapsed,
                   ser.testsRun, ser_fails, ser_errs, ser_skips, ser_elapsed)))
        print("Ran %s tests in %.3fs" % (par.testsRun + ser.testsRun,
                                         par_elapsed + ser_elapsed))
        ok = par.wasSuccessful() and ser.wasSuccessful()
        if not ok:
            print_color("FAILED", "red")
            sys.exit(1)

    def run_from_name(self, name):
        suite = unittest.TestSuite()
        name = os.path.splitext(os.path.basename(name))[0]
        suite.addTest(unittest.defaultTestLoader.loadTestsFromName(name))
        self.run(suite)


_runner = _Runner()
run_from_name = _runner.run_from_name


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
        _runner.run_parallel()
    else:
        if opts.last_failed:
            _runner.run_failed()
        else:
            _runner.run()


if __name__ == '__main__':
    main()
