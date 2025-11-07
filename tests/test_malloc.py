#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for psutil.malloc_* functions."""

import ctypes
import gc

import pytest

import psutil
from psutil import LINUX
from psutil import WINDOWS

from . import PsutilTestCase

if hasattr(psutil._psplatform, "malloc_info"):
    malloc_info = psutil._psplatform.malloc_info
    malloc_trim = psutil._psplatform.malloc_trim


MALLOC_SIZE = 10 * 1024 * 1024  # 10M


def leak_large_malloc():
    """Emulate a malloc() call in C."""
    # allocate X MB
    ptr = ctypes.create_string_buffer(MALLOC_SIZE)
    # touch all memory (like memset(p, 0, size))
    ptr.raw = b'\x00' * len(ptr)
    return ptr


def free_pointer(ptr):
    del ptr
    gc.collect()
    malloc_trim()


@pytest.mark.xdist_group(name="serial")
class TestMallocInfo(PsutilTestCase):
    def test_increase(self):
        mem1 = malloc_info()
        ptr = leak_large_malloc()
        mem2 = malloc_info()
        free_pointer(ptr)

        assert mem2.heap_used > mem1.heap_used
        assert mem2.mmap_used > mem1.mmap_used

        if LINUX:
            # malloc(10 MB) forces glibc to use mmap(), not the heap,
            # and malloc_info().mmap_used (which is hblkhd) does
            # increase by ~10 MB. On Linux, the entire 10 MB goes into
            # mmap_used.
            diff = (mem2.heap_used - mem1.heap_used) + (
                mem2.mmap_used - mem1.mmap_used
            )
        else:
            diff = mem2.heap_used - mem1.heap_used

        assert abs(MALLOC_SIZE - diff) < 50 * 1024  # 50KB tolerance


if WINDOWS:
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
    @pytest.mark.xdist_group(name="serial")
    class TestMallocWindows(PsutilTestCase):
        def test_heap_count(self):
            """Test that HeapCreate() without HeapDestroy() increases
            heap_count.
            """
            initial = malloc_info().heap_count

            heap = HeapCreate(HEAP_NO_SERIALIZE, 1024 * 1024, 0)
            assert heap != 0, "HeapCreate failed"

            try:
                assert malloc_info().heap_count == initial + 1
            finally:
                HeapDestroy(heap)

            assert malloc_info().heap_count == initial
