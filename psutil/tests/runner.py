#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Unit test runner, providing new features on top of unittest module:
- colourized output
- parallel run (UNIX only)
- print failures/tracebacks on CTRL+C
- re-run failed tests only (make test-failed)
"""

from __future__ import print_function
import atexit
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

try:
    import concurrencytest  # pip install concurrencytest
except ImportError:
    concurrencytest = None

import psutil
from psutil._common import hilite
from psutil._common import print_color
from psutil._common import term_supports_colors
from psutil.tests import APPVEYOR
from psutil.tests import import_module_by_path
from psutil.tests import reap_children
from psutil.tests import safe_rmpath
from psutil.tests import TOX


HERE = os.path.abspath(os.path.dirname(__file__))
VERBOSITY = 1 if TOX else 2
FAILED_TESTS_FNAME = '.failed-tests.txt'
NWORKERS = psutil.cpu_count() or 1

loadTestsFromTestCase = unittest.defaultTestLoader.loadTestsFromTestCase


# =====================================================================
# --- unittest subclasses
# =====================================================================


class ColouredResult(TextTestResult):

    def _print_color(self, s, color, bold=False):
        print_color(s, color, bold=bold, file=self.stream)

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
        self._print_color("skipped: %s" % reason.strip(), "brown")

    def printErrorList(self, flavour, errors):
        flavour = hilite(flavour, "red", bold=flavour == 'ERROR')
        TextTestResult.printErrorList(self, flavour, errors)


class ColouredTextRunner(TextTestRunner):
    resultclass = ColouredResult

    def _makeResult(self):
        # Store result instance so that it can be accessed on
        # KeyboardInterrupt.
        self.result = TextTestRunner._makeResult(self)
        return self.result


# =====================================================================
# --- public API
# =====================================================================


class SuiteLoader:

    testdir = HERE
    skip_files = ['test_memory_leaks.py']
    if "WHEELHOUSE_UPLOADER_USERNAME" in os.environ:
        skip_files.extend(['test_osx.py', 'test_linux.py', 'test_posix.py'])

    def _get_testmods(self):
        return [os.path.join(self.testdir, x)
                for x in os.listdir(self.testdir)
                if x.startswith('test_') and x.endswith('.py') and
                x not in self.skip_files]

    def _iter_testmod_classes(self):
        """Iterate over all test files in this directory and return
        all TestCase classes in them.
        """
        for path in self._get_testmods():
            mod = import_module_by_path(path)
            for name in dir(mod):
                obj = getattr(mod, name)
                if isinstance(obj, type) and \
                        issubclass(obj, unittest.TestCase):
                    yield obj

    def all(self):
        suite = unittest.TestSuite()
        for obj in self._iter_testmod_classes():
            test = loadTestsFromTestCase(obj)
            suite.addTest(test)
        return suite

    def parallel(self):
        serial = unittest.TestSuite()
        parallel = unittest.TestSuite()
        for obj in self._iter_testmod_classes():
            test = loadTestsFromTestCase(obj)
            if getattr(obj, '_serialrun', False):
                serial.addTest(test)
            else:
                parallel.addTest(test)
        return (serial, parallel)

    def last_failed(self):
        # ...from previously failed test run
        suite = unittest.TestSuite()
        if not os.path.isfile(FAILED_TESTS_FNAME):
            return suite
        with open(FAILED_TESTS_FNAME, 'rt') as f:
            names = f.read().split()
        for n in names:
            test = unittest.defaultTestLoader.loadTestsFromName(n)
            suite.addTest(test)
        return suite

    def from_name(self, name):
        suite = unittest.TestSuite()
        if name.endswith('.py'):
            name = os.path.splitext(os.path.basename(name))[0]
        suite.addTest(unittest.defaultTestLoader.loadTestsFromName(name))
        return suite


class Runner:

    def __init__(self):
        self.loader = SuiteLoader()
        self.failed_tnames = set()
        if term_supports_colors() and not APPVEYOR:
            self.runner = ColouredTextRunner(verbosity=VERBOSITY)
        else:
            self.runner = TextTestRunner(verbosity=VERBOSITY)

    def _write_last_failed(self):
        if self.failed_tnames:
            with open(FAILED_TESTS_FNAME, 'wt') as f:
                for tname in self.failed_tnames:
                    f.write(tname + '\n')

    def _save_result(self, result):
        if not result.wasSuccessful():
            for t in result.errors + result.failures:
                tname = t[0].id()
                self.failed_tnames.add(tname)

    def _run(self, suite):
        try:
            result = self.runner.run(suite)
        except (KeyboardInterrupt, SystemExit):
            result = self.runner.result
            result.printErrors()
            raise sys.exit(1)
        else:
            self._save_result(result)
            return result

    def _finalize(self, success):
        if success:
            safe_rmpath(FAILED_TESTS_FNAME)
        else:
            self._write_last_failed()
            print_color("FAILED", "red")
            sys.exit(1)

    def run(self, suite=None):
        """Run tests serially (1 process)."""
        if suite is None:
            suite = self.loader.all()
        result = self._run(suite)
        self._finalize(result.wasSuccessful())

    def run_last_failed(self):
        """Run tests which failed in the last run."""
        self.run(self.loader.last_failed())

    def run_from_name(self, name):
        """Run test by name, e.g.:
        "test_linux.TestSystemCPUStats.test_ctx_switches"
        """
        self.run(self.loader.from_name(name))

    def _parallelize_suite(self, suite):
        def fdopen(*args, **kwds):
            stream = orig_fdopen(*args, **kwds)
            atexit.register(stream.close)
            return stream

        # Monkey patch concurrencytest lib bug (fdopen() stream not closed).
        # https://github.com/cgoldberg/concurrencytest/issues/11
        orig_fdopen = os.fdopen
        concurrencytest.os.fdopen = fdopen
        forker = concurrencytest.fork_for_tests(NWORKERS)
        return concurrencytest.ConcurrentTestSuite(suite, forker)

    def run_parallel(self):
        """Run tests in parallel."""
        ser_suite, par_suite = self.loader.parallel()
        par_suite = self._parallelize_suite(par_suite)

        # run parallel
        print("starting parallel tests using %s workers" % NWORKERS)
        t = time.time()
        par = self._run(par_suite)
        par_elapsed = time.time() - t

        # cleanup workers and test subprocesses
        orphans = psutil.Process().children()
        gone, alive = psutil.wait_procs(orphans, timeout=1)
        if alive:
            print_color("alive processes %s" % alive, "red")
            reap_children()

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
        print("Ran %s tests in %.3fs using %s workers" % (
            par.testsRun + ser.testsRun, par_elapsed + ser_elapsed, NWORKERS))
        ok = par.wasSuccessful() and ser.wasSuccessful()
        self._finalize(ok)


runner = Runner()
run_from_name = runner.run_from_name


def _setup():
    if 'PSUTIL_TESTING' not in os.environ:
        # This won't work on Windows but set_testing() below will do it.
        os.environ['PSUTIL_TESTING'] = '1'
    psutil._psplatform.cext.set_testing()


def main():
    _setup()
    usage = "python3 -m psutil.tests [opts] [test-name]"
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

    # test-by-name
    if args:
        if len(args) > 1:
            parser.print_usage()
            return sys.exit(1)
        return runner.run_from_name(args[0])
    elif opts.last_failed:
        runner.run_last_failed()
    elif not opts.parallel:
        runner.run()
    # parallel
    elif concurrencytest is None:
        print_color("concurrencytest module is not installed; "
                    "running serial tests instead", "red")
        runner.run()
    elif NWORKERS == 1:
        print_color("only 1 CPU; running serial tests instead", "red")
        runner.run()
    else:
        runner.run_parallel()


if __name__ == '__main__':
    main()
