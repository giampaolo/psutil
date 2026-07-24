# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""pytest configuration.

Runs `@isolated` tests under an inter-process reader/writer lock when
pytest-xdist is active. Normal tests take a shared (read) lock;
`@isolated` tests take an exclusive (write) lock.

Once an isolated test holds the write lock, the other workers block
before starting their next test, so it runs with no concurrent psutil
tests in the same `-n auto` run (quiet relative to the other workers,
not the whole host). This is stronger than `@serial`/xdist_group, which
only controls which worker a test runs on.

The lock is reader-preferring, so while an isolated test is still
waiting for the write lock, new normal tests may keep acquiring the read
lock. The guarantee is exclusive execution once acquired, not writer
priority.
"""

import os
import tempfile

import pytest

PARALLEL = "PYTEST_XDIST_WORKER" in os.environ

if PARALLEL:
    import fasteners

    uid = os.environ.get("PYTEST_XDIST_TESTRUNUID", "")
    path = os.path.join(tempfile.gettempdir(), f"psutil-serial-{uid}.lock")
    rwlock = fasteners.InterProcessReaderWriterLock(path)


@pytest.fixture(autouse=True)  # noqa: RUF076
def isolated_test_lock(request):
    if not PARALLEL:
        yield
    elif request.node.get_closest_marker("isolated") is not None:
        with rwlock.write_lock():
            yield
    else:
        with rwlock.read_lock():
            yield
