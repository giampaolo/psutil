#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for psutil.malloc_* functions."""

import pytest

import psutil
from psutil import WINDOWS

from . import PsutilTestCase

if hasattr(psutil._psplatform, "malloc_info"):
    malloc_info = psutil._psplatform.malloc_info


if WINDOWS:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    HEAP_NO_SERIALIZE = 0x00000001

    def HeapCreate(opts, initial_size, max_size):
        fun = kernel32.HeapCreate
        fun.argtypes = [
            wintypes.DWORD,
            ctypes.c_size_t,
            ctypes.c_size_t,
        ]
        fun.restype = wintypes.HANDLE
        heap = fun(opts, initial_size, max_size)
        assert heap != 0, "HeapCreate failed"
        return heap

    def HeapDestroy(heap):
        fun = kernel32.HeapDestroy
        fun.argtypes = [wintypes.HANDLE]
        fun.restype = wintypes.BOOL
        assert fun(heap) != 0, "HeapDestroy failed"


@pytest.mark.skipif(not WINDOWS, reason="WINDOWS only")
class TestMallocWindows(PsutilTestCase):
    def test_heap_count(self):
        initial = malloc_info().heap_count

        heap = HeapCreate(HEAP_NO_SERIALIZE, 1024 * 1024, 0)
        assert heap != 0, "HeapCreate failed"

        try:
            assert malloc_info().heap_count == initial + 1
        finally:
            HeapDestroy(heap)

        assert malloc_info().heap_count == initial
