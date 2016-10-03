#!/usr/bin/env python

# Copyright (C) 2007-2016 Giampaolo Rodola' <g.rodola@gmail.com>.
# Use of this source code is governed by MIT license that can be
# found in the LICENSE file.

"""Script for running all test files (except memory leaks tests)."""

import os
import sys

from psutil.tests import unittest
from psutil.tests import VERBOSITY


HERE = os.path.abspath(os.path.dirname(__file__))
testmodules = [os.path.splitext(x)[0] for x in os.listdir(HERE)
               if x.endswith('.py') and x.startswith('test_') and not
               x.startswith('test_memory_leaks')]
suite = unittest.TestSuite()
for tm in testmodules:
    suite.addTest(unittest.defaultTestLoader.loadTestsFromName(tm))
result = unittest.TextTestRunner(verbosity=VERBOSITY).run(suite)
success = result.wasSuccessful()
sys.exit(0 if success else 1)
