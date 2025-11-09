#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for psutil.malloc_* functions."""

import ctypes
import gc
import mmap

import pytest

import psutil
from psutil import LINUX
from psutil import POSIX
from psutil import WINDOWS

from . import PsutilTestCase
from . import retry_on_failure

HEAP_SIZE = 64 * 1024  # 64 KiB
MMAP_SIZE = 10 * 1024 * 1024  # 10 MiB  (large enough to trigger mmap())


# =====================================================================
# --- UNIX utils
# =====================================================================


if POSIX:

    libc = ctypes.CDLL(None)

    # --- malloc/free wrappers for small heap allocations

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

    # --- mmap/munmap wrappers for large allocations

    PROT_READ = 1
    PROT_WRITE = 2
    MAP_PRIVATE = 2
    MAP_ANONYMOUS = getattr(mmap, "MAP_ANONYMOUS", 0x20)  # fallback

    PAGE_SIZE = 4096

    def touch(ptr, size):
        """Write one byte per page to force memory commitment."""
        array_type = ctypes.c_char * size
        buf = array_type.from_address(ptr)
        for i in range(0, size, PAGE_SIZE):
            buf[i] = b"x"[0]

    def mmap_alloc(size):
        """Allocate memory via mmap(), affects mmap_used."""
        fun = libc.mmap
        fun.argtypes = [
            ctypes.c_void_p,  # addr
            ctypes.c_size_t,  # length
            ctypes.c_int,  # prot
            ctypes.c_int,  # flags
            ctypes.c_int,  # fd
            ctypes.c_size_t,  # offset
        ]
        fun.restype = ctypes.c_void_p
        ptr = fun(
            0,
            size,
            PROT_READ | PROT_WRITE,
            MAP_PRIVATE | MAP_ANONYMOUS,
            -1,
            0,
        )
        assert ptr != ctypes.c_void_p(-1).value, "mmap() failed"
        touch(ptr, MMAP_SIZE)
        return ptr

    def munmap_free(ptr, size):
        """Free memory allocated via mmap()."""
        fun = libc.munmap
        fun.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
        fun.restype = ctypes.c_int
        ret = fun(ptr, size)
        assert ret == 0, "munmap() failed"


# =====================================================================
# --- Windows utils
# =====================================================================


elif WINDOWS:
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


@pytest.mark.skipif(not POSIX, reason="not POSIX")
class TestMallocUnix(MallocTestCase):

    @retry_on_failure()
    def test_heap_used(self):
        """Test that malloc() without free() increases heap_used."""
        size = HEAP_SIZE

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

    @retry_on_failure()
    def test_mmap_used(self):
        """Test that large mmap() allocation increases mmap_used."""
        size = MMAP_SIZE

        mem1 = psutil.malloc_info()
        ptr = malloc(size)
        mem2 = psutil.malloc_info()

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
        mem3 = psutil.malloc_info()
        assert_within_percent(mem3.heap_used, mem1.heap_used, percent=10)
        assert_within_percent(mem3.mmap_used, mem1.mmap_used, percent=10)


@pytest.mark.skipif(not WINDOWS, reason="WINDOWS only")
@pytest.mark.xdist_group(name="serial")
class TestMallocWindows(MallocTestCase):

    @retry_on_failure()
    def test_heap_used(self):
        """Test that HeapAlloc() without HeapFree() increases heap_used."""
        size = HEAP_SIZE

        mem1 = psutil.malloc_info()
        heap = GetProcessHeap()
        addr = HeapAlloc(heap, size)
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
        size = MMAP_SIZE

        mem1 = psutil.malloc_info()
        addr = VirtualAllocEx(size)
        mem2 = psutil.malloc_info()

        try:
            assert mem2.mmap_used - mem1.mmap_used == size
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
        heap = HeapCreate(HEAP_SIZE, 0)
        mem2 = psutil.malloc_info()
        try:
            assert mem2.heap_count == mem1.heap_count + 1
            assert mem2.heap_used == mem1.heap_used
            assert mem2.mmap_used == mem1.mmap_used
        finally:
            HeapDestroy(heap)

        mem3 = psutil.malloc_info()
        assert mem3 == mem1
