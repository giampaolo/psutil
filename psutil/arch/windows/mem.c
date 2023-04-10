/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>
#include <Psapi.h>

#include "../../_psutil_common.h"


PyObject *
psutil_virtual_mem(PyObject *self, PyObject *args) {
    unsigned long long totalPhys, availPhys, totalSys, availSys, pageSize;
    PERFORMANCE_INFORMATION perfInfo;

    if (! GetPerformanceInfo(&perfInfo, sizeof(PERFORMANCE_INFORMATION))) {
        PyErr_SetFromWindowsErr(0);
        return NULL;
    }
    // values are size_t, widen (if needed) to long long
    pageSize = perfInfo.PageSize;
    totalPhys = perfInfo.PhysicalTotal * pageSize;
    availPhys = perfInfo.PhysicalAvailable * pageSize;
    totalSys = perfInfo.CommitLimit * pageSize;
    availSys = totalSys - perfInfo.CommitTotal * pageSize;
    return Py_BuildValue(
        "(LLLL)",
        totalPhys,
        availPhys,
        totalSys,
        availSys);
}
