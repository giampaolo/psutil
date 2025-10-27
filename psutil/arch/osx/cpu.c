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
        Py_RETURN_NONE;
    return Py_BuildValue("i", num);
}


PyObject *
psutil_cpu_count_cores(PyObject *self, PyObject *args) {
    int num;

    if (psutil_sysctlbyname("hw.physicalcpu", &num, sizeof(num)) != 0)
        Py_RETURN_NONE;
    return Py_BuildValue("i", num);
}


PyObject *
psutil_cpu_times(PyObject *self, PyObject *args) {
    mach_msg_type_number_t count = HOST_CPU_LOAD_INFO_COUNT;
    kern_return_t error;
    host_cpu_load_info_data_t r_load;
    mach_port_t mport = mach_host_self();

    if (mport == MACH_PORT_NULL) {
        psutil_runtime_error("mach_host_self() returned MACH_PORT_NULL");
        return NULL;
    }

    error = host_statistics(
        mport, HOST_CPU_LOAD_INFO, (host_info_t)&r_load, &count
    );
    mach_port_deallocate(mach_task_self(), mport);

    if (error != KERN_SUCCESS) {
        return psutil_runtime_error(
            "host_statistics(HOST_CPU_LOAD_INFO) syscall failed: %s",
            mach_error_string(error)
        );
    }

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
    mach_msg_type_number_t count = HOST_VM_INFO_COUNT;
    mach_port_t mport = mach_host_self();
    struct vmmeter vmstat;

    if (mport == MACH_PORT_NULL) {
        psutil_runtime_error("mach_host_self() returned MACH_PORT_NULL");
        return NULL;
    }

    ret = host_statistics(mport, HOST_VM_INFO, (host_info_t)&vmstat, &count);
    mach_port_deallocate(mach_task_self(), mport);

    if (ret != KERN_SUCCESS) {
        psutil_runtime_error(
            "host_statistics(HOST_VM_INFO) failed: %s", mach_error_string(ret)
        );
        return NULL;
    }

    return Py_BuildValue(
        "IIIII",
        vmstat.v_swtch,
        vmstat.v_intr,
        vmstat.v_soft,
#if defined(__MAC_OS_X_VERSION_MIN_REQUIRED) \
    && __MAC_OS_X_VERSION_MIN_REQUIRED__ >= 120000
        0,
#else
        vmstat.v_syscall,
#endif
        vmstat.v_trap
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
    io_iterator_t iter = IO_OBJECT_NULL;
    io_registry_entry_t entry = IO_OBJECT_NULL;
    CFDictionaryRef matching = IOServiceMatching("AppleARMIODevice");
    int found = 0;

    if (!out_entry || !matching)
        return 0;

    status = IOServiceGetMatchingServices(kIOMainPortDefault, matching, &iter);
    if (status != KERN_SUCCESS || iter == IO_OBJECT_NULL)
        return 0;

    while ((entry = IOIteratorNext(iter)) != IO_OBJECT_NULL) {
        io_name_t name;
        if (IORegistryEntryGetName(entry, name) == KERN_SUCCESS
            && strcmp(name, "pmgr") == 0)
        {
            found = 1;
            break;
        }
        IOObjectRelease(entry);
    }

    IOObjectRelease(iter);

    if (found) {
        *out_entry = entry;
        return 1;
    }
    return 0;
}

// Python wrapper: return True/False.
PyObject *
psutil_has_cpu_freq(PyObject *self, PyObject *args) {
    io_registry_entry_t entry = IO_OBJECT_NULL;
    int ok = psutil_find_pmgr_entry(&entry);
    if (entry != IO_OBJECT_NULL)
        IOObjectRelease(entry);
    if (ok)
        Py_RETURN_TRUE;
    Py_RETURN_FALSE;
}


PyObject *
psutil_cpu_freq(PyObject *self, PyObject *args) {
    io_registry_entry_t entry = IO_OBJECT_NULL;
    CFTypeRef pCoreRef = NULL;
    CFTypeRef eCoreRef = NULL;
    size_t pCoreLength = 0;
    uint32_t pMin = 0, eMin = 0, min = 0, max = 0, curr = 0;

    if (!psutil_find_pmgr_entry(&entry)) {
        psutil_runtime_error("'pmgr' entry not found in AppleARMIODevice");
        return NULL;
    }

    pCoreRef = IORegistryEntryCreateCFProperty(
        entry, CFSTR("voltage-states5-sram"), kCFAllocatorDefault, 0
    );
    eCoreRef = IORegistryEntryCreateCFProperty(
        entry, CFSTR("voltage-states1-sram"), kCFAllocatorDefault, 0
    );

    if (!pCoreRef || !eCoreRef || CFGetTypeID(pCoreRef) != CFDataGetTypeID()
        || CFGetTypeID(eCoreRef) != CFDataGetTypeID()
        || CFDataGetLength(pCoreRef) < 8 || CFDataGetLength(eCoreRef) < 4)
    {
        psutil_runtime_error("invalid CPU frequency data");
        goto cleanup;
    }

    pCoreLength = CFDataGetLength(pCoreRef);
    CFDataGetBytes(pCoreRef, CFRangeMake(0, 4), (UInt8 *)&pMin);
    CFDataGetBytes(eCoreRef, CFRangeMake(0, 4), (UInt8 *)&eMin);
    CFDataGetBytes(pCoreRef, CFRangeMake(pCoreLength - 8, 4), (UInt8 *)&max);

    min = (pMin < eMin) ? pMin : eMin;
    curr = max;

cleanup:
    if (pCoreRef)
        CFRelease(pCoreRef);
    if (eCoreRef)
        CFRelease(eCoreRef);
    if (entry != IO_OBJECT_NULL)
        IOObjectRelease(entry);

    return Py_BuildValue(
        "KKK",
        (unsigned long long)(curr / 1000 / 1000),
        (unsigned long long)(min / 1000 / 1000),
        (unsigned long long)(max / 1000 / 1000)
    );
}

#else  // not ARM64 / ARCH64

PyObject *
psutil_has_cpu_freq(PyObject *self, PyObject *args) {
    Py_RETURN_TRUE;
}

PyObject *
psutil_cpu_freq(PyObject *self, PyObject *args) {
    unsigned int curr;
    int64_t min = 0, max = 0;
    int mib[2] = {CTL_HW, HW_CPU_FREQ};

    if (psutil_sysctl(mib, 2, &curr, sizeof(curr)) < 0)
        return psutil_oserror_wsyscall("sysctl(HW_CPU_FREQ)");

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
        (unsigned long long)(max / 1000 / 1000)
    );
}

#endif  // ARM64

PyObject *
psutil_per_cpu_times(PyObject *self, PyObject *args) {
    natural_t cpu_count = 0;
    mach_msg_type_number_t info_count = 0;
    processor_cpu_load_info_data_t *cpu_load_info = NULL;
    processor_info_array_t info_array = NULL;
    kern_return_t error;
    mach_port_t mport = mach_host_self();
    PyObject *py_retlist = PyList_New(0);

    if (!py_retlist)
        return NULL;

    if (mport == MACH_PORT_NULL) {
        psutil_runtime_error("mach_host_self() returned NULL");
        goto error;
    }

    error = host_processor_info(
        mport, PROCESSOR_CPU_LOAD_INFO, &cpu_count, &info_array, &info_count
    );
    mach_port_deallocate(mach_task_self(), mport);

    if (error != KERN_SUCCESS || !info_array) {
        psutil_runtime_error(
            "host_processor_info failed: %s", mach_error_string(error)
        );
        goto error;
    }

    cpu_load_info = (processor_cpu_load_info_data_t *)info_array;

    for (natural_t i = 0; i < cpu_count; i++) {
        PyObject *py_cputime = Py_BuildValue(
            "(dddd)",
            (double)cpu_load_info[i].cpu_ticks[CPU_STATE_USER] / CLK_TCK,
            (double)cpu_load_info[i].cpu_ticks[CPU_STATE_NICE] / CLK_TCK,
            (double)cpu_load_info[i].cpu_ticks[CPU_STATE_SYSTEM] / CLK_TCK,
            (double)cpu_load_info[i].cpu_ticks[CPU_STATE_IDLE] / CLK_TCK
        );
        if (!py_cputime) {
            goto error;
        }
        if (PyList_Append(py_retlist, py_cputime)) {
            Py_DECREF(py_cputime);
            goto error;
        }
        Py_DECREF(py_cputime);
    }

    vm_deallocate(
        mach_task_self(),
        (vm_address_t)info_array,
        info_count * sizeof(integer_t)
    );
    return py_retlist;

error:
    Py_XDECREF(py_retlist);
    if (info_array)
        vm_deallocate(
            mach_task_self(),
            (vm_address_t)info_array,
            info_count * sizeof(integer_t)
        );
    return NULL;
}
