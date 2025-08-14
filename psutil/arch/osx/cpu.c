/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

/*
System-wide CPU related functions.

Original code was refactored and moved from psutil/_psutil_osx.c in 2020
right before a4c0a0eb0d2a872ab7a45e47fcf37ef1fde5b012.
For reference, here's the git history with original implementations:

- CPU count logical: 3d291d425b856077e65163e43244050fb188def1
- CPU count physical: 4263e354bb4984334bc44adf5dd2f32013d69fba
- CPU times: 32488bdf54aed0f8cef90d639c1667ffaa3c31c7
- CPU stat: fa00dfb961ef63426c7818899340866ced8d2418
- CPU frequency: 6ba1ac4ebfcd8c95fca324b15606ab0ec1412d39
*/

#include <Python.h>
#include <mach/mach_error.h>
#include <mach/mach_host.h>
#include <mach/mach_port.h>
#include <mach/mach_vm.h>
#include <sys/sysctl.h>
#include <sys/vmmeter.h>
#include <mach/mach.h>
#if defined(__arm64__) || defined(__aarch64__)
    #include <CoreFoundation/CoreFoundation.h>
    #include <IOKit/IOKitLib.h>
#endif

#include "../../arch/all/init.h"

// added in macOS 12
#ifndef kIOMainPortDefault
    #define kIOMainPortDefault 0
#endif

PyObject *
psutil_cpu_count_logical(PyObject *self, PyObject *args) {
    int num;

    if (psutil_sysctlbyname("hw.logicalcpu", &num, sizeof(num)) != 0)
        Py_RETURN_NONE;  // mimic os.cpu_count()
    else
        return Py_BuildValue("i", num);
}


PyObject *
psutil_cpu_count_cores(PyObject *self, PyObject *args) {
    int num;

    if (psutil_sysctlbyname("hw.physicalcpu", &num, sizeof(num)) != 0)
        Py_RETURN_NONE;  // mimic os.cpu_count()
    else
        return Py_BuildValue("i", num);
}


PyObject *
psutil_cpu_times(PyObject *self, PyObject *args) {
    mach_msg_type_number_t count = HOST_CPU_LOAD_INFO_COUNT;
    kern_return_t error;
    host_cpu_load_info_data_t r_load;
    mach_port_t mport;

    mport = mach_host_self();
    if (mport == MACH_PORT_NULL) {
        PyErr_SetString(PyExc_RuntimeError,
                        "mach_host_self() returned MACH_PORT_NULL");
        return NULL;
    }

    error = host_statistics(mport, HOST_CPU_LOAD_INFO,
                            (host_info_t)&r_load, &count);
    if (error != KERN_SUCCESS) {
        mach_port_deallocate(mach_task_self(), mport);
        return PyErr_Format(
            PyExc_RuntimeError,
            "host_statistics(HOST_CPU_LOAD_INFO) syscall failed: %s",
            mach_error_string(error));
    }
    mach_port_deallocate(mach_task_self(), mport);

    return Py_BuildValue(
        "(dddd)",
        (double)r_load.cpu_ticks[CPU_STATE_USER] / CLK_TCK,
        (double)r_load.cpu_ticks[CPU_STATE_NICE] / CLK_TCK,
        (double)r_load.cpu_ticks[CPU_STATE_SYSTEM] / CLK_TCK,
        (double)r_load.cpu_ticks[CPU_STATE_IDLE] / CLK_TCK
    );
}


PyObject *
psutil_cpu_stats(PyObject *self, PyObject *args) {
    kern_return_t ret;
    mach_msg_type_number_t count;
    mach_port_t mport;
    struct vmmeter vmstat;

    mport = mach_host_self();
    if (mport == MACH_PORT_NULL) {
        PyErr_SetString(PyExc_RuntimeError,
                        "mach_host_self() returned MACH_PORT_NULL");
        return NULL;
    }

    count = HOST_VM_INFO_COUNT;
    ret = host_statistics(mport, HOST_VM_INFO, (host_info_t)&vmstat, &count);
    if (ret != KERN_SUCCESS) {
        mach_port_deallocate(mach_task_self(), mport);
        PyErr_Format(
            PyExc_RuntimeError,
            "host_statistics(HOST_VM_INFO) failed: %s",
            mach_error_string(ret));
        return NULL;
    }

    mach_port_deallocate(mach_task_self(), mport);
    return Py_BuildValue(
        "IIIII",
        vmstat.v_swtch,  // context switches
        vmstat.v_intr,   // interrupts
        vmstat.v_soft,   // software interrupts
#if defined(__MAC_OS_X_VERSION_MIN_REQUIRED) \
    && __MAC_OS_X_VERSION_MIN_REQUIRED__ >= 120000
        0,
#else
        vmstat.v_syscall,  // system calls (if available)
#endif
        vmstat.v_trap     // traps
    );
}


#if defined(__arm64__) || defined(__aarch64__)

// Helper to locate the 'pmgr' entry in AppleARMIODevice. Returns 0 on
// failure, nonzero on success, and stores the found entry in
// *out_entry. Caller is responsible for IOObjectRelease(*out_entry).
// Needed because on GitHub CI sometimes (but not all the times)
// "AppleARMIODevice" is not available.
static int
psutil_find_pmgr_entry(io_registry_entry_t *out_entry) {

    kern_return_t status;
    io_iterator_t iter = 0;
    io_registry_entry_t entry = 0;
    CFDictionaryRef matching;
    io_name_t name;
    int found = 0;

    *out_entry = 0;

    matching = IOServiceMatching("AppleARMIODevice");
    if (matching == NULL)
        return 0;

    status = IOServiceGetMatchingServices(kIOMainPortDefault, matching, &iter);
    if (status != KERN_SUCCESS)
        return 0;

    while ((entry = IOIteratorNext(iter)) != 0) {
        status = IORegistryEntryGetName(entry, name);
        if (status == KERN_SUCCESS && strcmp(name, "pmgr") == 0) {
            found = 1;
            break;
        }
        IOObjectRelease(entry);
    }

    IOObjectRelease(iter);

    if (found) {
        *out_entry = entry;  // caller must release
        return 1;
    }

    return 0;
}

// Python wrapper: return True/False.
PyObject *
psutil_has_cpu_freq(PyObject *self, PyObject *args) {
    io_registry_entry_t entry = 0;
    int ok = psutil_find_pmgr_entry(&entry);
    if (entry != 0)
        IOObjectRelease(entry);
    if (ok)
        Py_RETURN_TRUE;
    Py_RETURN_FALSE;
}


PyObject *
psutil_cpu_freq(PyObject *self, PyObject *args) {
    io_registry_entry_t entry = 0;
    CFTypeRef pCoreRef = NULL;
    CFTypeRef eCoreRef = NULL;
    size_t pCoreLength;
    uint32_t pMin = 0, eMin = 0, min = 0, max = 0, curr = 0;

    if (!psutil_find_pmgr_entry(&entry)) {
        return PyErr_Format(
            PyExc_RuntimeError,
            "'pmgr' entry was not found in AppleARMIODevice service"
        );
    }

    pCoreRef = IORegistryEntryCreateCFProperty(
        entry, CFSTR("voltage-states5-sram"), kCFAllocatorDefault, 0
    );
    if (pCoreRef == NULL ||
            CFGetTypeID(pCoreRef) != CFDataGetTypeID() ||
            CFDataGetLength(pCoreRef) < 8) {
        PyErr_SetString(
            PyExc_RuntimeError,
            "'voltage-states5-sram' is missing or invalid"
        );
        goto error;
    }

    eCoreRef = IORegistryEntryCreateCFProperty(
        entry, CFSTR("voltage-states1-sram"), kCFAllocatorDefault, 0
    );
    if (eCoreRef == NULL ||
            CFGetTypeID(eCoreRef) != CFDataGetTypeID() ||
            CFDataGetLength(eCoreRef) < 4) {
        PyErr_SetString(
            PyExc_RuntimeError,
            "'voltage-states1-sram' is missing or invalid"
        );
        goto error;
    }

    pCoreLength = CFDataGetLength(pCoreRef);
    CFDataGetBytes(pCoreRef, CFRangeMake(0, 4), (UInt8 *)&pMin);
    CFDataGetBytes(eCoreRef, CFRangeMake(0, 4), (UInt8 *)&eMin);
    CFDataGetBytes(pCoreRef, CFRangeMake(pCoreLength - 8, 4), (UInt8 *)&max);

    min = (pMin < eMin) ? pMin : eMin;
    curr = max;

    if (pCoreRef)
        CFRelease(pCoreRef);
    if (eCoreRef)
        CFRelease(eCoreRef);
    if (entry)
        IOObjectRelease(entry);

    return Py_BuildValue(
        "KKK",
        (unsigned long long)(curr / 1000 / 1000),
        (unsigned long long)(min / 1000 / 1000),
        (unsigned long long)(max / 1000 / 1000)
    );

error:
    if (pCoreRef)
        CFRelease(pCoreRef);
    if (eCoreRef)
        CFRelease(eCoreRef);
    if (entry)
        IOObjectRelease(entry);
    return NULL;
}
#else  // not ARM64 / ARCH64
PyObject *
psutil_has_cpu_freq(PyObject *self, PyObject *args) {
    Py_RETURN_TRUE;
}

PyObject *
psutil_cpu_freq(PyObject *self, PyObject *args) {
    unsigned int curr;
    int64_t min;
    int64_t max;
    int mib[2];

    // also available as "hw.cpufrequency" but it's deprecated
    mib[0] = CTL_HW;
    mib[1] = HW_CPU_FREQ;

    if (psutil_sysctl(mib, 2, &curr, sizeof(curr)) < 0)
        return psutil_PyErr_SetFromOSErrnoWithSyscall("sysctl(HW_CPU_FREQ)");

    if (psutil_sysctlbyname("hw.cpufrequency_min", &min, sizeof(min)) != 0) {
        min = 0;
        psutil_debug("sysctlbyname('hw.cpufrequency_min') failed (set to 0)");
    }

    if (psutil_sysctlbyname("hw.cpufrequency_max", &max, sizeof(max)) != 0) {
        max = 0;
        psutil_debug("sysctlbyname('hw.cpufrequency_max') failed (set to 0)");
    }

    return Py_BuildValue(
        "KKK",
        (unsigned long long)(curr / 1000 / 1000),
        (unsigned long long)(min / 1000 / 1000),
        (unsigned long long)(max / 1000 / 1000));
}
#endif

PyObject *
psutil_per_cpu_times(PyObject *self, PyObject *args) {
    natural_t cpu_count;
    natural_t i;
    processor_info_array_t info_array = NULL;
    mach_msg_type_number_t info_count;
    kern_return_t error;
    processor_cpu_load_info_data_t *cpu_load_info = NULL;
    int ret;
    mach_port_t mport;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_cputime = NULL;

    if (py_retlist == NULL)
        return NULL;

    mport = mach_host_self();
    if (mport == MACH_PORT_NULL) {
        PyErr_SetString(PyExc_RuntimeError,
                        "mach_host_self() returned MACH_PORT_NULL");
        goto error;
    }

    error = host_processor_info(mport, PROCESSOR_CPU_LOAD_INFO,
                                &cpu_count, &info_array, &info_count);
    if (error != KERN_SUCCESS) {
        mach_port_deallocate(mach_task_self(), mport);
        PyErr_Format(
            PyExc_RuntimeError,
            "host_processor_info(PROCESSOR_CPU_LOAD_INFO) syscall failed: %s",
             mach_error_string(error));
        goto error;
    }
    mach_port_deallocate(mach_task_self(), mport);

    cpu_load_info = (processor_cpu_load_info_data_t *) info_array;

    for (i = 0; i < cpu_count; i++) {
        py_cputime = Py_BuildValue(
            "(dddd)",
            (double)cpu_load_info[i].cpu_ticks[CPU_STATE_USER] / CLK_TCK,
            (double)cpu_load_info[i].cpu_ticks[CPU_STATE_NICE] / CLK_TCK,
            (double)cpu_load_info[i].cpu_ticks[CPU_STATE_SYSTEM] / CLK_TCK,
            (double)cpu_load_info[i].cpu_ticks[CPU_STATE_IDLE] / CLK_TCK
        );
        if (!py_cputime)
            goto error;
        if (PyList_Append(py_retlist, py_cputime)) {
            Py_DECREF(py_cputime);
            goto error;
        }
        Py_CLEAR(py_cputime);
    }

    ret = vm_deallocate(mach_task_self(), (vm_address_t)info_array,
                        info_count * sizeof(integer_t));
    if (ret != KERN_SUCCESS)
        PyErr_WarnEx(PyExc_RuntimeWarning, "vm_deallocate() failed", 2);
    return py_retlist;

error:
    Py_XDECREF(py_cputime);
    Py_DECREF(py_retlist);
    if (info_array != NULL) {
        ret = vm_deallocate(mach_task_self(), (vm_address_t)info_array,
                            info_count * sizeof(integer_t));
        if (ret != KERN_SUCCESS)
            PyErr_WarnEx(PyExc_RuntimeWarning, "vm_deallocate() failed", 2);
    }
    return NULL;
}
