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

#include "../../_psutil_common.h"
#include "../../_psutil_posix.h"


PyObject *
psutil_cpu_count_logical(PyObject *self, PyObject *args) {
    int num;
    size_t size = sizeof(int);

    if (sysctlbyname("hw.logicalcpu", &num, &size, NULL, 2))
        Py_RETURN_NONE;  // mimic os.cpu_count()
    else
        return Py_BuildValue("i", num);
}


PyObject *
psutil_cpu_count_cores(PyObject *self, PyObject *args) {
    int num;
    size_t size = sizeof(int);

    if (sysctlbyname("hw.physicalcpu", &num, &size, NULL, 0))
        Py_RETURN_NONE;  // mimic os.cpu_count()
    else
        return Py_BuildValue("i", num);
}


PyObject *
psutil_cpu_times(PyObject *self, PyObject *args) {
    mach_msg_type_number_t count = HOST_CPU_LOAD_INFO_COUNT;
    kern_return_t error;
    host_cpu_load_info_data_t r_load;

    mach_port_t host_port = mach_host_self();
    error = host_statistics(host_port, HOST_CPU_LOAD_INFO,
                            (host_info_t)&r_load, &count);
    if (error != KERN_SUCCESS) {
        return PyErr_Format(
            PyExc_RuntimeError,
            "host_statistics(HOST_CPU_LOAD_INFO) syscall failed: %s",
            mach_error_string(error));
    }
    mach_port_deallocate(mach_task_self(), host_port);

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
    struct vmmeter vmstat;
    kern_return_t ret;
    mach_msg_type_number_t count = sizeof(vmstat) / sizeof(integer_t);
    mach_port_t mport = mach_host_self();

    ret = host_statistics(mport, HOST_VM_INFO, (host_info_t)&vmstat, &count);
    if (ret != KERN_SUCCESS) {
        PyErr_Format(
            PyExc_RuntimeError,
            "host_statistics(HOST_VM_INFO) failed: %s",
            mach_error_string(ret));
        return NULL;
    }
    mach_port_deallocate(mach_task_self(), mport);

    return Py_BuildValue(
        "IIIII",
        vmstat.v_swtch,  // ctx switches
        vmstat.v_intr,  // interrupts
        vmstat.v_soft,  // software interrupts
        vmstat.v_syscall,  // syscalls
        vmstat.v_trap  // traps
    );
}

#if defined(__arm64__) || defined(__aarch64__)
PyObject *
psutil_cpu_freq(PyObject *self, PyObject *args) {
    uint32_t min;
    uint32_t curr;
    uint32_t pMin;
    uint32_t eMin;
    uint32_t max;
    kern_return_t status;
    CFDictionaryRef matching = NULL;
    CFTypeRef pCoreRef = NULL;
    CFTypeRef eCoreRef = NULL;
    io_iterator_t iter = 0;
    io_registry_entry_t entry = 0;
    io_name_t name;

    matching = IOServiceMatching("AppleARMIODevice");
    if (matching == 0) {
        return PyErr_Format(
            PyExc_RuntimeError,
            "IOServiceMatching call failed, 'AppleARMIODevice' not found"
        );
    }

    status = IOServiceGetMatchingServices(kIOMainPortDefault, matching, &iter);
    if (status != KERN_SUCCESS) {
        PyErr_Format(
            PyExc_RuntimeError, "IOServiceGetMatchingServices call failed"
        );
        goto error;
    }

    while ((entry = IOIteratorNext(iter)) != 0) {
        status = IORegistryEntryGetName(entry, name);
        if (status != KERN_SUCCESS) {
            IOObjectRelease(entry);
            continue;
        }
        if (strcmp(name, "pmgr") == 0) {
            break;
        }
        IOObjectRelease(entry);
    }

    if (entry == 0) {
        PyErr_Format(
            PyExc_RuntimeError,
            "'pmgr' entry was not found in AppleARMIODevice service"
        );
        goto error;
    }

    pCoreRef = IORegistryEntryCreateCFProperty(
        entry, CFSTR("voltage-states5-sram"), kCFAllocatorDefault, 0);
    if (pCoreRef == NULL) {
        PyErr_Format(
            PyExc_RuntimeError, "'voltage-states5-sram' property not found");
        goto error;
    }

    eCoreRef = IORegistryEntryCreateCFProperty(
        entry, CFSTR("voltage-states1-sram"), kCFAllocatorDefault, 0);
    if (eCoreRef == NULL) {
        PyErr_Format(
            PyExc_RuntimeError, "'voltage-states1-sram' property not found");
        goto error;
    }

    size_t pCoreLength = CFDataGetLength(pCoreRef);
    size_t eCoreLength = CFDataGetLength(eCoreRef);
    if (pCoreLength < 8) {
        PyErr_Format(
            PyExc_RuntimeError,
            "expected 'voltage-states5-sram' buffer to have at least size 8"
        );
        goto error;
    }
    if (eCoreLength < 4) {
        PyErr_Format(
            PyExc_RuntimeError,
            "expected 'voltage-states1-sram' buffer to have at least size 4"
        );
        goto error;
    }

    CFDataGetBytes(pCoreRef, CFRangeMake(0, 4), (UInt8 *) &pMin);
    CFDataGetBytes(eCoreRef, CFRangeMake(0, 4), (UInt8 *) &eMin);
    CFDataGetBytes(pCoreRef, CFRangeMake(pCoreLength - 8, 4), (UInt8 *) &max);

    min = pMin < eMin ? pMin : eMin;
    curr = max;

    CFRelease(pCoreRef);
    CFRelease(eCoreRef);
    IOObjectRelease(iter);
    IOObjectRelease(entry);

    return Py_BuildValue(
        "IKK",
        curr / 1000 / 1000,
        min / 1000 / 1000,
        max / 1000 / 1000
    );

error:
    if (pCoreRef != NULL)
        CFRelease(pCoreRef);
    if (eCoreRef != NULL)
        CFRelease(eCoreRef);
    if (iter != 0)
        IOObjectRelease(iter);
    if (entry != 0)
        IOObjectRelease(entry);
    return NULL;
}
#else
PyObject *
psutil_cpu_freq(PyObject *self, PyObject *args) {
    unsigned int curr;
    int64_t min = 0;
    int64_t max = 0;
    int mib[2];
    size_t len = sizeof(curr);
    size_t size = sizeof(min);

    // also available as "hw.cpufrequency" but it's deprecated
    mib[0] = CTL_HW;
    mib[1] = HW_CPU_FREQ;

    if (sysctl(mib, 2, &curr, &len, NULL, 0) < 0)
        return psutil_PyErr_SetFromOSErrnoWithSyscall("sysctl(HW_CPU_FREQ)");

    if (sysctlbyname("hw.cpufrequency_min", &min, &size, NULL, 0))
        psutil_debug("sysctl('hw.cpufrequency_min') failed (set to 0)");

    if (sysctlbyname("hw.cpufrequency_max", &max, &size, NULL, 0))
        psutil_debug("sysctl('hw.cpufrequency_min') failed (set to 0)");

    return Py_BuildValue(
        "IKK",
        curr / 1000 / 1000,
        min / 1000 / 1000,
        max / 1000 / 1000);
}
#endif

PyObject *
psutil_per_cpu_times(PyObject *self, PyObject *args) {
    natural_t cpu_count;
    natural_t i;
    processor_info_array_t info_array;
    mach_msg_type_number_t info_count;
    kern_return_t error;
    processor_cpu_load_info_data_t *cpu_load_info = NULL;
    int ret;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_cputime = NULL;

    if (py_retlist == NULL)
        return NULL;

    mach_port_t host_port = mach_host_self();
    error = host_processor_info(host_port, PROCESSOR_CPU_LOAD_INFO,
                                &cpu_count, &info_array, &info_count);
    if (error != KERN_SUCCESS) {
        PyErr_Format(
            PyExc_RuntimeError,
            "host_processor_info(PROCESSOR_CPU_LOAD_INFO) syscall failed: %s",
             mach_error_string(error));
        goto error;
    }
    mach_port_deallocate(mach_task_self(), host_port);

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
        if (PyList_Append(py_retlist, py_cputime))
            goto error;
        Py_CLEAR(py_cputime);
    }

    ret = vm_deallocate(mach_task_self(), (vm_address_t)info_array,
                        info_count * sizeof(int));
    if (ret != KERN_SUCCESS)
        PyErr_WarnEx(PyExc_RuntimeWarning, "vm_deallocate() failed", 2);
    return py_retlist;

error:
    Py_XDECREF(py_cputime);
    Py_DECREF(py_retlist);
    if (cpu_load_info != NULL) {
        ret = vm_deallocate(mach_task_self(), (vm_address_t)info_array,
                            info_count * sizeof(int));
        if (ret != KERN_SUCCESS)
            PyErr_WarnEx(PyExc_RuntimeWarning, "vm_deallocate() failed", 2);
    }
    return NULL;
}
