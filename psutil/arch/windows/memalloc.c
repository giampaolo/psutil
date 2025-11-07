/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */


#include <Python.h>
#include <windows.h>
#include <malloc.h>


// Returns:
// - heap_used:  sum of used blocks (like uordblks)
// - mmap_used:  VirtualAlloc'd regions (like hblkhd)
// - heap_total: total committed heap (like arena)
PyObject *
psutil_malloc_info(PyObject *self, PyObject *args) {
    HANDLE process = GetCurrentProcess();
    MEMORY_BASIC_INFORMATION mbi;
    LPVOID addr = NULL;
    SIZE_T used = 0;
    SIZE_T total_heap = 0;
    SIZE_T mmap_used = 0;
    SIZE_T heap_total;
    _HEAPINFO hinfo = {0};
    hinfo._pentry = NULL;
    int status;

    // CRT heap walk (small allocations)
    while ((status = _heapwalk(&hinfo)) == _HEAPOK) {
        total_heap += hinfo._size;
        if (hinfo._useflag == _USEDENTRY) {
            used += hinfo._size;
        }
    }

    if (status != _HEAPEND && status != _HEAPEMPTY)
        return psutil_runtime_error("_heapwalk failed");

    // VirtualAlloc'd regions (large allocations / mmap equivalent)
    while (VirtualQuery(addr, &mbi, sizeof(mbi)) == sizeof(mbi)) {
        if (mbi.State == MEM_COMMIT && mbi.Type == MEM_PRIVATE) {
            // Exclude CRT heap (already counted above)
            if (!(mbi.AllocationProtect & PAGE_READWRITE)
                || mbi.RegionSize < 64 * 1024)
            {
                // Heuristic: small RW regions are likely heap
                // Skip to avoid double-counting
            }
            else {
                mmap_used += mbi.RegionSize;
            }
        }
        addr = (LPBYTE)mbi.BaseAddress + mbi.RegionSize;
    }

    heap_total = total_heap + mmap_used;

    // heap_used  = CRT heap used
    // mmap_used  = VirtualAlloc'd (large)
    // heap_total = CRT heap total + mmap
    return Py_BuildValue(
        "nnn", (Py_ssize_t)used, (Py_ssize_t)mmap_used, (Py_ssize_t)heap_total
    );
}
