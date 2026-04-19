/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// System-wide CPU related functions.
//
// Original code was refactored and moved from psutil/_psutil_osx.c in 2020,
// right before a4c0a0eb0d2a872ab7a45e47fcf37ef1fde5b012.
//
// For reference, here's the git history with original implementations:
// - CPU count logical: 3d291d425b856077e65163e43244050fb188def1
// - CPU count physical: 4263e354bb4984334bc44adf5dd2f32013d69fba
// - CPU times: 32488bdf54aed0f8cef90d639c1667ffaa3c31c7
// - CPU stat: fa00dfb961ef63426c7818899340866ced8d2418
// - CPU frequency: 6ba1ac4ebfcd8c95fca324b15606ab0ec1412d39

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


// Compute overall min/max CPU frequency by enumerating every
// `voltage-states<N>-sram` property on the pmgr entry. This design
// deliberately avoids:
//   - hard-coding specific property indexes (Apple renumbered the
//     `voltage-statesN-sram` key space on M5-family chips, so any
//     fixed index assumption breaks there)
//   - dispatching on chip generation (the raw values tell us the unit
//     themselves; no lookup table required)
// Apple M1-M3 encode frequencies in Hz; M4+ switched to kHz. The unit
// is detected per-value by magnitude. Observed Apple Silicon range
// M1-M5 is ~0.6-4.6 GHz, so Hz values are >>1e8 while kHz values are
// <<1e8.
//
// The `-sram` suffix alone is not a CPU discriminator: on M3 Max the
// GPU / NPU / fabric subsystems also publish -sram DVFS tables (e.g.
// `voltage-states9-sram`, `voltage-states14..16-sram`) with fmax
// around 1.4 GHz. We additionally require each table's fmax to exceed
// 2 GHz to qualify as a CPU cluster; this is the same per-table filter
// macpow uses, and is comfortably above observed GPU peaks (~1.6 GHz)
// while below every CPU cluster fmax ever shipped (M1 E-core at 2064
// MHz is the lowest). Forward risk: Apple Silicon GPU fmax is rising
// ~10%/generation, so the 2 GHz floor is expected to give several
// generations of headroom — revisit if a future chip closes the gap.
PyObject *
psutil_cpu_freq(PyObject *self, PyObject *args) {
    static const char KEY_PREFIX[] = "voltage-states";
    static const char KEY_SUFFIX[] = "-sram";
    static const size_t KEY_PREFIX_LEN = sizeof(KEY_PREFIX) - 1;
    static const size_t KEY_SUFFIX_LEN = sizeof(KEY_SUFFIX) - 1;
    // Raw frequency values above 10^8 are Hz; below are kHz.
    static const uint32_t UNIT_THRESHOLD = 100000000U;
    // Per-value plausibility bounds. Drops terminator zeros and any
    // junk the enumeration might pick up.
    static const uint32_t MIN_PLAUSIBLE_MHZ = 500;
    static const uint32_t MAX_PLAUSIBLE_MHZ = 20000;
    // Per-table classification: CPU clusters have fmax >= 2 GHz. See
    // block comment above for justification.
    static const uint32_t CPU_CLUSTER_MIN_FMAX_MHZ = 2000;

    io_registry_entry_t entry = IO_OBJECT_NULL;
    CFMutableDictionaryRef props = NULL;
    const void **keys = NULL;
    const void **values = NULL;
    CFIndex count = 0;
    uint32_t min_mhz = UINT32_MAX;
    uint32_t max_mhz = 0;
    int found_any = 0;

    if (!psutil_find_pmgr_entry(&entry)) {
        psutil_runtime_error("'pmgr' entry not found in AppleARMIODevice");
        return NULL;
    }

    if (IORegistryEntryCreateCFProperties(
            entry, &props, kCFAllocatorDefault, 0
        ) != KERN_SUCCESS
        || props == NULL)
    {
        IOObjectRelease(entry);
        psutil_runtime_error("IORegistryEntryCreateCFProperties failed");
        return NULL;
    }

    count = CFDictionaryGetCount(props);
    if (count > 0) {
        keys = (const void **)malloc(count * sizeof(void *));
        values = (const void **)malloc(count * sizeof(void *));
        if (keys == NULL || values == NULL) {
            free(keys);
            free(values);
            CFRelease(props);
            IOObjectRelease(entry);
            PyErr_NoMemory();
            return NULL;
        }
        CFDictionaryGetKeysAndValues(props, keys, values);
    }

    for (CFIndex i = 0; i < count; i++) {
        CFStringRef key = (CFStringRef)keys[i];
        CFTypeRef value = (CFTypeRef)values[i];
        char name[64];
        size_t name_len;
        int all_digits;

        // Key must be "voltage-states<N>-sram" where N is one or more digits.
        if (CFGetTypeID(key) != CFStringGetTypeID())
            continue;
        if (!CFStringGetCString(
                key, name, sizeof(name), kCFStringEncodingUTF8
            ))
            continue;
        name_len = strlen(name);
        if (name_len < KEY_PREFIX_LEN + 1 + KEY_SUFFIX_LEN)
            continue;
        if (strncmp(name, KEY_PREFIX, KEY_PREFIX_LEN) != 0)
            continue;
        if (strcmp(name + name_len - KEY_SUFFIX_LEN, KEY_SUFFIX) != 0)
            continue;
        all_digits = 1;
        for (size_t j = KEY_PREFIX_LEN; j < name_len - KEY_SUFFIX_LEN; j++) {
            if (name[j] < '0' || name[j] > '9') {
                all_digits = 0;
                break;
            }
        }
        if (!all_digits)
            continue;

        if (CFGetTypeID(value) != CFDataGetTypeID())
            continue;

        // Each DVFS entry is 8 bytes: 4-byte LE freq + 4-byte LE voltage.
        // Accumulate this table's min/max first; then fold into overall
        // min/max only if the table's fmax qualifies it as a CPU cluster.
        uint32_t table_min = UINT32_MAX;
        uint32_t table_max = 0;
        int table_has_value = 0;
        CFIndex blob_len = CFDataGetLength((CFDataRef)value);
        const UInt8 *bytes = CFDataGetBytePtr((CFDataRef)value);
        for (CFIndex off = 0; off + 4 <= blob_len; off += 8) {
            uint32_t raw_freq;
            uint32_t freq_mhz;

            // ARM64 is little-endian; copy 4 bytes as native uint32.
            memcpy(&raw_freq, bytes + off, sizeof(raw_freq));

            if (raw_freq > UNIT_THRESHOLD)
                freq_mhz = raw_freq / 1000U / 1000U;  // Hz -> MHz
            else
                freq_mhz = raw_freq / 1000U;  // kHz -> MHz

            if (freq_mhz < MIN_PLAUSIBLE_MHZ || freq_mhz > MAX_PLAUSIBLE_MHZ)
                continue;

            if (freq_mhz < table_min)
                table_min = freq_mhz;
            if (freq_mhz > table_max)
                table_max = freq_mhz;
            table_has_value = 1;
        }

        if (!table_has_value || table_max < CPU_CLUSTER_MIN_FMAX_MHZ)
            continue;

        if (table_min < min_mhz)
            min_mhz = table_min;
        if (table_max > max_mhz)
            max_mhz = table_max;
        found_any = 1;
    }

    free(keys);
    free(values);
    CFRelease(props);
    IOObjectRelease(entry);

    if (!found_any) {
        psutil_runtime_error(
            "no valid CPU frequency data found in pmgr voltage-states tables"
        );
        return NULL;
    }

    // No real current-frequency API on Apple Silicon; report max as current.
    return Py_BuildValue(
        "KKK",
        (unsigned long long)max_mhz,
        (unsigned long long)min_mhz,
        (unsigned long long)max_mhz
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
        if (!pylist_append_fmt(
                py_retlist,
                "(dddd)",
                (double)cpu_load_info[i].cpu_ticks[CPU_STATE_USER] / CLK_TCK,
                (double)cpu_load_info[i].cpu_ticks[CPU_STATE_NICE] / CLK_TCK,
                (double)cpu_load_info[i].cpu_ticks[CPU_STATE_SYSTEM] / CLK_TCK,
                (double)cpu_load_info[i].cpu_ticks[CPU_STATE_IDLE] / CLK_TCK
            ))
        {
            goto error;
        }
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
