/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>
#include <PowrProf.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <intrin.h>

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

    // gets cpu time informations
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
        Py_RETURN_NONE;  // mimick os.cpu_count()
}


/*
 * Re-adapted from:
 * https://docs.microsoft.com/en-us/windows/win32/api/sysinfoapi/
 *     nf-sysinfoapi-getlogicalprocessorinformation?redirectedfrom=MSDN
 */
PyObject *
psutil_GetLogicalProcessorInformationEx(PyObject *self, PyObject *args) {
    DWORD rc;
    PSYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX buffer = NULL;
    PSYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX ptr = NULL;
    DWORD length = 0;
    DWORD offset = 0;
    DWORD coresCount = 0;
    DWORD socketsCount = 0;
    DWORD numaNodesCount = 0;
    DWORD L1CacheCount = 0;
    DWORD L2CacheCount = 0;
    DWORD L3CacheCount = 0;
    DWORD prevProcInfoSize = 0;
    PCACHE_RELATIONSHIP Cache;
    PyObject *py_retdict = PyDict_New();

    if (py_retdict == NULL)
        return NULL;

    // GetLogicalProcessorInformationEx() is available from Windows 7
    // onward. Differently from GetLogicalProcessorInformation()
    // it supports process groups, meaning this is able to report more
    // than 64 CPUs. See:
    // https://bugs.python.org/issue33166
    if (GetLogicalProcessorInformationEx == NULL) {
        psutil_debug("Win < 7; cpu_count_cores() forced to None");
        return py_retdict;
    }

    while (1) {
        rc = GetLogicalProcessorInformationEx(RelationAll, buffer, &length);
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
                PyErr_SetFromOSErrnoWithSyscall(
                    "GetLogicalProcessorInformationEx");
                return NULL;
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
            (((char*)ptr) + prevProcInfoSize);

        if (ptr->Relationship == RelationProcessorCore) {
            coresCount += 1;
        }
        else if (ptr->Relationship == RelationProcessorCore) {
            numaNodesCount += 1;
        }
        else if (ptr->Relationship == RelationProcessorPackage) {
            socketsCount += 1;
        }
        else if (ptr->Relationship == RelationCache) {
            // Cache data is in ptr->Cache, one CACHE_DESCRIPTOR structure for each cache.
            Cache = &ptr->Cache;
            if (Cache->Level == 1)
                L1CacheCount = Cache->CacheSize;
            else if (Cache->Level == 2)
                L2CacheCount = Cache->CacheSize;
            else if (Cache->Level == 3)
                L3CacheCount = Cache->CacheSize;
        }

        // When offset == length, we've reached the last processor
        // info struct in the buffer.
        offset += ptr->Size;
        prevProcInfoSize = ptr->Size;
    }

    free(buffer);

    if (psutil_add_to_dict(py_retdict, "cores",
                           Py_BuildValue("I", coresCount)) == 1) {
        return NULL;
    }
    if (psutil_add_to_dict(py_retdict, "sockets",
                           Py_BuildValue("I", socketsCount)) == 1) {
        return NULL;
    }
    if (psutil_add_to_dict(py_retdict, "numa",
                           Py_BuildValue("I", numaNodesCount)) == 1) {
        return NULL;
    }
    if (psutil_add_to_dict(py_retdict, "l1_cache",
                           Py_BuildValue("I", L1CacheCount)) == 1) {
        return NULL;
    }
    if (psutil_add_to_dict(py_retdict, "l2_cache",
                           Py_BuildValue("I", L2CacheCount)) == 1) {
        return NULL;
    }
    if (psutil_add_to_dict(py_retdict, "l3_cache",
                           Py_BuildValue("I", L3CacheCount)) == 1) {
        return NULL;
    }
    return py_retdict;
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


// CPU info for x86, x64 processors.
// Re-adapted from: https://docs.microsoft.com/en-us/previous-versions/
//     visualstudio/visual-studio-2008/hskdteyh(v=vs.90)?redirectedfrom=MSDN
// List of CPU flags
// https://project.altservice.com/documents/14

static char* szFeatures[] = {
    "fpu",          // "x87 FPU On Chip",
    "vme",          // "Virtual-8086 Mode Enhancement",
    "de",           // "Debugging Extensions",
    "psa",          // "Page Size Extensions",
    "tsc",          // "Time Stamp Counter",
    "msr",          // "RDMSR and WRMSR Support",
    "pae",          // "Physical Address Extensions",
    "mce",          // "Machine Check Exception",
    "cx8",          // "CMPXCHG8B Instruction",
    "apic",         // "APIC On Chip",
    "unknown1",     // "Unknown1",
    "sep",          // "SYSENTER and SYSEXIT",
    "mtrr",         // "Memory Type Range Registers",
    "pge",          // "PTE Global Bit",
    "mca",          // "Machine Check Architecture",
    "cmov",         // "Conditional Move/Compare Instruction",
    "pat",          // "Page Attribute Table",
    "pse36",        // "36-bit Page Size Extension",
    "pn",           // "Processor Serial Number",
    "clflush",      // "CFLUSH Extension",
    "unknown2",     // "Unknown2",
    "dts",          // "Debug Store",
    "tmclockctrl",  // "Thermal Monitor and Clock Ctrl",  ???
    "mmx",          // "MMX Technology",
    "fxsr",         // "FXSAVE/FXRSTOR",
    "sse",          // "SSE Extensions",
    "sse2",         // "SSE2 Extensions",
    "ss",           // "Self Snoop",
    "mthread",      // "Multithreading Technology",
    "tm",           // "Thermal Monitor",
    "unknown4",     // "Unknown4",
    "pbe",          // "Pending Break Enable"
};


static void
stradd(char *base, int len, char *tail) {
    if (strlen(base) != 0)
        strcat_s(base, len, " ");
    strcat_s(base, len, tail);
}


PyObject *
psutil_cpu_info(PyObject *self, PyObject *args) {
    char CPUString[0x20];
    char CPUBrandString[0x40];
    int CPUInfo[4] = {-1};
    int nSteppingID = 0;
    int nModel = 0;
    int nFamily = 0;
    int nProcessorType = 0;
    int nExtendedmodel = 0;
    int nExtendedfamily = 0;
    int nBrandIndex = 0;
    int nCLFLUSHcachelinesize = 0;
    int nLogicalProcessors = 0;
    int nAPICPhysicalID = 0;
    int nFeatureInfo = 0;
    int nCacheLineSize = 0;
    int nL2Associativity = 0;
    int nCacheSizeK = 0;
    int nPhysicalAddress = 0;
    int nVirtualAddress = 0;
    int nRet = 0;

    int nCores = 0;
    int nCacheType = 0;
    int nCacheLevel = 0;
    int nMaxThread = 0;
    int nSysLineSize = 0;
    int nPhysicalLinePartitions = 0;
    int nWaysAssociativity = 0;
    int nNumberSets = 0;

    unsigned nIds, nExIds, i;

    bool bSSE3Instructions = false;
    bool bMONITOR_MWAIT = false;
    bool bCPLQualifiedDebugStore = false;
    bool bVirtualMachineExtensions = false;
    bool bEnhancedIntelSpeedStepTechnology = false;
    bool bThermalMonitor2 = false;
    bool bSupplementalSSE3 = false;
    bool bL1ContextID = false;
    bool bCMPXCHG16B = false;
    bool bxTPRUpdateControl = false;
    bool bPerfDebugCapabilityMSR = false;
    bool bSSE41Extensions = false;
    bool bSSE42Extensions = false;
    bool bPOPCNT = false;

    bool bMultithreading = false;

    bool bLAHF_SAHFAvailable = false;
    bool bCmpLegacy = false;
    bool bSVM = false;
    bool bExtApicSpace = false;
    bool bAltMovCr8 = false;
    bool bLZCNT = false;
    bool bSSE4A = false;
    bool bMisalignedSSE = false;
    bool bPREFETCH = false;
    bool bSKINITandDEV = false;
    bool bSYSCALL_SYSRETAvailable = false;
    bool bExecuteDisableBitAvailable = false;
    bool bMMXExtensions = false;
    bool bFFXSR = false;
    bool b1GBSupport = false;
    bool bRDTSCP = false;
    bool b64Available = false;
    bool b3DNowExt = false;
    bool b3DNow = false;
    bool bNestedPaging = false;
    bool bLBRVisualization = false;
    bool bFP128 = false;
    bool bMOVOptimization = false;

    bool bSelfInit = false;
    bool bFullyAssociative = false;
    char flags[900] = "";

    PyObject *py_retdict = PyDict_New();

    if (py_retdict == NULL)
        return NULL;

    // __cpuid with an InfoType argument of 0 returns the number of
    // valid Ids in CPUInfo[0] and the CPU identification string in
    // the other three array elements. The CPU identification string is
    // not in linear order. The code below arranges the information
    // in a human readable form.
    __cpuid(CPUInfo, 0);
    nIds = CPUInfo[0];
    memset(CPUString, 0, sizeof(CPUString));
    *((int*)CPUString) = CPUInfo[1];
    *((int*)(CPUString+4)) = CPUInfo[3];
    *((int*)(CPUString+8)) = CPUInfo[2];

    // Get the information associated with each valid Id
    for (i=0; i <= nIds; ++i) {
        __cpuid(CPUInfo, i);

        // Interpret CPU feature information.
        if  (i == 1) {
            nSteppingID = CPUInfo[0] & 0xf;
            nModel = (CPUInfo[0] >> 4) & 0xf;
            nFamily = (CPUInfo[0] >> 8) & 0xf;
            nProcessorType = (CPUInfo[0] >> 12) & 0x3;
            nExtendedmodel = (CPUInfo[0] >> 16) & 0xf;
            nExtendedfamily = (CPUInfo[0] >> 20) & 0xff;
            nBrandIndex = CPUInfo[1] & 0xff;
            nCLFLUSHcachelinesize = ((CPUInfo[1] >> 8) & 0xff) * 8;
            nLogicalProcessors = ((CPUInfo[1] >> 16) & 0xff);
            nAPICPhysicalID = (CPUInfo[1] >> 24) & 0xff;
            bSSE3Instructions = (CPUInfo[2] & 0x1) || false;
            bMONITOR_MWAIT = (CPUInfo[2] & 0x8) || false;
            bCPLQualifiedDebugStore = (CPUInfo[2] & 0x10) || false;
            bVirtualMachineExtensions = (CPUInfo[2] & 0x20) || false;
            bEnhancedIntelSpeedStepTechnology = (CPUInfo[2] & 0x80) || false;
            bThermalMonitor2 = (CPUInfo[2] & 0x100) || false;
            bSupplementalSSE3 = (CPUInfo[2] & 0x200) || false;
            bL1ContextID = (CPUInfo[2] & 0x300) || false;
            bCMPXCHG16B= (CPUInfo[2] & 0x2000) || false;
            bxTPRUpdateControl = (CPUInfo[2] & 0x4000) || false;
            bPerfDebugCapabilityMSR = (CPUInfo[2] & 0x8000) || false;
            bSSE41Extensions = (CPUInfo[2] & 0x80000) || false;
            bSSE42Extensions = (CPUInfo[2] & 0x100000) || false;
            bPOPCNT= (CPUInfo[2] & 0x800000) || false;
            nFeatureInfo = CPUInfo[3];
            bMultithreading = (nFeatureInfo & (1 << 28)) || false;
        }
    }

    // Calling __cpuid with 0x80000000 as the InfoType argument
    // gets the number of valid extended IDs.
    __cpuid(CPUInfo, 0x80000000);
    nExIds = CPUInfo[0];
    memset(CPUBrandString, 0, sizeof(CPUBrandString));

    // Get the information associated with each extended ID.
    for (i=0x80000000; i<=nExIds; ++i) {
        __cpuid(CPUInfo, i);
        if  (i == 0x80000001) {
            bLAHF_SAHFAvailable = (CPUInfo[2] & 0x1) || false;
            bCmpLegacy = (CPUInfo[2] & 0x2) || false;
            bSVM = (CPUInfo[2] & 0x4) || false;
            bExtApicSpace = (CPUInfo[2] & 0x8) || false;
            bAltMovCr8 = (CPUInfo[2] & 0x10) || false;
            bLZCNT = (CPUInfo[2] & 0x20) || false;
            bSSE4A = (CPUInfo[2] & 0x40) || false;
            bMisalignedSSE = (CPUInfo[2] & 0x80) || false;
            bPREFETCH = (CPUInfo[2] & 0x100) || false;
            bSKINITandDEV = (CPUInfo[2] & 0x1000) || false;
            bSYSCALL_SYSRETAvailable = (CPUInfo[3] & 0x800) || false;
            bExecuteDisableBitAvailable = (CPUInfo[3] & 0x10000) || false;
            bMMXExtensions = (CPUInfo[3] & 0x40000) || false;
            bFFXSR = (CPUInfo[3] & 0x200000) || false;
            b1GBSupport = (CPUInfo[3] & 0x400000) || false;
            bRDTSCP = (CPUInfo[3] & 0x8000000) || false;
            b64Available = (CPUInfo[3] & 0x20000000) || false;
            b3DNowExt = (CPUInfo[3] & 0x40000000) || false;
            b3DNow = (CPUInfo[3] & 0x80000000) || false;
        }

        // Interpret CPU brand string and cache information.
        if  (i == 0x80000002)
            memcpy(CPUBrandString, CPUInfo, sizeof(CPUInfo));
        else if  (i == 0x80000003)
            memcpy(CPUBrandString + 16, CPUInfo, sizeof(CPUInfo));
        else if  (i == 0x80000004)
            memcpy(CPUBrandString + 32, CPUInfo, sizeof(CPUInfo));
        else if  (i == 0x80000006) {
            nCacheLineSize = CPUInfo[2] & 0xff;
            nL2Associativity = (CPUInfo[2] >> 12) & 0xf;
            nCacheSizeK = (CPUInfo[2] >> 16) & 0xffff;
        }
        else if  (i == 0x80000008) {
           nPhysicalAddress = CPUInfo[0] & 0xff;
           nVirtualAddress = (CPUInfo[0] >> 8) & 0xff;
        }
        else if  (i == 0x8000000A) {
            bNestedPaging = (CPUInfo[3] & 0x1) || false;
            bLBRVisualization = (CPUInfo[3] & 0x2) || false;
        }
        else if  (i == 0x8000001A) {
            bFP128 = (CPUInfo[0] & 0x1) || false;
            bMOVOptimization = (CPUInfo[0] & 0x2) || false;
        }
    }

    if (psutil_add_to_dict(py_retdict, "vendor",
                           Py_BuildValue("s", CPUString)) == 1)
        goto error;

    if  (nIds >= 1) {
        /*
        if (nSteppingID)
            printf_s("Stepping ID = %d\n", nSteppingID);
        if (nModel)
            printf_s("Model = %d\n", nModel);
        if (nFamily)
            printf_s("Family = %d\n", nFamily);
        if (nProcessorType)
            printf_s("Processor Type = %d\n", nProcessorType);
        if (nExtendedmodel)
            printf_s("Extended model = %d\n", nExtendedmodel);
        if (nExtendedfamily)
            printf_s("Extended family = %d\n", nExtendedfamily);
        if (nBrandIndex)
            printf_s("Brand Index = %d\n", nBrandIndex);
        if (nCLFLUSHcachelinesize)
            printf_s("CLFLUSH cache line size = %d\n",
                     nCLFLUSHcachelinesize);
        if (bMultithreading && (nLogicalProcessors > 0))
           printf_s("Logical Processor Count = %d\n", nLogicalProcessors);
        if (nAPICPhysicalID)
            printf_s("APIC Physical ID = %d\n", nAPICPhysicalID);
        */

        if (nFeatureInfo || bSSE3Instructions ||
            bMONITOR_MWAIT || bCPLQualifiedDebugStore ||
            bVirtualMachineExtensions || bEnhancedIntelSpeedStepTechnology ||
            bThermalMonitor2 || bSupplementalSSE3 || bL1ContextID ||
            bCMPXCHG16B || bxTPRUpdateControl || bPerfDebugCapabilityMSR ||
            bSSE41Extensions || bSSE42Extensions || bPOPCNT ||
            bLAHF_SAHFAvailable || bCmpLegacy || bSVM ||
            bExtApicSpace || bAltMovCr8 ||
            bLZCNT || bSSE4A || bMisalignedSSE ||
            bPREFETCH || bSKINITandDEV || bSYSCALL_SYSRETAvailable ||
            bExecuteDisableBitAvailable || bMMXExtensions || bFFXSR ||
            b1GBSupport || bRDTSCP || b64Available || b3DNowExt || b3DNow ||
            bNestedPaging || bLBRVisualization || bFP128 || bMOVOptimization)
        {

            if (bSSE3Instructions)  // SSE3
                stradd(flags, _countof(flags), "sse3");
            if (bMONITOR_MWAIT)  // MONITOR/MWAIT
                stradd(flags, _countof(flags), "monitor");
            if (bCPLQualifiedDebugStore)  // CPL Qualified Debug Store
                stradd(flags, _countof(flags), "ds_cpl");
            if (bVirtualMachineExtensions)  // Virtual Machine Extensions???
                stradd(flags, _countof(flags), "vmext");
            if (bEnhancedIntelSpeedStepTechnology)  // Enhanced Intel SpeedStep Technology
                stradd(flags, _countof(flags), "est");
            if (bThermalMonitor2)  // Thermal Monitor 2
                stradd(flags, _countof(flags), "tm2");
            if (bSupplementalSSE3) // Supplemental Streaming SIMD Extensions 3?
                stradd(flags, _countof(flags), "supplsse3");
            if (bL1ContextID)  // L1 Context ID ???
                stradd(flags, _countof(flags), "l1ctxid");
            if (bCMPXCHG16B)  // CMPXCHG16B Instruction
                stradd(flags, _countof(flags), "cx16");
            if (bxTPRUpdateControl)  // xTPR Update Control
                stradd(flags, _countof(flags), "xtpr");
            if (bPerfDebugCapabilityMSR)  // Perf\\Debug Capability MSR
                stradd(flags, _countof(flags), "perfdebugmsr");
            if (bSSE41Extensions)  // SSE4.1 Extensions
                stradd(flags, _countof(flags), "sse4_1");
            if (bSSE42Extensions)  // SSE4.2 Extensions
                stradd(flags, _countof(flags), "sse4_2");
            if (bPOPCNT)  // PPOPCNT Instruction
                stradd(flags, _countof(flags), "popcnt");

            i = 0;
            nIds = 1;
            while (i < (sizeof(szFeatures) / sizeof(const char*))) {
                if (nFeatureInfo & nIds) {
                    stradd(flags, _countof(flags), szFeatures[i]);
                }
                nIds <<= 1;
                ++i;
            }

            if (bLAHF_SAHFAvailable)  // LAHF/SAHF in 64-bit mode
                stradd(flags, _countof(flags), "lhaf_lm");
            if (bCmpLegacy)  // Core multi-processing legacy mode
                stradd(flags, _countof(flags), "cmplegacy");
            if (bSVM)  // Secure Virtual Machine
                stradd(flags, _countof(flags), "svm");
            if (bExtApicSpace)  // Extended APIC Register Space
                stradd(flags, _countof(flags), "x2apic");
            if (bAltMovCr8)  // AltMovCr8 ???
                stradd(flags, _countof(flags), "altmovcr8");
            if (bLZCNT)  // LZCNT instruction
                stradd(flags, _countof(flags), "lzcnt");
            if (bSSE4A)  // SSE4A
                stradd(flags, _countof(flags), "sse4a)");
            if (bMisalignedSSE)  // Misaligned SSE mode
                stradd(flags, _countof(flags), "misalignsse");
            if (bPREFETCH)  // PREFETCH and PREFETCHW Instructions
                stradd(flags, _countof(flags), "3dnowprefetch");
            if (bSKINITandDEV)  // SKINIT and DEV support
                stradd(flags, _countof(flags), "skinit");
            if (bSYSCALL_SYSRETAvailable)  // SYSCALL/SYSRET in 64-bit mode
                stradd(flags, _countof(flags), "syscall");
            if (bExecuteDisableBitAvailable)  // Execute Disable Bit
                stradd(flags, _countof(flags), "nx");
            if (bMMXExtensions)  // Extensions to MMX Instructions
                stradd(flags, _countof(flags), "mmxext");
            if (bFFXSR)  // FFXSR
                stradd(flags, _countof(flags), "ffxsr");
            if (b1GBSupport)  // 1GB page support
                stradd(flags, _countof(flags), "pdpe1gb");
            if (bRDTSCP)  // RDTSCP instruction
                stradd(flags, _countof(flags), "rdtscp");
            if (b64Available)  // 64 bit Technology
                stradd(flags, _countof(flags), "lm");
            if (b3DNowExt)  // 3Dnow Ext
                stradd(flags, _countof(flags), "3dnowext");
            if (b3DNow)  // 3Dnow! instructions
                stradd(flags, _countof(flags), "3dnow");
            if (bNestedPaging)  // Nested Paging
                stradd(flags, _countof(flags), "npt");
            if (bLBRVisualization)  // LBR Visualization
                stradd(flags, _countof(flags), "lbrv");
            if (bFP128)  // FP128 optimization???
                stradd(flags, _countof(flags), "fp128");
            if (bMOVOptimization)  // MOVU Optimization???
                stradd(flags, _countof(flags), "movu");
        }
    }

    if (nExIds >= 0x80000004) {
        if (psutil_add_to_dict(py_retdict, "model",
                               Py_BuildValue("s", CPUBrandString)) == 1)
            goto error;

    }
    /*
    if (nExIds >= 0x80000006) {
        printf_s("Cache Line Size = %d\n", nCacheLineSize);
        printf_s("L2 Associativity = %d\n", nL2Associativity);
        printf_s("Cache Size = %dK\n", nCacheSizeK);
    }

    while (1) {
        __cpuidex(CPUInfo, 0x4, i);
        if (!(CPUInfo[0] & 0xf0))
            break;

        if (i == 0) {
            nCores = CPUInfo[0] >> 26;
            // printf_s("\n\nNumber of Cores = %d\n", nCores + 1);
        }

        nCacheType = (CPUInfo[0] & 0x1f);
        nCacheLevel = (CPUInfo[0] & 0xe0) >> 5;
        bSelfInit = (CPUInfo[0] & 0x100) >> 8;
        bFullyAssociative = (CPUInfo[0] & 0x200) >> 9;
        nMaxThread = (CPUInfo[0] & 0x03ffc000) >> 14;
        nSysLineSize = (CPUInfo[1] & 0x0fff);
        nPhysicalLinePartitions = (CPUInfo[1] & 0x03ff000) >> 12;
        nWaysAssociativity = (CPUInfo[1]) >> 22;
        nNumberSets = CPUInfo[2];

        printf_s("\n");

        printf_s("ECX Index %d\n", i);
        switch (nCacheType) {
            case 0:
                printf_s("   Type: Null\n");
                break;
            case 1:
                printf_s("   Type: Data Cache\n");
                break;
            case 2:
                printf_s("   Type: Instruction Cache\n");
                break;
            case 3:
                printf_s("   Type: Unified Cache\n");
                break;
            default:
                 printf_s("   Type: Unknown\n");
        }

        printf_s("   Level = %d\n", nCacheLevel + 1);
        if (bSelfInit) {
            printf_s("   Self Initializing\n");
        }
        else {
            printf_s("   Not Self Initializing\n");
        }
        if (bFullyAssociative) {
            printf_s("   Is Fully Associatve\n");
        }
        else {
            printf_s("   Is Not Fully Associatve\n");
        }
        printf_s("   Max Threads = %d\n",
            nMaxThread+1);
        printf_s("   System Line Size = %d\n",
            nSysLineSize+1);
        printf_s("   Physical Line Partions = %d\n",
            nPhysicalLinePartitions+1);
        printf_s("   Ways of Associativity = %d\n",
            nWaysAssociativity+1);
        printf_s("   Number of Sets = %d\n",
            nNumberSets+1);
        i = i + 1;
    }
    */

    if (psutil_add_to_dict(py_retdict, "flags",
                           Py_BuildValue("s", flags)) == 1)
        goto error;

    return py_retdict;

error:
    Py_DECREF(py_retdict);
    return NULL;
}
