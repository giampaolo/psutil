/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <malloc/malloc.h>
#include <mach/mach.h>
#include <mach/vm_map.h>

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


// Release unused memory from the default malloc zone back to the OS.
PyObject *
psutil_malloc_trim(PyObject *self, PyObject *args) {
    vm_address_t *zones = NULL;
    unsigned int count = 0;
    kern_return_t kr;

    // Get list of all malloc zones
    kr = malloc_get_all_zones(mach_task_self(), NULL, &zones, &count);
    if (kr != KERN_SUCCESS || count == 0 || zones == NULL) {
        // Fallback: try default zone only
        malloc_zone_t *default_zone = malloc_default_zone();
        if (default_zone) {
            malloc_zone_pressure_relief(default_zone, 0);
        }
        Py_RETURN_NONE;
    }

    // Trim each zone
    for (unsigned int i = 0; i < count; i++) {
        malloc_zone_t *zone = (malloc_zone_t *)zones[i];
        if (zone) {
            malloc_zone_pressure_relief(zone, 0);
        }
    }

    Py_RETURN_NONE;
}
