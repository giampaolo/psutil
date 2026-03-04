/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// Struct-sequence types for macOS. Created once at module import time
// via psutil_osx_init_ntuples() and reused for every call.

#include <Python.h>

#include "../../arch/all/init.h"


PyTypeObject *psutil_svmem_type = NULL;
PyTypeObject *psutil_sswap_type = NULL;


int
psutil_osx_init_ntuples(void) {
    psutil_svmem_type = psutil_structseq_type_new(
        "svmem",
        "total",
        "available",
        "percent",
        "used",
        "free",
        "active",
        "inactive",
        "wired",
        NULL
    );
    if (!psutil_svmem_type)
        return -1;

    psutil_sswap_type = psutil_structseq_type_new(
        "sswap", "total", "used", "free", "percent", "sin", "sout", NULL
    );
    if (!psutil_sswap_type)
        return -1;

    return 0;
}
