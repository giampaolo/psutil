/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>
#include <PowrProf.h>

#include "../../_psutil_common.h"


/*
 * Return the number of logical, active CPUs. Return 0 if undetermined.
 * See discussion at: https://bugs.python.org/issue33166#msg314631
 */
static unsigned int
psutil_get_num_cpus(int fail_on_err) {
    unsigned int ncpus = 0;

    // Minimum requirement: Windows 7
    if (GetActiveProcessorCount != NULL) {
        ncpus = GetActiveProcessorCount(ALL_PROCESSOR_GROUPS);
        if ((ncpus == 0) && (fail_on_err == 1)) {
            PyErr_SetFromWindowsErr(0);
        }
    }
    else {
        psutil_debug("GetActiveProcessorCount() not available; "
                     "using GetSystemInfo()");
        ncpus = (unsigned int)PSUTIL_SYSTEM_INFO.dwNumberOfProcessors;
        if ((ncpus <= 0) && (fail_on_err == 1)) {
            PyErr_SetString(
                PyExc_RuntimeError,
                "GetSystemInfo() failed to retrieve CPU count");
        }
    }
    return ncpus;
}


/*
 * Retrieves system CPU timing information as a (user, system, idle)
 * tuple. On a multiprocessor system, the values returned are the
 * sum of the designated times across all processors.
 */
PyObject *
psutil_cpu_times(PyObject *self, PyObject *args) {
    double idle, kernel, user, system;
    FILETIME idle_time, kernel_time, user_time;

    if (!GetSystemTimes(&idle_time, &kernel_time, &user_time)) {
        PyErr_SetFromWindowsErr(0);
        return NULL;
    }

    idle = (double)((HI_T * idle_time.dwHighDateTime) + \
                   (LO_T * idle_time.dwLowDateTime));
    user = (double)((HI_T * user_time.dwHighDateTime) + \
                   (LO_T * user_time.dwLowDateTime));
    kernel = (double)((HI_T * kernel_time.dwHighDateTime) + \
                     (LO_T * kernel_time.dwLowDateTime));

    // Kernel time includes idle time.
    // We return only busy kernel time subtracting idle time from
    // kernel time.
    system = (kernel - idle);
    return Py_BuildValue("(ddd)", user, system, idle);
}


/*
 * Same as above but for all system CPUs.
 */
PyObject *
psutil_per_cpu_times(PyObject *self, PyObject *args) {
    double idle, kernel, systemt, user, interrupt, dpc;
    NTSTATUS status;
    _SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION *sppi = NULL;
    UINT i;
    unsigned int ncpus;
    PyObject *py_tuple = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;

    // retrieves number of processors
    ncpus = psutil_get_num_cpus(1);
    if (ncpus == 0)
        goto error;

    // allocates an array of _SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION
    // structures, one per processor
    sppi = (_SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION *) \
        malloc(ncpus * sizeof(_SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION));
    if (sppi == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    // gets cpu time information
    status = NtQuerySystemInformation(
        SystemProcessorPerformanceInformation,
        sppi,
        ncpus * sizeof(_SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION),
        NULL);
    if (! NT_SUCCESS(status)) {
        psutil_SetFromNTStatusErr(
            status,
            "NtQuerySystemInformation(SystemProcessorPerformanceInformation)"
        );
        goto error;
    }

    // computes system global times summing each
    // processor value
    idle = user = kernel = interrupt = dpc = 0;
    for (i = 0; i < ncpus; i++) {
        py_tuple = NULL;
        user = (double)((HI_T * sppi[i].UserTime.HighPart) +
                       (LO_T * sppi[i].UserTime.LowPart));
        idle = (double)((HI_T * sppi[i].IdleTime.HighPart) +
                       (LO_T * sppi[i].IdleTime.LowPart));
        kernel = (double)((HI_T * sppi[i].KernelTime.HighPart) +
                         (LO_T * sppi[i].KernelTime.LowPart));
        interrupt = (double)((HI_T * sppi[i].InterruptTime.HighPart) +
                            (LO_T * sppi[i].InterruptTime.LowPart));
        dpc = (double)((HI_T * sppi[i].DpcTime.HighPart) +
                      (LO_T * sppi[i].DpcTime.LowPart));

        // kernel time includes idle time on windows
        // we return only busy kernel time subtracting
        // idle time from kernel time
        systemt = kernel - idle;
        py_tuple = Py_BuildValue(
            "(ddddd)",
            user,
            systemt,
            idle,
            interrupt,
            dpc
        );
        if (!py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_CLEAR(py_tuple);
    }

    free(sppi);
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    if (sppi)
        free(sppi);
    return NULL;
}


/*
 * Return the number of active, logical CPUs.
 */
PyObject *
psutil_cpu_count_logical(PyObject *self, PyObject *args) {
    unsigned int ncpus;

    ncpus = psutil_get_num_cpus(0);
    if (ncpus != 0)
        return Py_BuildValue("I", ncpus);
    else
        Py_RETURN_NONE;  // mimic os.cpu_count()
}


/*
 * Return the number of CPU cores (non hyper-threading).
 */
PyObject *
psutil_cpu_count_cores(PyObject *self, PyObject *args) {
    DWORD rc;
    PSYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX buffer = NULL;
    PSYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX ptr = NULL;
    DWORD length = 0;
    DWORD offset = 0;
    DWORD ncpus = 0;
    DWORD prev_processor_info_size = 0;

    // GetLogicalProcessorInformationEx() is available from Windows 7
    // onward. Differently from GetLogicalProcessorInformation()
    // it supports process groups, meaning this is able to report more
    // than 64 CPUs. See:
    // https://bugs.python.org/issue33166
    if (GetLogicalProcessorInformationEx == NULL) {
        psutil_debug("Win < 7; cpu_count_cores() forced to None");
        Py_RETURN_NONE;
    }

    while (1) {
        rc = GetLogicalProcessorInformationEx(
            RelationAll, buffer, &length);
        if (rc == FALSE) {
            if (GetLastError() == ERROR_INSUFFICIENT_BUFFER) {
                if (buffer) {
                    free(buffer);
                }
                buffer = \
                    (PSYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX)malloc(length);
                if (NULL == buffer) {
                    PyErr_NoMemory();
                    return NULL;
                }
            }
            else {
                psutil_debug("GetLogicalProcessorInformationEx() returned %u",
                             GetLastError());
                goto return_none;
            }
        }
        else {
            break;
        }
    }

    ptr = buffer;
    while (offset < length) {
        // Advance ptr by the size of the previous
        // SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX struct.
        ptr = (SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX*) \
            (((char*)ptr) + prev_processor_info_size);

        if (ptr->Relationship == RelationProcessorCore) {
            ncpus += 1;
        }

        // When offset == length, we've reached the last processor
        // info struct in the buffer.
        offset += ptr->Size;
        prev_processor_info_size = ptr->Size;
    }

    free(buffer);
    if (ncpus != 0) {
        return Py_BuildValue("I", ncpus);
    }
    else {
        psutil_debug("GetLogicalProcessorInformationEx() count was 0");
        Py_RETURN_NONE;  // mimic os.cpu_count()
    }

return_none:
    if (buffer != NULL)
        free(buffer);
    Py_RETURN_NONE;
}


/*
 * Return CPU statistics.
 */
PyObject *
psutil_cpu_stats(PyObject *self, PyObject *args) {
    NTSTATUS status;
    _SYSTEM_PERFORMANCE_INFORMATION *spi = NULL;
    _SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION *sppi = NULL;
    _SYSTEM_INTERRUPT_INFORMATION *InterruptInformation = NULL;
    unsigned int ncpus;
    UINT i;
    ULONG64 dpcs = 0;
    ULONG interrupts = 0;

    // retrieves number of processors
    ncpus = psutil_get_num_cpus(1);
    if (ncpus == 0)
        goto error;

    // get syscalls / ctx switches
    spi = (_SYSTEM_PERFORMANCE_INFORMATION *) \
           malloc(ncpus * sizeof(_SYSTEM_PERFORMANCE_INFORMATION));
    if (spi == NULL) {
        PyErr_NoMemory();
        goto error;
    }
    status = NtQuerySystemInformation(
        SystemPerformanceInformation,
        spi,
        ncpus * sizeof(_SYSTEM_PERFORMANCE_INFORMATION),
        NULL);
    if (! NT_SUCCESS(status)) {
        psutil_SetFromNTStatusErr(
            status, "NtQuerySystemInformation(SystemPerformanceInformation)");
        goto error;
    }

    // get DPCs
    InterruptInformation = \
        malloc(sizeof(_SYSTEM_INTERRUPT_INFORMATION) * ncpus);
    if (InterruptInformation == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    status = NtQuerySystemInformation(
        SystemInterruptInformation,
        InterruptInformation,
        ncpus * sizeof(SYSTEM_INTERRUPT_INFORMATION),
        NULL);
    if (! NT_SUCCESS(status)) {
        psutil_SetFromNTStatusErr(
            status, "NtQuerySystemInformation(SystemInterruptInformation)");
        goto error;
    }
    for (i = 0; i < ncpus; i++) {
        dpcs += InterruptInformation[i].DpcCount;
    }

    // get interrupts
    sppi = (_SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION *) \
        malloc(ncpus * sizeof(_SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION));
    if (sppi == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    status = NtQuerySystemInformation(
        SystemProcessorPerformanceInformation,
        sppi,
        ncpus * sizeof(_SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION),
        NULL);
    if (! NT_SUCCESS(status)) {
        psutil_SetFromNTStatusErr(
            status,
            "NtQuerySystemInformation(SystemProcessorPerformanceInformation)");
        goto error;
    }

    for (i = 0; i < ncpus; i++) {
        interrupts += sppi[i].InterruptCount;
    }

    // done
    free(spi);
    free(InterruptInformation);
    free(sppi);
    return Py_BuildValue(
        "kkkk",
        spi->ContextSwitches,
        interrupts,
        (unsigned long)dpcs,
        spi->SystemCalls
    );

error:
    if (spi)
        free(spi);
    if (InterruptInformation)
        free(InterruptInformation);
    if (sppi)
        free(sppi);
    return NULL;
}


/*
 * Return CPU frequency.
 */
PyObject *
psutil_cpu_freq(PyObject *self, PyObject *args) {
    PROCESSOR_POWER_INFORMATION *ppi;
    NTSTATUS ret;
    ULONG size;
    LPBYTE pBuffer = NULL;
    ULONG current;
    ULONG max;
    unsigned int ncpus;

    // Get the number of CPUs.
    ncpus = psutil_get_num_cpus(1);
    if (ncpus == 0)
        return NULL;

    // Allocate size.
    size = ncpus * sizeof(PROCESSOR_POWER_INFORMATION);
    pBuffer = (BYTE*)LocalAlloc(LPTR, size);
    if (! pBuffer) {
        PyErr_SetFromWindowsErr(0);
        return NULL;
    }

    // Syscall.
    ret = CallNtPowerInformation(
        ProcessorInformation, NULL, 0, pBuffer, size);
    if (ret != 0) {
        PyErr_SetString(PyExc_RuntimeError,
                        "CallNtPowerInformation syscall failed");
        goto error;
    }

    // Results.
    ppi = (PROCESSOR_POWER_INFORMATION *)pBuffer;
    max = ppi->MaxMhz;
    current = ppi->CurrentMhz;
    LocalFree(pBuffer);

    return Py_BuildValue("kk", current, max);

error:
    if (pBuffer != NULL)
        LocalFree(pBuffer);
    return NULL;
}
