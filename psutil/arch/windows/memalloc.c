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
// - heap_total: total committed heap, like `arena` on Linux.
//
// - heap_count: number of heaps (Windows only). Catches `HeapCreate()`
//   without `HeapDestroy()`.
PyObject *
psutil_malloc_info(PyObject *self, PyObject *args) {
    HANDLE process = GetCurrentProcess();
    MEMORY_BASIC_INFORMATION mbi;
    LPVOID addr = NULL;
    SIZE_T heap_used = 0;
    SIZE_T mmap_used = 0;
    SIZE_T heap_total;
    DWORD heap_count;
    SIZE_T crt_heap_total = 0;
    _HEAPINFO hinfo = {0};
    hinfo._pentry = NULL;
    int status;
    int is_heap_region;
    HANDLE *heaps = NULL;

    // Walk CRT heaps to measure used and total heap
    while ((status = _heapwalk(&hinfo)) == _HEAPOK) {
        crt_heap_total += hinfo._size;
        if (hinfo._useflag == _USEDENTRY) {
            heap_used += hinfo._size;
        }
    }

    // Get number of heaps
    heap_count = GetProcessHeaps(0, NULL);
    if (heap_count == 0)
        return psutil_oserror_wsyscall("GetProcessHeaps (1/2)");
    heaps = (HANDLE *)malloc(heap_count * sizeof(HANDLE));
    if (!heaps) {
        PyErr_NoMemory();
        return NULL;
    }
    GetProcessHeaps(heap_count, heaps);

    // VirtualAlloc'd regions (large allocations / mmap|hblkhd equivalent)
    while (VirtualQuery(addr, &mbi, sizeof(mbi)) == sizeof(mbi)) {
        if (mbi.State == MEM_COMMIT && mbi.Type == MEM_PRIVATE
            && (mbi.AllocationProtect & PAGE_READWRITE))
        {
            is_heap_region = 0;
            if (heaps) {
                for (DWORD i = 0; i < heap_count; i++) {
                    if (mbi.AllocationBase == heaps[i]) {
                        is_heap_region = 1;
                        break;
                    }
                }
            }

            if (!is_heap_region) {
                mmap_used += mbi.RegionSize;
            }
        }
        addr = (LPBYTE)mbi.BaseAddress + mbi.RegionSize;
    }

    if (heaps)
        free(heaps);

    heap_total = crt_heap_total + mmap_used;

    return Py_BuildValue(
        "nnnn",
        (Py_ssize_t)heap_used,
        (Py_ssize_t)mmap_used,
        (Py_ssize_t)heap_total,
        (Py_ssize_t)heap_count
    );
}


// Release unused memory from the process heap back to the OS. Return
// the size of the largest committed free block in the heap, in bytes.
// Equivalent to Linux malloc_trim(0).
PyObject *
psutil_malloc_trim(PyObject *self, PyObject *args) {
    HANDLE hHeap = GetProcessHeap();
    SIZE_T largest_free;

    if (hHeap == NULL)
        return psutil_oserror_wsyscall("GetProcessHeap");

    largest_free = HeapCompact(hHeap, 0);
    if (largest_free == 0) {
        if (GetLastError() != NO_ERROR) {
            return psutil_oserror_wsyscall("HeapCompact");
        }
    }
    return Py_BuildValue("K", (unsigned long long)largest_free);
}
