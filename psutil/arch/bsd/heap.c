/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#if defined(PSUTIL_FREEBSD) || defined(PSUTIL_NETBSD)
#include <Python.h>
#include <stdlib.h>
#if defined(PSUTIL_FREEBSD)
#include <malloc_np.h>
#else
#include <malloc.h>
#endif

#include "../../arch/all/init.h"


// Return low-level heap statistics from the C allocator. Return
// jemalloc heap stats via `mallctl()`. Mimics Linux `mallinfo2()`:
//   - heap_used  ~ stats.allocated  (like `uordblks`)
//   - mmap_used  ~ stats.mapped     (like `hblkhd`)
PyObject *
psutil_heap_info(PyObject *self, PyObject *args) {
    uint64_t epoch = 0;
    uint64_t allocated = 0, active = 0, mapped = 0;
    size_t sz_epoch = sizeof(epoch);
    size_t sz_val;
    int ret;

    // Flush per-thread tcache so small leaks become visible.
    // Originates from https://github.com/giampaolo/psleak/issues/6. In
    // there we had failures for small allocations, which disappeared
    // after we added this.
    ret = mallctl("thread.tcache.flush", NULL, NULL, NULL, 0);
    if (ret != 0)
        return psutil_oserror_wsyscall("mallctl('thread.tcache.flush')");

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

    return Py_BuildValue("KK", allocated, mapped);
}


// Release unused heap memory from all jemalloc arenas back to the OS.
// Aggressively purges free pages from all arenas (main + per-thread).
// More effective than Linux `heap_trim(0)`.
PyObject *
psutil_heap_trim(PyObject *self, PyObject *args) {
    char cmd[32];
    int ret;

#ifdef MALLCTL_ARENAS_ALL
    // FreeBSD. MALLCTL_ARENAS_ALL is a magic number (4096) which means "all
    // arenas".
    str_format(cmd, sizeof(cmd), "arena.%u.purge", MALLCTL_ARENAS_ALL);
    ret = mallctl(cmd, NULL, NULL, NULL, 0);
    if (ret != 0)
        return psutil_oserror();
#else
    // NetBSD. Iterate over all arenas.
    unsigned narenas;
    size_t sz = sizeof(narenas);

    ret = mallctl("arenas.narenas", &narenas, &sz, NULL, 0);
    if (ret != 0)
        return psutil_oserror_wsyscall("mallctl('arenas.narenas')");

    for (unsigned i = 0; i < narenas; i++) {
        str_format(cmd, sizeof(cmd), "arena.%u.purge", i);
        ret = mallctl(cmd, NULL, NULL, NULL, 0);
        if (ret != 0)
            return psutil_oserror_wsyscall("mallctl('arena.{n}.purge')");
    }
#endif

    Py_RETURN_NONE;
}
#endif  // PSUTIL_FREEBSD || PSUTIL_NETBSD
