/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <stdlib.h>
#include <malloc_np.h>

#include "../../arch/all/init.h"

#define _STRINGIFY(x) #x
#define STRINGIFY(x) _STRINGIFY(x)


// Return low-level heap statistics from the C allocator. Return
// jemalloc heap stats via `mallctl()`. Mimics Linux `mallinfo2()`:
//   - heap_used  ~ stats.allocated  (like `uordblks`)
//   - mmap_used  ~ stats.mapped     (like `hblkhd`)
//   - heap_total ~ stats.active     (similar to `arena`)
PyObject *
psutil_malloc_info(PyObject *self, PyObject *args) {
    uint64_t epoch = 0;
    uint64_t allocated = 0, active = 0, mapped = 0;
    size_t sz_epoch = sizeof(epoch);
    size_t sz_val;
    int ret;

    // Read current epoch
    ret = mallctl("epoch", &epoch, &sz_epoch, NULL, 0);
    if (ret != 0)
        return psutil_oserror_wsyscall("mallctl('epoch')");

    // Refresh stats
    ret = mallctl("epoch", NULL, NULL, &epoch, sz_epoch);
    if (ret != 0)
        return psutil_oserror_wsyscall("mallctl('epoch') update");

    // Read stats
    sz_val = sizeof(allocated);
    ret = mallctl("stats.allocated", &allocated, &sz_val, NULL, 0);
    if (ret != 0)
        return psutil_oserror_wsyscall("mallctl('stats.allocated')");

    sz_val = sizeof(mapped);
    ret = mallctl("stats.mapped", &mapped, &sz_val, NULL, 0);
    if (ret != 0)
        return psutil_oserror_wsyscall("mallctl('stats.mapped')");

    sz_val = sizeof(active);
    ret = mallctl("stats.active", &active, &sz_val, NULL, 0);
    if (ret != 0)
        return psutil_oserror_wsyscall("mallctl('stats.active')");

    return Py_BuildValue("KKK", allocated, mapped, active);
}


// Release unused memory from all jemalloc arenas back to the OS.
// Aggressively purges free pages from all arenas (main + per-thread).
// More effective than Linux `malloc_trim(0)`.
PyObject *
psutil_malloc_trim(PyObject *self, PyObject *args) {
    int ret = mallctl(
        "arena." STRINGIFY(MALLCTL_ARENAS_ALL) ".purge", NULL, NULL, NULL, 0
    );
    if (ret != 0)
        return psutil_oserror();
    Py_RETURN_NONE;
}
