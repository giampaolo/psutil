# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Pytest hooks."""

import warnings

# Activate pytest hooks defined in test_process_all.py.
from .test_process_all import pytest_runtest_makereport  # noqa: F401
from .test_process_all import pytest_terminal_summary  # noqa: F401

# Monkey patch pytest-instafail so that we ALSO get the full
# traceback/failure summary at the end of the run, see:
# https://github.com/pytest-dev/pytest-instafail/issues/21.
try:
    import pytest_instafail
    from _pytest.terminal import TerminalReporter

    pytest_instafail.InstafailingTerminalReporter  # noqa: B018
except (ImportError, AttributeError):
    warnings.warn(
        "failed to monkey patch pytest-instafail",
        category=DeprecationWarning,
        stacklevel=2,
    )
else:
    pytest_instafail.InstafailingTerminalReporter.summary_failures = (
        TerminalReporter.summary_failures
    )
    pytest_instafail.InstafailingTerminalReporter.summary_errors = (
        TerminalReporter.summary_errors
    )
