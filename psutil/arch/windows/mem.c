/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>
#include <Psapi.h>
#include <pdh.h>

#include "../../arch/all/init.h"


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

    if (!GetPerformanceInfo(&perfInfo, sizeof(PERFORMANCE_INFORMATION))) {
        psutil_oserror();
        return NULL;
    }
    // values are size_t, widen (if needed) to long long
    pageSize = perfInfo.PageSize;
    totalPhys = perfInfo.PhysicalTotal * pageSize;
    availPhys = perfInfo.PhysicalAvailable * pageSize;
    totalSys = perfInfo.CommitLimit * pageSize;
    availSys = totalSys - perfInfo.CommitTotal * pageSize;
    return Py_BuildValue("(LLLL)", totalPhys, availPhys, totalSys, availSys);
}


PyObject *
psutil_GetPerformanceInfo(PyObject *self, PyObject *args) {
    PERFORMANCE_INFORMATION info;
    PyObject *dict = PyDict_New();

    if (!dict)
        return NULL;
    if (!GetPerformanceInfo(&info, sizeof(PERFORMANCE_INFORMATION))) {
        psutil_oserror();
        goto error;
    }

    // clang-format off
    if (!pydict_add(dict, "CommitTotal", "K", (ULONGLONG)info.CommitTotal)) goto error;
    if (!pydict_add(dict, "CommitLimit", "K", (ULONGLONG)info.CommitLimit)) goto error;
    if (!pydict_add(dict, "CommitPeak", "K", (ULONGLONG)info.CommitPeak)) goto error;
    if (!pydict_add(dict, "PhysicalTotal", "K", (ULONGLONG)info.PhysicalTotal)) goto error;
    if (!pydict_add(dict, "PhysicalAvailable", "K", (ULONGLONG)info.PhysicalAvailable)) goto error;
    if (!pydict_add(dict, "SystemCache", "K", (ULONGLONG)info.SystemCache)) goto error;
    if (!pydict_add(dict, "KernelTotal", "K", (ULONGLONG)info.KernelTotal)) goto error;
    if (!pydict_add(dict, "KernelPaged", "K", (ULONGLONG)info.KernelPaged)) goto error;
    if (!pydict_add(dict, "KernelNonpaged", "K", (ULONGLONG)info.KernelNonpaged)) goto error;
    if (!pydict_add(dict, "PageSize", "K", (ULONGLONG)info.PageSize)) goto error;
    if (!pydict_add(dict, "HandleCount", "I", (unsigned int)info.HandleCount)) goto error;
    if (!pydict_add(dict, "ProcessCount", "I", (unsigned int)info.ProcessCount)) goto error;
    if (!pydict_add(dict, "ThreadCount", "I", (unsigned int)info.ThreadCount)) goto error;
    // clang-format on
    return dict;

error:
    Py_DECREF(dict);
    return NULL;
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
        psutil_runtime_error("PdhOpenQueryW failed");
        return NULL;
    }

    s = PdhAddEnglishCounterW(hQuery, szCounterPath, 0, &hCounter);
    if (s != ERROR_SUCCESS) {
        PdhCloseQuery(hQuery);
        psutil_runtime_error(
            "PdhAddEnglishCounterW failed. Performance counters may be "
            "disabled."
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
            (PDH_HCOUNTER)hCounter, PDH_FMT_DOUBLE, 0, &counterValue
        );
        if (s != ERROR_SUCCESS) {
            PdhCloseQuery(hQuery);
            psutil_runtime_error("PdhGetFormattedCounterValue failed");
            return NULL;
        }
        percentUsage = counterValue.doubleValue;
    }

    PdhRemoveCounter(hCounter);
    PdhCloseQuery(hQuery);
    return Py_BuildValue("d", percentUsage);
}
