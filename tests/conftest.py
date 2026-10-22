# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Pytest hooks."""

import warnings

import pytest

# Activate pytest hooks defined in test_process_all.py.
from .test_process_all import pytest_runtest_makereport  # noqa: F401
from .test_process_all import pytest_terminal_summary  # noqa: F401


def _escape_surrogates(text):
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return text.encode("utf-8", "backslashreplace").decode("utf-8")
    else:
        return text


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_logreport(report):
    """Escape the non-UTF8 paths used by test_unicode.py when a test
    fails. If one of them ends up in a report, xdist can't send it to
    the master process, and the whole run dies.
    """
    if isinstance(report.longrepr, tuple):
        path, lineno, reason = report.longrepr
        report.longrepr = (path, lineno, _escape_surrogates(reason))
    elif report.longrepr is not None:
        text = str(report.longrepr)
        escaped = _escape_surrogates(text)
        if escaped != text:
            report.longrepr = escaped
    report.sections = [
        (name, _escape_surrogates(content))
        for name, content in report.sections
    ]


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
