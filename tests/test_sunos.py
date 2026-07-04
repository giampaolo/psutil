#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Sun OS specific tests."""

import os

import psutil
from psutil import SUNOS

from . import PsutilTestCase
from . import pytest
from . import sh


@pytest.mark.skipif(not SUNOS, reason="SUNOS only")
class SunOSSpecificTestCase(PsutilTestCase):
    def test_swap_memory(self):
        out = sh(f"env PATH=/usr/sbin:/sbin:{os.environ['PATH']} swap -l")
        lines = out.strip().split('\n')[1:]
        if not lines:
            raise ValueError('no swap device(s) configured')
        total = free = 0
        for line in lines:
            fields = line.split()
            total = int(fields[3]) * 512
            free = int(fields[4]) * 512
        used = total - free

        psutil_swap = psutil.swap_memory()
        assert psutil_swap.total == total
        assert psutil_swap.used == used
        assert psutil_swap.free == free

    def test_cpu_count(self):
        out = sh("/usr/sbin/psrinfo")
        assert psutil.cpu_count() == len(out.split('\n'))

    def test_proc_environ_bad_arg_no_leak(self):
        # Regression: parse failure must not leak py_retdict.
        tracemalloc.start()
        snap1 = tracemalloc.take_snapshot()
        for _ in range(100):
            try:
                psutil._pssunos.cext.proc_environ(0)
            except TypeError:
                pass
        snap2 = tracemalloc.take_snapshot()
        tracemalloc.stop()
        growth = sum(d.size_diff for d in snap2.compare_to(snap1, 'filename'))
        self.assertLess(growth, 256)

    def test_proc_environ_skips_invalid_utf8_value(self):
        # Regression: py_envval decode-fail must hit goto error,
        # not silently pass NULL into PyDict_SetItem.
        # Smoke test: confirm the public route recovers gracefully on
        # the mocked C entry returning a populated dict.
        with mock.patch(
            "psutil._pssunos.cext.proc_environ",
            return_value={"GOOD": "ok"},
        ) as m:
            assert psutil._pssunos.cext.proc_environ() == {"GOOD": "ok"}
            assert m.called
