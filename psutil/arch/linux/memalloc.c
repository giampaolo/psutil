/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <malloc.h>
#include <dlfcn.h>

#include "../../arch/all/init.h"


PyObject *
psutil_malloc_info(PyObject *self, PyObject *args) {
    void *handle;
    void *fun;
    void *mi;
    const char *fmt;

    handle = dlopen("libc.so.6", RTLD_LAZY);
    if (handle)
        fun = dlsym(handle, "mallinfo2");
    else
        fun = NULL;

    if (fun != NULL) {
        // mallinfo2() appeared in glibc 2.33, February 2021.
        static struct mallinfo2 m2;
        m2 = ((struct mallinfo2(*)(void))fun)();
        fmt = "KKK";
        mi = &m2;
    }
    else {
        // mallinfo() is deprecated. It uses 'int' fields which overflow for
        // heaps > 2 GiB.
        static struct mallinfo m1;
        psutil_debug("WARNING: using deprecated mallinfo()");
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wdeprecated-declarations"
        m1 = mallinfo();
#pragma GCC diagnostic pop
        fmt = "iii";
        mi = &m1;
    }

    if (handle)
        dlclose(handle);

    return Py_BuildValue(
        fmt,
        // Total allocated space via `malloc` (bytes currently in use by app)
        (unsigned long long)((struct mallinfo2 *)mi)->uordblks,
        // Bytes in `mmap`-ed regions (large allocations). Should be stable
        // unless you're allocating huge blocks.
        (unsigned long long)((struct mallinfo2 *)mi)->hblkhd,
        // non-mmapped heap space
        (unsigned long long)((struct mallinfo2 *)mi)->arena
    );
}


// Release unused memory held by the allocator back to the OS.
PyObject *
psutil_malloc_release(PyObject *self, PyObject *args) {
    // malloc_trim returns 1 if some memory was released, else 0.
    int ret = malloc_trim(0);
    return PyBool_FromLong(ret);
}
