/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Functions related to the Windows Management Instrumentation API.
 */

#include <Python.h>
#include <windows.h>
#include <pdh.h>

#include "../../_psutil_common.h"


// We use an exponentially weighted moving average, just like Unix systems do
// https://en.wikipedia.org/wiki/Load_(computing)#Unix-style_load_calculation
//
// These constants serve as the damping factor and are calculated with
// 1 / exp(sampling interval in seconds / window size in seconds)
//
// This formula comes from linux's include/linux/sched/loadavg.h
// https://github.com/torvalds/linux/blob/345671ea0f9258f410eb057b9ced9cefbbe5dc78/include/linux/sched/loadavg.h#L20-L23
#define LOADAVG_FACTOR_1F  0.9200444146293232478931553241
#define LOADAVG_FACTOR_5F  0.9834714538216174894737477501
#define LOADAVG_FACTOR_15F 0.9944598480048967508795473394
// The time interval in seconds between taking load counts, same as Linux
#define SAMPLING_INTERVAL 5

double load_avg_1m = 0;
double load_avg_5m = 0;
double load_avg_15m = 0;


VOID CALLBACK LoadAvgCallback(PVOID hCounter, BOOLEAN timedOut) {
    PDH_FMT_COUNTERVALUE displayValue;
    double currentLoad;
    PDH_STATUS err;

    err = PdhGetFormattedCounterValue(
        (PDH_HCOUNTER)hCounter, PDH_FMT_DOUBLE, 0, &displayValue);
    // Skip updating the load if we can't get the value successfully
    if (err != ERROR_SUCCESS) {
        return;
    }
    currentLoad = displayValue.doubleValue;

    load_avg_1m = load_avg_1m * LOADAVG_FACTOR_1F + currentLoad * \
        (1.0 - LOADAVG_FACTOR_1F);
    load_avg_5m = load_avg_5m * LOADAVG_FACTOR_5F + currentLoad * \
        (1.0 - LOADAVG_FACTOR_5F);
    load_avg_15m = load_avg_15m * LOADAVG_FACTOR_15F + currentLoad * \
        (1.0 - LOADAVG_FACTOR_15F);
}


PyObject *
psutil_init_loadavg_counter(PyObject *self, PyObject *args) {
    WCHAR *szCounterPath = L"\\System\\Processor Queue Length";
    PDH_STATUS s;
    BOOL ret;
    HQUERY hQuery;
    HCOUNTER hCounter;
    HANDLE event;
    HANDLE waitHandle;

    if ((PdhOpenQueryW(NULL, 0, &hQuery)) != ERROR_SUCCESS) {
        PyErr_Format(PyExc_RuntimeError, "PdhOpenQueryW failed");
        return NULL;
    }

    s = PdhAddEnglishCounterW(hQuery, szCounterPath, 0, &hCounter);
    if (s != ERROR_SUCCESS) {
        PyErr_Format(
            PyExc_RuntimeError,
            "PdhAddEnglishCounterW failed. Performance counters may be disabled."
        );
        return NULL;
    }

    event = CreateEventW(NULL, FALSE, FALSE, L"LoadUpdateEvent");
    if (event == NULL) {
        PyErr_SetFromOSErrnoWithSyscall("CreateEventW");
        return NULL;
    }

    s = PdhCollectQueryDataEx(hQuery, SAMPLING_INTERVAL, event);
    if (s != ERROR_SUCCESS) {
        PyErr_Format(PyExc_RuntimeError, "PdhCollectQueryDataEx failed");
        return NULL;
    }

    ret = RegisterWaitForSingleObject(
        &waitHandle,
        event,
        (WAITORTIMERCALLBACK)LoadAvgCallback,
        (PVOID)
        hCounter,
        INFINITE,
        WT_EXECUTEDEFAULT);

    if (ret == 0) {
        PyErr_SetFromOSErrnoWithSyscall("RegisterWaitForSingleObject");
        return NULL;
    }

    Py_RETURN_NONE;
}


/*
 * Gets the emulated 1 minute, 5 minute and 15 minute load averages
 * (processor queue length) for the system.
 * `init_loadavg_counter` must be called before this function to engage the
 * mechanism that records load values.
 */
PyObject *
psutil_get_loadavg(PyObject *self, PyObject *args) {
    return Py_BuildValue("(ddd)", load_avg_1m, load_avg_5m, load_avg_15m);
}
