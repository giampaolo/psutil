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


static int
get_zones(malloc_zone_t ***out_zones, unsigned int *out_count) {
    vm_address_t *raw = NULL;
    unsigned int count = 0;
    kern_return_t kr;
    malloc_zone_t **zones;
    malloc_zone_t *zone;

    *out_zones = NULL;
    *out_count = 0;

    kr = malloc_get_all_zones(mach_task_self(), NULL, &raw, &count);
    if (kr == KERN_SUCCESS && raw != NULL && count > 0) {
        *out_zones = (malloc_zone_t **)raw;
        *out_count = count;
        return 1;  // success
    }

    psutil_debug("malloc_get_all_zones() failed; using malloc_default_zone()");

    zones = (malloc_zone_t **)malloc(sizeof(malloc_zone_t *));
    if (!zones) {
        PyErr_NoMemory();
        return -1;
    }

    zone = malloc_default_zone();
    if (!zone) {
        free(zones);
        psutil_runtime_error("malloc_default_zone() failed");
        return -1;
    }

    zones[0] = zone;
    *out_zones = zones;
    *out_count = 1;
    return 0;  // fallback, caller must free()
}


// psutil_heap_info() -> (heap_used, mmap_used)
//
// Return libmalloc heap stats via `malloc_zone_statistics()`.
// Compatible with macOS 10.6+ (Sierra and earlier).
//
// Mapping:
//   - heap_used  ~ size_in_use          (live allocated bytes)
//   - mmap_used  ~ 0                    (no direct stat)
PyObject *
psutil_heap_info(PyObject *self, PyObject *args) {
    malloc_zone_t **zones = NULL;
    unsigned int count = 0;
    uint64_t heap_used = 0;
    uint64_t mmap_used = 0;
    int ok;

    ok = get_zones(&zones, &count);
    if (ok == -1)
        return NULL;

    for (unsigned int i = 0; i < count; i++) {
        malloc_statistics_t stats = {0};
        malloc_zone_statistics(zones[i], &stats);
        heap_used += (uint64_t)stats.size_in_use;
    }

    if (!ok)
        free(zones);

    return Py_BuildValue("KK", heap_used, mmap_used);
}


// Return unused heap memory back to the OS.
PyObject *
psutil_heap_trim(PyObject *self, PyObject *args) {
    malloc_zone_t **zones = NULL;
    unsigned int count = 0;
    int ok;

    ok = get_zones(&zones, &count);
    if (ok == -1)
        return NULL;

    for (unsigned int i = 0; i < count; i++)
        malloc_zone_pressure_relief(zones[i], 0);

    if (!ok)
        free(zones);

    Py_RETURN_NONE;
}
