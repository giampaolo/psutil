#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for psutil.malloc_* functions."""

import ctypes
import gc

import pytest

import psutil
from psutil import POSIX
from psutil import WINDOWS

from . import PsutilTestCase
from . import retry_on_failure

MALLOC_SIZE = 10 * 1024 * 1024  # 10M


class MallocTestCase(PsutilTestCase):
    def setUp(self):
        trim_memory()

    @classmethod
    def tearDownClass(cls):
        trim_memory()


def trim_memory():
    gc.collect()
    psutil.malloc_trim()


def assert_within_percent(actual, expected, percent):
    """Assert that `actual` is within `percent` tolerance of `expected`."""
    lower = expected * (1 - percent / 100)
    upper = expected * (1 + percent / 100)
    if not (lower <= actual <= upper):
        raise AssertionError(
            f"{actual} is not within {percent}% tolerance of expected"
            f" {expected} (allowed range: {lower} - {upper})"
        )


if POSIX:
    libc = ctypes.CDLL(None)

    def malloc(size):
        """Allocate memory via malloc(), affects heap_used."""
        fun = libc.malloc
        fun.argtypes = [ctypes.c_size_t]
        fun.restype = ctypes.c_void_p
        ptr = fun(size)
        assert ptr, "malloc() failed"
        return ptr

    def free(ptr):
        """Free malloc() memory."""
        fun = libc.free
        fun.argtypes = [ctypes.c_void_p]
        fun.restype = None
        fun(ptr)


# --- tests


@pytest.mark.skipif(not POSIX, reason="not POSIX")
class TestMallocUnix(MallocTestCase):
    MALLOC_SIZE = 64 * 1024  # 64 KiB

    @retry_on_failure()
    def test_heap_used(self):
        """Test that malloc() without free() increases heap_used."""
        size = self.MALLOC_SIZE

        mem1 = psutil.malloc_info()
        ptr = malloc(size)
        mem2 = psutil.malloc_info()

        try:
            # heap_used should increase (roughly) by the requested size
            diff = mem2.heap_used - mem1.heap_used
            assert diff > 0
            assert_within_percent(diff, size, percent=10)

            # mmap_used should not increase for small allocations, but
            # sometimes it does.
            diff = mem2.mmap_used - mem1.mmap_used
            if diff != 0:
                assert diff > 0
                assert_within_percent(diff, size, percent=10)
        finally:
            free(ptr)

        # assert we returned close to the baseline (mem1) after free()
        trim_memory()
        mem3 = psutil.malloc_info()
        assert_within_percent(mem3.heap_used, mem1.heap_used, percent=10)
        assert_within_percent(mem3.mmap_used, mem1.mmap_used, percent=10)


if WINDOWS:
    from ctypes import wintypes

    import win32api
    import win32con
    import win32process

    kernel32 = ctypes.windll.kernel32
    HEAP_NO_SERIALIZE = 0x00000001

    # --- for `heap_used`

    def GetProcessHeap():
        fun = kernel32.GetProcessHeap
        fun.argtypes = []
        fun.restype = wintypes.HANDLE
        heap = fun()
        assert heap != 0, "GetProcessHeap failed"
        return heap

    def HeapAlloc(heap, size):
        fun = kernel32.HeapAlloc
        fun.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_size_t]
        fun.restype = ctypes.c_void_p
        addr = fun(heap, 0, size)
        assert addr, "HeapAlloc failed"
        return addr

    def HeapFree(heap, addr):
        fun = kernel32.HeapFree
        fun.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p]
        fun.restype = wintypes.BOOL
        assert fun(heap, 0, addr) != 0, "HeapFree failed"

    # --- for `mmap_used`

    def VirtualAllocEx(size):
        return win32process.VirtualAllocEx(
            win32api.GetCurrentProcess(),
            0,
            size,
            win32con.MEM_COMMIT | win32con.MEM_RESERVE,
            win32con.PAGE_READWRITE,
        )

    def VirtualFreeEx(addr):
        win32process.VirtualFreeEx(
            win32api.GetCurrentProcess(), addr, 0, win32con.MEM_RELEASE
        )

    # --- for `heap_count`

    def HeapCreate(initial_size, max_size):
        fun = kernel32.HeapCreate
        fun.argtypes = [
            wintypes.DWORD,
            ctypes.c_size_t,
            ctypes.c_size_t,
        ]
        fun.restype = wintypes.HANDLE
        heap = fun(HEAP_NO_SERIALIZE, initial_size, max_size)
        assert heap != 0, "HeapCreate failed"
        return heap

    def HeapDestroy(heap):
        fun = kernel32.HeapDestroy
        fun.argtypes = [wintypes.HANDLE]
        fun.restype = wintypes.BOOL
        assert fun(heap) != 0, "HeapDestroy failed"

    # ---

    @pytest.mark.skipif(not WINDOWS, reason="WINDOWS only")
    @pytest.mark.xdist_group(name="serial")
    class TestMallocWindows(MallocTestCase):

        @retry_on_failure()
        def test_heap_used(self):
            """Test that HeapAlloc() without HeapFree() increases heap_used."""
            # Note: a bigger size puts the memory into `mmap_used`
            # instead, so we keep it small on purpose.
            size = 64 * 1024

            mem1 = psutil.malloc_info()
            heap = GetProcessHeap()
            addr = HeapAlloc(heap, 64 * 1024)
            mem2 = psutil.malloc_info()

            try:
                assert mem2.heap_used - mem1.heap_used == size
                assert mem2.mmap_used == mem1.mmap_used
                assert mem2.heap_count == mem1.heap_count
            finally:
                HeapFree(heap, addr)

            mem3 = psutil.malloc_info()
            assert mem3 == mem1

        @retry_on_failure()
        def test_mmap_used(self):
            """Test that VirtualAllocEx() without VirtualFreeEx() increases
            mmap_used.
            """
            mem1 = psutil.malloc_info()
            addr = VirtualAllocEx(MALLOC_SIZE)
            mem2 = psutil.malloc_info()

            try:
                assert mem2.mmap_used - mem1.mmap_used == MALLOC_SIZE
                assert mem2.heap_used == mem1.heap_used
                assert mem2.heap_count == mem1.heap_count
            finally:
                VirtualFreeEx(addr)

            mem3 = psutil.malloc_info()
            assert mem3 == mem1

        @retry_on_failure()
        def test_heap_count(self):
            """Test that HeapCreate() without HeapDestroy() increases
            heap_count.
            """
            mem1 = psutil.malloc_info()
            heap = HeapCreate(1024 * 1024, 0)
            mem2 = psutil.malloc_info()
            try:
                assert mem2.heap_count == mem1.heap_count + 1
                assert mem2.heap_used == mem1.heap_used
                assert mem2.mmap_used == mem1.mmap_used
            finally:
                HeapDestroy(heap)

            mem3 = psutil.malloc_info()
            assert mem3 == mem1
