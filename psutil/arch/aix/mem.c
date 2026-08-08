/*
 * Copyright (c) 2009, Giampaolo Rodola'
 * Copyright (c) 2017, Arnon Yaari
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <libperfstat.h>

#include "../../arch/all/init.h"
#include "init.h"


PyObject *
psutil_virtual_mem(PyObject *self, PyObject *args) {
    int rc;
    long pagesize = psutil_getpagesize();
    perfstat_memory_total_t memory;

    rc = perfstat_memory_total(
        NULL, &memory, sizeof(perfstat_memory_total_t), 1
    );
    if (rc <= 0) {
        psutil_oserror();
        return NULL;
    }

    return Py_BuildValue(
        "KKKKK",
        (unsigned long long)memory.real_total * pagesize,
        (unsigned long long)memory.real_avail * pagesize,
        (unsigned long long)memory.real_free * pagesize,
        (unsigned long long)memory.real_pinned * pagesize,
        (unsigned long long)memory.real_inuse * pagesize
    );
}


PyObject *
psutil_swap_mem(PyObject *self, PyObject *args) {
    int rc;
    long pagesize = psutil_getpagesize();
    perfstat_memory_total_t memory;

    rc = perfstat_memory_total(
        NULL, &memory, sizeof(perfstat_memory_total_t), 1
    );
    if (rc <= 0) {
        psutil_oserror();
        return NULL;
    }

    return Py_BuildValue(
        "KKKK",
        (unsigned long long)memory.pgsp_total * pagesize,
        (unsigned long long)memory.pgsp_free * pagesize,
        (unsigned long long)memory.pgins * pagesize,
        (unsigned long long)memory.pgouts * pagesize
    );
}
