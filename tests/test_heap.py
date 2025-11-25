#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for `psutil.heap_info()`.

This module deliberately creates **controlled memory leaks** by calling
low-level C allocation functions (`malloc()`, `HeapAlloc()`,
`VirtualAllocEx()`, etc.) **without** freeing them - exactly how
real-world memory leaks occur in native C extensions code.

By bypassing Python's memory manager entirely (via `ctypes`), we
directly exercise the underlying system allocator:

UNIX

- Small `malloc()` allocations (≤128KB on glibc) without `free()`
  increase `heap_used`.
- Large `malloc()` allocations  without `free()` trigger `mmap()` and
  increase `mmap_used`.
    - Note: direct `mmap()` / `munmap()` via `ctypes` was attempted but
      proved unreliable.

Windows

- `HeapAlloc()` without `HeapFree()` increases `heap_used`.
- `VirtualAllocEx()` without `VirtualFreeEx()` increases `mmap_used`.
- `HeapCreate()` without `HeapDestroy()` increases `heap_count`.

These tests ensure that `psutil.heap_info()` detects unreleased
native memory across different allocators (glibc on Linux,
jemalloc on BSD/macOS, Windows CRT).
"""

import ctypes
import gc

import pytest

import psutil
from psutil import LINUX
from psutil import MACOS
from psutil import POSIX
from psutil import WINDOWS

from . import HAS_HEAP_INFO
from . import PsutilTestCase
from . import retry_on_failure

HEAP_SIZE = 64 * 1024  # 64 KiB
MMAP_SIZE = 10 * 1024 * 1024  # 10 MiB  (large enough to trigger mmap())


# =====================================================================
# --- Utils
# =====================================================================


if POSIX:  # noqa: SIM108
    libc = ctypes.CDLL(None)
else:
    libc = ctypes.CDLL("msvcrt.dll")


def malloc(size):
    """Allocate memory via malloc(). If passed a small size, usually
    affects heap_used, else mmap_used (not on Windows).
    """
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


# =====================================================================
# --- Tests
# =====================================================================


def trim_memory():
    gc.collect()
    psutil.heap_trim()


def assert_within_percent(actual, expected, percent):
    """Assert that `actual` is within `percent` tolerance of `expected`."""
    lower = expected * (1 - percent / 100)
    upper = expected * (1 + percent / 100)
    if not (lower <= actual <= upper):
        raise AssertionError(
            f"{actual} is not within {percent}% tolerance of expected"
            f" {expected} (allowed range: {lower} - {upper})"
        )


@pytest.mark.skipif(not HAS_HEAP_INFO, reason="heap_info() not supported")
class HeapTestCase(PsutilTestCase):
    def setUp(self):
        trim_memory()

    @classmethod
    def tearDownClass(cls):
        trim_memory()


class TestHeap(HeapTestCase):

    # On Windows malloc() increases mmap_used
    @pytest.mark.skipif(WINDOWS, reason="not on WINDOWS")
    @retry_on_failure()
    def test_heap_used(self):
        """Test that a small malloc() allocation without free()
        increases heap_used.
        """
        size = HEAP_SIZE

        mem1 = psutil.heap_info()
        ptr = malloc(size)
        mem2 = psutil.heap_info()

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
        mem3 = psutil.heap_info()
        assert_within_percent(mem3.heap_used, mem1.heap_used, percent=10)
        assert_within_percent(mem3.mmap_used, mem1.mmap_used, percent=10)

    @pytest.mark.skipif(MACOS, reason="not supported")
    @retry_on_failure()
    def test_mmap_used(self):
        """Test that a large malloc allocation increases mmap_used.
        NOTE: `mmap()` / `munmap()` via ctypes proved to be unreliable.
        """
        size = MMAP_SIZE

        mem1 = psutil.heap_info()
        ptr = malloc(size)
        mem2 = psutil.heap_info()

        try:
            # mmap_used should increase (roughly) by the requested size
            diff = mem2.mmap_used - mem1.mmap_used
            assert diff > 0
            assert_within_percent(diff, size, percent=10)

            diff = mem2.heap_used - mem1.heap_used
            if diff != 0:
                if LINUX:
                    # heap_used should not increase significantly
                    assert diff >= 0
                    assert_within_percent(diff, 0, percent=5)
                else:
                    # On BSD jemalloc allocates big memory both into
                    # heap_used and mmap_used.
                    assert_within_percent(diff, size, percent=10)

        finally:
            free(ptr)

        # assert we returned close to the baseline (mem1) after free()
        trim_memory()
        mem3 = psutil.heap_info()
        assert_within_percent(mem3.heap_used, mem1.heap_used, percent=10)
        assert_within_percent(mem3.mmap_used, mem1.mmap_used, percent=10)

        if WINDOWS:
            assert mem1.heap_count == mem2.heap_count == mem3.heap_count


@pytest.mark.skipif(not WINDOWS, reason="WINDOWS only")
@pytest.mark.xdist_group(name="serial")
class TestHeapWindows(HeapTestCase):

    @retry_on_failure()
    def test_heap_used(self):
        """Test that HeapAlloc() without HeapFree() increases heap_used."""
        size = HEAP_SIZE

        mem1 = psutil.heap_info()
        heap = GetProcessHeap()
        addr = HeapAlloc(heap, size)
        mem2 = psutil.heap_info()

        try:
            assert mem2.heap_used - mem1.heap_used == size
        finally:
            HeapFree(heap, addr)

        trim_memory()
        mem3 = psutil.heap_info()
        assert mem3.heap_used == mem1.heap_used

    @retry_on_failure()
    def test_mmap_used(self):
        """Test that VirtualAllocEx() without VirtualFreeEx() increases
        mmap_used.
        """
        size = MMAP_SIZE

        mem1 = psutil.heap_info()
        addr = VirtualAllocEx(size)
        mem2 = psutil.heap_info()

        try:
            assert mem2.mmap_used - mem1.mmap_used == size
        finally:
            VirtualFreeEx(addr)

        trim_memory()
        mem3 = psutil.heap_info()
        assert mem3.mmap_used == mem1.mmap_used

    @retry_on_failure()
    def test_heap_count(self):
        """Test that HeapCreate() without HeapDestroy() increases
        heap_count.
        """
        mem1 = psutil.heap_info()
        heap = HeapCreate(HEAP_SIZE, 0)
        mem2 = psutil.heap_info()
        try:
            assert mem2.heap_count == mem1.heap_count + 1
        finally:
            HeapDestroy(heap)

        trim_memory()
        mem3 = psutil.heap_info()
        assert mem3.heap_count == mem1.heap_count
