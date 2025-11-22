/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include "../../arch/all/init.h"

#if defined(PSUTIL_HAS_MALLOC_INFO)  // not available on musl / alpine
#include <Python.h>
#include <malloc.h>
#include <dlfcn.h>


// A copy of glibc's mallinfo2 layout. Allows compilation even if
// <malloc.h> doesn't define mallinfo2.
struct my_mallinfo2 {
    size_t arena;
    size_t ordblks;
    size_t smblks;
    size_t hblks;
    size_t hblkhd;
    size_t usmblks;
    size_t fsmblks;
    size_t uordblks;
    size_t fordblks;
    size_t keepcost;
};


// psutil_malloc_info() -> (heap_used, mmap_used, heap_total)
// Return low-level heap statistics from the C allocator (glibc).
PyObject *
psutil_malloc_info(PyObject *self, PyObject *args) {
    static int warned = 0;
    void *handle = NULL;
    void *fun = NULL;
    unsigned long long uord, mmap, arena;

    handle = dlopen("libc.so.6", RTLD_LAZY);
    if (handle != NULL) {
        fun = dlsym(handle, "mallinfo2");
    }

    if (fun != NULL) {
        struct my_mallinfo2 m2;

        m2 = ((struct my_mallinfo2(*)(void))fun)();

        uord = (unsigned long long)m2.uordblks;
        mmap = (unsigned long long)m2.hblkhd;
        arena = (unsigned long long)m2.arena;
    }
    else {
        struct mallinfo m1;

        if (!warned) {
            psutil_debug("WARNING: using deprecated mallinfo()");
            warned = 1;
        }

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wdeprecated-declarations"
        m1 = mallinfo();
#pragma GCC diagnostic pop

        uord = (unsigned long long)m1.uordblks;
        mmap = (unsigned long long)m1.hblkhd;
        arena = (unsigned long long)m1.arena;
    }

    if (handle)
        dlclose(handle);

    return Py_BuildValue("KKK", uord, mmap, arena);
}


// Release unused memory held by the allocator back to the OS.
PyObject *
psutil_malloc_trim(PyObject *self, PyObject *args) {
    // malloc_trim returns 1 if some memory was released, else 0.
    int ret = malloc_trim(0);
    return PyBool_FromLong(ret);
}
#endif  // PSUTIL_HAS_MALLOC_INFO
