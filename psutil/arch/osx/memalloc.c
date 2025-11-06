/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <malloc/malloc.h>

#include "../../arch/all/init.h"


// psutil_malloc_info() -> (heap_used, mmap_used, heap_total)
//
// Return libmalloc heap stats via `malloc_zone_statistics()`.
// Compatible with macOS 10.6+ (Sierra and earlier).
//
// Mapping:
//   - heap_used  ~ size_in_use          (live allocated bytes)
//   - mmap_used  ~ 0                    (no direct stat)
//   - heap_total ~ size_allocated       (total committed)
PyObject *
psutil_malloc_info(PyObject *self, PyObject *args) {
    malloc_statistics_t stats = {0};
    malloc_zone_t *zone = malloc_default_zone();

    if (!zone)
        return psutil_runtime_error("malloc_default_zone() failed");

    malloc_zone_statistics(zone, &stats);

    uint64_t heap_used = (uint64_t)stats.size_in_use;
    uint64_t mmap_used = 0;
    uint64_t heap_total = (uint64_t)stats.size_allocated;

    return Py_BuildValue("KKK", heap_used, mmap_used, heap_total);
}


PyObject *
psutil_malloc_trim(PyObject *self, PyObject *args) {
    malloc_zone_t *zone = malloc_default_zone();

    if (!zone)
        return psutil_runtime_error("malloc_default_zone() failed");
    malloc_zone_pressure_relief(zone, 0);  // 0 = release all possible
    Py_RETURN_NONE;
}
