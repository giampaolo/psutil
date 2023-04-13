/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>
#include <Psapi.h>
#include <pdh.h>

#include "../../_psutil_common.h"


PyObject *
psutil_getpagesize(PyObject *self, PyObject *args) {
    // XXX: we may want to use GetNativeSystemInfo to differentiate
    // page size for WoW64 processes (but am not sure).
    return Py_BuildValue("I", PSUTIL_SYSTEM_INFO.dwPageSize);
}


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


// Return a float representing the percent usage of all paging files on
// the system.
PyObject *
psutil_swap_percent(PyObject *self, PyObject *args) {
    WCHAR *szCounterPath = L"\\Paging File(_Total)\\% Usage";
    PDH_STATUS s;
    HQUERY hQuery;
    HCOUNTER hCounter;
    PDH_FMT_COUNTERVALUE counterValue;
    double percentUsage;

    if ((PdhOpenQueryW(NULL, 0, &hQuery)) != ERROR_SUCCESS) {
        PyErr_Format(PyExc_RuntimeError, "PdhOpenQueryW failed");
        return NULL;
    }

    s = PdhAddEnglishCounterW(hQuery, szCounterPath, 0, &hCounter);
    if (s != ERROR_SUCCESS) {
        PdhCloseQuery(hQuery);
        PyErr_Format(
            PyExc_RuntimeError,
            "PdhAddEnglishCounterW failed. Performance counters may be disabled."
        );
        return NULL;
    }

    s = PdhCollectQueryData(hQuery);
    if (s != ERROR_SUCCESS) {
        // If swap disabled this will fail.
        psutil_debug("PdhCollectQueryData failed; assume swap percent is 0");
        percentUsage = 0;
    }
    else {
        s = PdhGetFormattedCounterValue(
            (PDH_HCOUNTER)hCounter, PDH_FMT_DOUBLE, 0, &counterValue);
        if (s != ERROR_SUCCESS) {
            PdhCloseQuery(hQuery);
            PyErr_Format(
                PyExc_RuntimeError, "PdhGetFormattedCounterValue failed");
            return NULL;
        }
        percentUsage = counterValue.doubleValue;
    }

    PdhRemoveCounter(hCounter);
    PdhCloseQuery(hQuery);
    return Py_BuildValue("d", percentUsage);
}
