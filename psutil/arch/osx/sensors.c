/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// Sensors related functions. Original code was refactored and moved
// from psutil/_psutil_osx.c in 2023. This is the GIT blame before the move:
// https://github.com/giampaolo/psutil/blame/efd7ed3/psutil/_psutil_osx.c
// Original battery code:
// https://github.com/giampaolo/psutil/commit/e0df5da


#include <Python.h>
#include <IOKit/ps/IOPowerSources.h>
#include <IOKit/ps/IOPSKeys.h>

#include "../../_psutil_common.h"


PyObject *
psutil_sensors_battery(PyObject *self, PyObject *args) {
    PyObject *py_tuple = NULL;
    CFTypeRef power_info = NULL;
    CFArrayRef power_sources_list = NULL;
    CFDictionaryRef power_sources_information = NULL;
    CFNumberRef capacity_ref = NULL;
    CFNumberRef time_to_empty_ref = NULL;
    CFStringRef ps_state_ref = NULL;
    uint32_t capacity;     /* units are percent */
    int time_to_empty;     /* units are minutes */
    int is_power_plugged;

    power_info = IOPSCopyPowerSourcesInfo();

    if (!power_info) {
        PyErr_SetString(PyExc_RuntimeError,
            "IOPSCopyPowerSourcesInfo() syscall failed");
        goto error;
    }

    power_sources_list = IOPSCopyPowerSourcesList(power_info);
    if (!power_sources_list) {
        PyErr_SetString(PyExc_RuntimeError,
            "IOPSCopyPowerSourcesList() syscall failed");
        goto error;
    }

    /* Should only get one source. But in practice, check for > 0 sources */
    if (!CFArrayGetCount(power_sources_list)) {
        PyErr_SetString(PyExc_NotImplementedError, "no battery");
        goto error;
    }

    power_sources_information = IOPSGetPowerSourceDescription(
        power_info, CFArrayGetValueAtIndex(power_sources_list, 0));

    capacity_ref = (CFNumberRef)  CFDictionaryGetValue(
        power_sources_information, CFSTR(kIOPSCurrentCapacityKey));
    if (!CFNumberGetValue(capacity_ref, kCFNumberSInt32Type, &capacity)) {
        PyErr_SetString(PyExc_RuntimeError,
            "No battery capacity infomration in power sources info");
        goto error;
    }

    ps_state_ref = (CFStringRef) CFDictionaryGetValue(
        power_sources_information, CFSTR(kIOPSPowerSourceStateKey));
    is_power_plugged = CFStringCompare(
        ps_state_ref, CFSTR(kIOPSACPowerValue), 0)
        == kCFCompareEqualTo;

    time_to_empty_ref = (CFNumberRef) CFDictionaryGetValue(
        power_sources_information, CFSTR(kIOPSTimeToEmptyKey));
    if (!CFNumberGetValue(time_to_empty_ref,
                          kCFNumberIntType, &time_to_empty)) {
        /* This value is recommended for non-Apple power sources, so it's not
         * an error if it doesn't exist. We'll return -1 for "unknown" */
        /* A value of -1 indicates "Still Calculating the Time" also for
         * apple power source */
        time_to_empty = -1;
    }

    py_tuple = Py_BuildValue("Iii",
        capacity, time_to_empty, is_power_plugged);
    if (!py_tuple) {
        goto error;
    }

    CFRelease(power_info);
    CFRelease(power_sources_list);
    /* Caller should NOT release power_sources_information */

    return py_tuple;

error:
    if (power_info)
        CFRelease(power_info);
    if (power_sources_list)
        CFRelease(power_sources_list);
    Py_XDECREF(py_tuple);
    return NULL;
}
