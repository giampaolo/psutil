/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */


#include <Python.h>
#include <windows.h>
#include <malloc.h>

#include "../../arch/all/init.h"


// Returns a tuple with:
//
// - heap_used: sum of used blocks, like `uordblks` on Linux. Catches
//   small `malloc()` without `free()` and small `HeapAlloc()` without
//   `HeapFree()`. If bigger than some KB they go into `mmap_used`.
//
// - mmap_used: VirtualAlloc'd regions, like `hblkhd` on Linux. Catches
//   `VirtualAlloc()` without `VirtualFree()`.
//
// - heap_count (Windows only): number of private heaps. Catches
//   `HeapCreate()` without `HeapDestroy()`.
PyObject *
psutil_heap_info(PyObject *self, PyObject *args) {
    MEMORY_BASIC_INFORMATION mbi;
    LPVOID addr = NULL;
    SIZE_T heap_used = 0;
    SIZE_T mmap_used = 0;
    DWORD heap_count;
    DWORD nhandles;
    _HEAPINFO hinfo = {0};
    hinfo._pentry = NULL;
    int status;
    HANDLE *heaps = NULL;

    // Walk CRT heaps to measure heap used.
    while ((status = _heapwalk(&hinfo)) == _HEAPOK) {
        if (hinfo._useflag == _USEDENTRY) {
            heap_used += hinfo._size;
        }
    }
    if ((status != _HEAPEND) && (status != _HEAPOK))
        return psutil_oserror_wsyscall("_heapwalk");

    // Get number of heaps (+ heap handles).
    nhandles = GetProcessHeaps(0, NULL);  // 1st: get count
    if (nhandles == 0)
        return psutil_oserror_wsyscall("GetProcessHeaps (1/2)");

    heaps = (HANDLE *)malloc(nhandles * sizeof(HANDLE));
    if (!heaps) {
        PyErr_NoMemory();
        return NULL;
    }

    heap_count = GetProcessHeaps(nhandles, heaps);  // 2nd: get heaps handles
    if (heap_count == 0) {
        free(heaps);
        return psutil_oserror_wsyscall("GetProcessHeaps (2/2)");
    }
    // The number of heaps may have changed between the two calls. If
    // it shrank, fewer handles than `nhandles` were stored; if it
    // grew, the extra heaps didn't fit in the buffer. Either way only
    // the first min(heap_count, nhandles) buffer entries are valid.
    if (heap_count != nhandles) {
        psutil_debug(
            "GetProcessHeaps(): heap count changed from %lu to %lu "
            "between the two calls",
            (unsigned long)nhandles,
            (unsigned long)heap_count
        );
        if (heap_count < nhandles)
            nhandles = heap_count;
    }

    // VirtualAlloc'd regions (large allocations / mmap|hblkhd equivalent).
    while (VirtualQuery(addr, &mbi, sizeof(mbi)) == sizeof(mbi)) {
        if (mbi.State == MEM_COMMIT && mbi.Type == MEM_PRIVATE
            && (mbi.AllocationProtect & PAGE_READWRITE))
        {
            int is_heap_region = 0;
            for (DWORD i = 0; i < nhandles; i++) {
                if (mbi.AllocationBase == heaps[i]) {
                    is_heap_region = 1;
                    break;
                }
            }

            if (!is_heap_region) {
                mmap_used += mbi.RegionSize;
            }
        }
        addr = (LPBYTE)mbi.BaseAddress + mbi.RegionSize;
    }

    free(heaps);

    return Py_BuildValue(
        "nnn",
        (Py_ssize_t)heap_used,
        (Py_ssize_t)mmap_used,
        (Py_ssize_t)heap_count
    );
}


// Return unused heap memory back to the OS. Return the size of the
// largest committed free block in the heap, in bytes. Equivalent to
// Linux `heap_trim(0)`.
PyObject *
psutil_heap_trim(PyObject *self, PyObject *args) {
    HANDLE hHeap = GetProcessHeap();
    SIZE_T largest_free;

    if (hHeap == NULL)
        return psutil_oserror_wsyscall("GetProcessHeap");

    // HeapCompact() returns 0 both on error and when the heap has no
    // committed free blocks, in which case last-error is untouched.
    SetLastError(0);
    largest_free = HeapCompact(hHeap, 0);
    if (largest_free == 0) {
        if (GetLastError() != NO_ERROR) {
            return psutil_oserror_wsyscall("HeapCompact");
        }
    }
    return Py_BuildValue("K", (unsigned long long)largest_free);
}
