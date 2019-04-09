#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Unit test runner, providing colourized output and printing failures
on KeyboardInterrupt.
"""

from __future__ import print_function
import atexit
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
from psutil._common import memoize
from psutil.tests import safe_rmpath
from psutil.tests import TOX


HERE = os.path.abspath(os.path.dirname(__file__))
VERBOSITY = 1 if TOX else 2
FAILED_TESTS_FNAME = '.failed-tests.txt'
if os.name == 'posix':
    GREEN = 1
    RED = 2
    BROWN = 94
else:
    GREEN = 2
    RED = 4
    BROWN = 6
    DEFAULT_COLOR = 7


def term_supports_colors(file=sys.stdout):
    if os.name == 'nt':
        return ctypes is not None
    try:
        import curses
        assert file.isatty()
        curses.setupterm()
        assert curses.tigetnum("colors") > 0
    except Exception:
        return False
    else:
        return True


def hilite(s, color, bold=False):
    """Return an highlighted version of 'string'."""
    attr = []
    if color == GREEN:
        attr.append('32')
    elif color == RED:
        attr.append('91')
    elif color == BROWN:
        attr.append('33')
    else:
        raise ValueError("unrecognized color")
    if bold:
        attr.append('1')
    return '\x1b[%sm%s\x1b[0m' % (';'.join(attr), s)


@memoize
def _stderr_handle():
    GetStdHandle = ctypes.windll.Kernel32.GetStdHandle
    STD_ERROR_HANDLE_ID = ctypes.c_ulong(0xfffffff4)
    GetStdHandle.restype = ctypes.c_ulong
    handle = GetStdHandle(STD_ERROR_HANDLE_ID)
    atexit.register(ctypes.windll.Kernel32.CloseHandle, handle)
    return handle


def win_colorprint(printer, s, color, bold=False):
    if bold and color <= 7:
        color += 8
    handle = _stderr_handle()
    SetConsoleTextAttribute = ctypes.windll.Kernel32.SetConsoleTextAttribute
    SetConsoleTextAttribute(handle, color)
    try:
        printer(s)
    finally:
        SetConsoleTextAttribute(handle, DEFAULT_COLOR)


class ColouredResult(TextTestResult):

    def _color_print(self, s, color, bold=False):
        if os.name == 'posix':
            self.stream.writeln(hilite(s, color, bold=bold))
        else:
            win_colorprint(self.stream.writeln, s, color, bold=bold)

    def addSuccess(self, test):
        TestResult.addSuccess(self, test)
        self._color_print("OK", GREEN)

    def addError(self, test, err):
        TestResult.addError(self, test, err)
        self._color_print("ERROR", RED, bold=True)

    def addFailure(self, test, err):
        TestResult.addFailure(self, test, err)
        self._color_print("FAIL", RED)

    def addSkip(self, test, reason):
        TestResult.addSkip(self, test, reason)
        self._color_print("skipped: %s" % reason, BROWN)

    def printErrorList(self, flavour, errors):
        flavour = hilite(flavour, RED, bold=flavour == 'ERROR')
        TextTestResult.printErrorList(self, flavour, errors)


class ColouredRunner(TextTestRunner):
    resultclass = ColouredResult if term_supports_colors() else TextTestResult

    def _makeResult(self):
        # Store result instance so that it can be accessed on
        # KeyboardInterrupt.
        self.result = TextTestRunner._makeResult(self)
        return self.result


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
