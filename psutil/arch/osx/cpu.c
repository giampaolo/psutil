/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

/*
System-wide CPU related functions.

References:
- https://opensource.apple.com/source/xnu/xnu-1456.1.26/bsd/sys/sysctl.h.auto.html
- sysctl C types: https://ss64.com/osx/sysctl.html
- https://apple.stackexchange.com/questions/238777
- it looks like CPU "sockets" on macOS are called "packages"
- it looks like macOS does not support NUMA nodes:
  https://apple.stackexchange.com/questions/36465/do-mac-pros-use-numa
- $ sysctl -a | grep machdep.cpu

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
#include <sys/sysctl.h>
#include <ctype.h>
#include <sys/sysctl.h>
#include <sys/vmmeter.h>

#include <mach/mach_error.h>
#include <mach/mach_host.h>
#include <mach/mach_port.h>

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
psutil_cpu_sockets() {
    // It looks like on macOS "sockets" are called "packages".
    // Hopefully it's the same thing.
    int value;
    size_t size = sizeof(value);

    if (sysctlbyname("hw.packages", &value, &size, NULL, 2))
        Py_RETURN_NONE;
    else
        return Py_BuildValue("i", value);
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


PyObject *
psutil_cpu_freq(PyObject *self, PyObject *args) {
    unsigned int curr;
    int64_t min = 0;
    int64_t max = 0;
    int mib[2];
    size_t len = sizeof(curr);
    size_t size = sizeof(min);

    // also availble as "hw.cpufrequency" but it's deprecated
    mib[0] = CTL_HW;
    mib[1] = HW_CPU_FREQ;

    if (sysctl(mib, 2, &curr, &len, NULL, 0) < 0)
        return PyErr_SetFromOSErrnoWithSyscall("sysctl(HW_CPU_FREQ)");

    if (sysctlbyname("hw.cpufrequency_min", &min, &size, NULL, 0))
        psutil_debug("sysct('hw.cpufrequency_min') failed (set to 0)");

    if (sysctlbyname("hw.cpufrequency_max", &max, &size, NULL, 0))
        psutil_debug("sysctl('hw.cpufrequency_min') failed (set to 0)");

    return Py_BuildValue(
        "IKK",
        curr / 1000 / 1000,
        min / 1000 / 1000,
        max / 1000 / 1000);
}


PyObject *
psutil_cpu_model() {
    size_t len;
    char *buffer;
    PyObject *py_str = NULL;

    if (sysctlbyname("machdep.cpu.brand_string", NULL, &len, NULL, 0) != 0) {
        psutil_debug("sysctlbyname('machdep.cpu.brand_string') "
                     "failed (ignored)");
        Py_RETURN_NONE;
    }

    buffer = malloc(len);
    if (sysctlbyname("machdep.cpu.brand_string", buffer, &len, NULL, 0) != 0) {
        free(buffer);
        psutil_debug("sysctlbyname('machdep.cpu.brand_string') "
                     "failed (ignored)");
        Py_RETURN_NONE;
    }

    py_str = Py_BuildValue("s", buffer);
    free(buffer);
    return py_str;
}


PyObject *
psutil_cpu_vendor() {
    size_t len;
    char *buffer;
    PyObject *py_str = NULL;

    if (sysctlbyname("machdep.cpu.vendor", NULL, &len, NULL, 0) != 0) {
        psutil_debug("sysctlbyname('machdep.cpu.vendor') failed (ignored)");
        Py_RETURN_NONE;
    }

    buffer = malloc(len);
    if (sysctlbyname("machdep.cpu.vendor", buffer, &len, NULL, 0) != 0) {
        free(buffer);
        psutil_debug("sysctlbyname('machdep.cpu.vendor') failed (ignored)");
        Py_RETURN_NONE;
    }

    py_str = Py_BuildValue("s", buffer);
    free(buffer);
    return py_str;
}


PyObject *
psutil_cpu_flags() {
    size_t len1;
    size_t len2;
    char *buf1 = NULL;
    char *buf2 = NULL;
    char *buf3 = NULL;
    int i;
    PyObject *py_str = NULL;

    // There are standard and extended features (both strings). First,
    // get the size for both.
    if (sysctlbyname("machdep.cpu.features", NULL, &len1, NULL, 0) != 0) {
        psutil_debug("sysctlbyname('machdep.cpu.features') failed (ignored)");
        Py_RETURN_NONE;
    }

    if (sysctlbyname("machdep.cpu.extfeatures", NULL, &len2, NULL, 0) != 0) {
        psutil_debug("sysctlbyname('machdep.cpu.extfeatures') failed (ignored)");
        Py_RETURN_NONE;
    }

    // Now we get the real values; we need 2 mallocs.

    // ...standard
    buf1 = malloc(len1);
    if (buf1 == NULL) {
        PyErr_NoMemory();
        goto error;
    }
    if (sysctlbyname("machdep.cpu.features", buf1, &len1, NULL, 0) != 0) {
        psutil_debug("sysctlbyname('machdep.cpu.features') failed (ignored)");
        goto error;
    }

    // ...extended
    buf2 = malloc(len2);
    if (buf2 == NULL) {
        PyErr_NoMemory();
        goto error;
    }
    if (sysctlbyname("machdep.cpu.extfeatures", buf2, &len2, NULL, 0) != 0) {
        psutil_debug("sysctlbyname('machdep.cpu.extfeatures') failed (ignored)");
        goto error;
    }

    // Lower case both strings (mimic Linux lscpu).
    for (i = 0; buf1[i]; i++)
        buf1[i] = tolower(buf1[i]);
    for (i = 0; buf2[i]; i++)
        buf2[i] = tolower(buf2[i]);

    // Make space for both in a new buffer and join them (+1 is for the
    // null terminator).
    buf3 = malloc(len1 + len2 + 1);
    if (buf3 == NULL) {
        PyErr_NoMemory();
        goto error;
    }
    sprintf(buf3, "%s %s", buf1, buf2);

    // Return.
    py_str = Py_BuildValue("s", buf3);
    free(buf1);
    free(buf2);
    free(buf3);
    return py_str;

error:
    if (buf1 != NULL)
        free(buf1);
    if (buf2 != NULL)
        free(buf2);
    if (buf3 != NULL)
        free(buf3);
    if (PyErr_Occurred())  // malloc failed
        return NULL;
    Py_RETURN_NONE;
}


// also available as sysctlbyname("hw.l1icachesize") but it returns 1
PyObject *
psutil_cpu_l1i_cache() {
    int value;
    size_t len = sizeof(value);
    int mib[2] = { CTL_HW, HW_L1ICACHESIZE };

    if (sysctl(mib, 2, &value, &len, NULL, 0) < 0) {
        psutil_debug("sysctl(HW_L1ICACHESIZE) failed (ignored)");
        Py_RETURN_NONE;
    }
    return Py_BuildValue("i", value);
}


// also available as sysctlbyname("hw.l1dcachesize") but it returns 1
PyObject *
psutil_cpu_l1d_cache() {
    int value;
    size_t len = sizeof(value);
    int mib[2] = { CTL_HW, HW_L1DCACHESIZE };

    if (sysctl(mib, 2, &value, &len, NULL, 0) < 0) {
        psutil_debug("sysctl(HW_L1DCACHESIZE) failed (ignored)");
        Py_RETURN_NONE;
    }
    return Py_BuildValue("i", value);
}


// also available as sysctlbyname("hw.l2cachesize") but it returns 1
PyObject *
psutil_cpu_l2_cache() {
    int value;
    size_t len = sizeof(value);
    int mib[2] = { CTL_HW, HW_L2CACHESIZE };

    if (sysctl(mib, 2, &value, &len, NULL, 0) < 0) {
        psutil_debug("sysctl(HW_L2CACHESIZE) failed (ignored)");
        Py_RETURN_NONE;
    }
    return Py_BuildValue("i", value);
}


// also available as sysctlbyname("hw.l3cachesize") but it returns 1
PyObject *
psutil_cpu_l3_cache() {
    int value;
    size_t len = sizeof(value);
    int mib[2] = { CTL_HW, HW_L3CACHESIZE };

    if (sysctl(mib, 2, &value, &len, NULL, 0) < 0) {
        psutil_debug("sysctl(HW_L3CACHESIZE) failed (ignored)");
        Py_RETURN_NONE;
    }
    return Py_BuildValue("i", value);
}


/*
PyObject *
psutil_cpu_num_cores_per_socket() {
    int value;
    size_t size = sizeof(value);

    if (sysctlbyname("machdep.cpu.cores_per_package",
                     &value, &size, NULL, 0) != 0) {
        psutil_debug("sysctlbyname('machdep.cpu.cores_per_package') "
                     "failed (ignored)");
        Py_RETURN_NONE;
    }
    return Py_BuildValue("i", value);
}


// "threads_per_core" is how it's being called by lscpu on Linux.
// Here it's "thread_count". Hopefully it's the same thing.
PyObject *
psutil_cpu_threads_per_core() {
    int value;
    size_t size = sizeof(value);

    if (sysctlbyname("machdep.cpu.thread_count",
                     &value, &size, NULL, 0) != 0) {
        psutil_debug("sysctlbyname('machdep.cpu.thread_count') "
                     "failed (ignored)");
        Py_RETURN_NONE;
    }
    return Py_BuildValue("i", value);
}
*/
