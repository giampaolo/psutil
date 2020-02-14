/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Windows platform-specific module methods for _psutil_windows.
 *
 * List of undocumented Windows NT APIs which are used in here and in
 * other modules:
 * - NtQuerySystemInformation
 * - NtQueryInformationProcess
 * - NtQueryObject
 * - NtSuspendProcess
 * - NtResumeProcess
 */

// Fixes clash between winsock2.h and windows.h
#define WIN32_LEAN_AND_MEAN

#include <Python.h>
#include <windows.h>
#include <Psapi.h>  // memory_info(), memory_maps()
#include <signal.h>
#include <tlhelp32.h>  // threads(), PROCESSENTRY32
#include <wtsapi32.h>  // users()

// Link with Iphlpapi.lib
#pragma comment(lib, "IPHLPAPI.lib")

#include "_psutil_common.h"
#include "arch/windows/security.h"
#include "arch/windows/process_utils.h"
#include "arch/windows/process_info.h"
#include "arch/windows/process_handles.h"
#include "arch/windows/disk.h"
#include "arch/windows/cpu.h"
#include "arch/windows/net.h"
#include "arch/windows/services.h"
#include "arch/windows/socks.h"
#include "arch/windows/wmi.h"

// Raised by Process.wait().
static PyObject *TimeoutExpired;
static PyObject *TimeoutAbandoned;


/*
 * Return the number of logical, active CPUs. Return 0 if undetermined.
 * See discussion at: https://bugs.python.org/issue33166#msg314631
 */
unsigned int
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
 * Return a Python float representing the system uptime expressed in seconds
 * since the epoch.
 */
static PyObject *
psutil_boot_time(PyObject *self, PyObject *args) {
    ULONGLONG upTime;
    FILETIME fileTime;

    GetSystemTimeAsFileTime(&fileTime);
    // Number of milliseconds that have elapsed since the system was started.
    upTime = GetTickCount64() / 1000ull;
    return Py_BuildValue("d", psutil_FiletimeToUnixTime(fileTime) - upTime);
}


/*
 * Return 1 if PID exists in the current process list, else 0.
 */
static PyObject *
psutil_pid_exists(PyObject *self, PyObject *args) {
    DWORD pid;
    int status;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    status = psutil_pid_is_running(pid);
    if (-1 == status)
        return NULL; // exception raised in psutil_pid_is_running()
    return PyBool_FromLong(status);
}


/*
 * Return a Python list of all the PIDs running on the system.
 */
static PyObject *
psutil_pids(PyObject *self, PyObject *args) {
    DWORD *proclist = NULL;
    DWORD numberOfReturnedPIDs;
    DWORD i;
    PyObject *py_pid = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;
    proclist = psutil_get_pids(&numberOfReturnedPIDs);
    if (proclist == NULL)
        goto error;

    for (i = 0; i < numberOfReturnedPIDs; i++) {
        py_pid = PyLong_FromPid(proclist[i]);
        if (!py_pid)
            goto error;
        if (PyList_Append(py_retlist, py_pid))
            goto error;
        Py_CLEAR(py_pid);
    }

    // free C array allocated for PIDs
    free(proclist);
    return py_retlist;

error:
    Py_XDECREF(py_pid);
    Py_DECREF(py_retlist);
    if (proclist != NULL)
        free(proclist);
    return NULL;
}


/*
 * Kill a process given its PID.
 */
static PyObject *
psutil_proc_kill(PyObject *self, PyObject *args) {
    HANDLE hProcess;
    DWORD pid;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (pid == 0)
        return AccessDenied("automatically set for PID 0");

    hProcess = OpenProcess(PROCESS_TERMINATE, FALSE, pid);
    if (hProcess == NULL) {
        if (GetLastError() == ERROR_INVALID_PARAMETER) {
            // see https://github.com/giampaolo/psutil/issues/24
            psutil_debug("OpenProcess -> ERROR_INVALID_PARAMETER turned "
                         "into NoSuchProcess");
            NoSuchProcess("OpenProcess");
        }
        else {
            PyErr_SetFromWindowsErr(0);
        }
        return NULL;
    }

    if (! TerminateProcess(hProcess, SIGTERM)) {
        // ERROR_ACCESS_DENIED may happen if the process already died. See:
        // https://github.com/giampaolo/psutil/issues/1099
        if (GetLastError() != ERROR_ACCESS_DENIED) {
            PyErr_SetFromOSErrnoWithSyscall("TerminateProcess");
            return NULL;
        }
    }

    CloseHandle(hProcess);
    Py_RETURN_NONE;
}


/*
 * Wait for process to terminate and return its exit code.
 */
static PyObject *
psutil_proc_wait(PyObject *self, PyObject *args) {
    HANDLE hProcess;
    DWORD ExitCode;
    DWORD retVal;
    DWORD pid;
    long timeout;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID "l", &pid, &timeout))
        return NULL;
    if (pid == 0)
        return AccessDenied("automatically set for PID 0");

    hProcess = OpenProcess(SYNCHRONIZE | PROCESS_QUERY_INFORMATION,
                           FALSE, pid);
    if (hProcess == NULL) {
        if (GetLastError() == ERROR_INVALID_PARAMETER) {
            // no such process; we do not want to raise NSP but
            // return None instead.
            Py_RETURN_NONE;
        }
        else {
            PyErr_SetFromWindowsErr(0);
            return NULL;
        }
    }

    // wait until the process has terminated
    Py_BEGIN_ALLOW_THREADS
    retVal = WaitForSingleObject(hProcess, timeout);
    Py_END_ALLOW_THREADS

    // handle return code
    if (retVal == WAIT_FAILED) {
        PyErr_SetFromOSErrnoWithSyscall("WaitForSingleObject");
        CloseHandle(hProcess);
        return NULL;
    }
    if (retVal == WAIT_TIMEOUT) {
        PyErr_SetString(TimeoutExpired,
                        "WaitForSingleObject() returned WAIT_TIMEOUT");
        CloseHandle(hProcess);
        return NULL;
    }
    if (retVal == WAIT_ABANDONED) {
        psutil_debug("WaitForSingleObject() -> WAIT_ABANDONED");
        PyErr_SetString(TimeoutAbandoned,
                        "WaitForSingleObject() returned WAIT_ABANDONED");
        CloseHandle(hProcess);
        return NULL;
    }

    // WaitForSingleObject() returned WAIT_OBJECT_0. It means the
    // process is gone so we can get its process exit code. The PID
    // may still stick around though but we'll handle that from Python.
    if (GetExitCodeProcess(hProcess, &ExitCode) == 0) {
        PyErr_SetFromOSErrnoWithSyscall("GetExitCodeProcess");
        CloseHandle(hProcess);
        return NULL;
    }

    CloseHandle(hProcess);

#if PY_MAJOR_VERSION >= 3
    return PyLong_FromLong((long) ExitCode);
#else
    return PyInt_FromLong((long) ExitCode);
#endif
}


/*
 * Return a Python tuple (user_time, kernel_time)
 */
static PyObject *
psutil_proc_times(PyObject *self, PyObject *args) {
    DWORD       pid;
    HANDLE      hProcess;
    FILETIME    ftCreate, ftExit, ftKernel, ftUser;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    hProcess = psutil_handle_from_pid(pid, PROCESS_QUERY_LIMITED_INFORMATION);

    if (hProcess == NULL)
        return NULL;
    if (! GetProcessTimes(hProcess, &ftCreate, &ftExit, &ftKernel, &ftUser)) {
        if (GetLastError() == ERROR_ACCESS_DENIED) {
            // usually means the process has died so we throw a NoSuchProcess
            // here
            NoSuchProcess("GetProcessTimes");
        }
        else {
            PyErr_SetFromWindowsErr(0);
        }
        CloseHandle(hProcess);
        return NULL;
    }

    CloseHandle(hProcess);

    /*
     * User and kernel times are represented as a FILETIME structure
     * which contains a 64-bit value representing the number of
     * 100-nanosecond intervals since January 1, 1601 (UTC):
     * http://msdn.microsoft.com/en-us/library/ms724284(VS.85).aspx
     * To convert it into a float representing the seconds that the
     * process has executed in user/kernel mode I borrowed the code
     * below from Python's Modules/posixmodule.c
     */
    return Py_BuildValue(
       "(ddd)",
       (double)(ftUser.dwHighDateTime * HI_T + \
                ftUser.dwLowDateTime * LO_T),
       (double)(ftKernel.dwHighDateTime * HI_T + \
                ftKernel.dwLowDateTime * LO_T),
       psutil_FiletimeToUnixTime(ftCreate)
   );
}


/*
 * Return process cmdline as a Python list of cmdline arguments.
 */
static PyObject *
psutil_proc_cmdline(PyObject *self, PyObject *args, PyObject *kwdict) {
    DWORD pid;
    int pid_return;
    int use_peb;
    PyObject *py_usepeb = Py_True;
    static char *keywords[] = {"pid", "use_peb", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwdict, _Py_PARSE_PID "|O",
                                     keywords, &pid, &py_usepeb))
    {
        return NULL;
    }
    if ((pid == 0) || (pid == 4))
        return Py_BuildValue("[]");

    pid_return = psutil_pid_is_running(pid);
    if (pid_return == 0)
        return NoSuchProcess("psutil_pid_is_running");
    if (pid_return == -1)
        return NULL;

    use_peb = (py_usepeb == Py_True) ? 1 : 0;
    return psutil_get_cmdline(pid, use_peb);
}


/*
 * Return process cmdline as a Python list of cmdline arguments.
 */
static PyObject *
psutil_proc_environ(PyObject *self, PyObject *args) {
    DWORD pid;
    int pid_return;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if ((pid == 0) || (pid == 4))
        return Py_BuildValue("s", "");

    pid_return = psutil_pid_is_running(pid);
    if (pid_return == 0)
        return NoSuchProcess("psutil_pid_is_running");
    if (pid_return == -1)
        return NULL;

    return psutil_get_environ(pid);
}


/*
 * Return process executable path. Works for all processes regardless of
 * privilege. NtQuerySystemInformation has some sort of internal cache,
 * since it succeeds even when a process is gone (but not if a PID never
 * existed).
 */
static PyObject *
psutil_proc_exe(PyObject *self, PyObject *args) {
    DWORD pid;
    NTSTATUS status;
    PVOID buffer;
    ULONG bufferSize = 0x100;
    SYSTEM_PROCESS_ID_INFORMATION processIdInfo;
    PyObject *py_exe;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    if (pid == 0)
        return AccessDenied("forced for PID 0");

    buffer = MALLOC_ZERO(bufferSize);
    if (! buffer)
        return PyErr_NoMemory();
    processIdInfo.ProcessId = (HANDLE)(ULONG_PTR)pid;
    processIdInfo.ImageName.Length = 0;
    processIdInfo.ImageName.MaximumLength = (USHORT)bufferSize;
    processIdInfo.ImageName.Buffer = buffer;

    status = NtQuerySystemInformation(
        SystemProcessIdInformation,
        &processIdInfo,
        sizeof(SYSTEM_PROCESS_ID_INFORMATION),
        NULL);

    if (status == STATUS_INFO_LENGTH_MISMATCH) {
        // Required length is stored in MaximumLength.
        FREE(buffer);
        buffer = MALLOC_ZERO(processIdInfo.ImageName.MaximumLength);
        if (! buffer)
            return PyErr_NoMemory();
        processIdInfo.ImageName.Buffer = buffer;

        status = NtQuerySystemInformation(
            SystemProcessIdInformation,
            &processIdInfo,
            sizeof(SYSTEM_PROCESS_ID_INFORMATION),
            NULL);
    }

    if (! NT_SUCCESS(status)) {
        FREE(buffer);
        if (psutil_pid_is_running(pid) == 0)
            NoSuchProcess("NtQuerySystemInformation");
        else
            psutil_SetFromNTStatusErr(status, "NtQuerySystemInformation");
        return NULL;
    }

    if (processIdInfo.ImageName.Buffer == NULL) {
        // Happens for PID 4.
        py_exe = Py_BuildValue("s", "");
    }
    else {
        py_exe = PyUnicode_FromWideChar(processIdInfo.ImageName.Buffer,
                                        processIdInfo.ImageName.Length / 2);
    }
    FREE(buffer);
    return py_exe;
}


/*
 * Return process memory information as a Python tuple.
 */
static PyObject *
psutil_proc_memory_info(PyObject *self, PyObject *args) {
    HANDLE hProcess;
    DWORD pid;
    PROCESS_MEMORY_COUNTERS_EX cnt;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    hProcess = psutil_handle_from_pid(pid, PROCESS_QUERY_LIMITED_INFORMATION);
    if (NULL == hProcess)
        return NULL;

    if (! GetProcessMemoryInfo(hProcess, (PPROCESS_MEMORY_COUNTERS)&cnt,
                               sizeof(cnt))) {
        PyErr_SetFromWindowsErr(0);
        CloseHandle(hProcess);
        return NULL;
    }
    CloseHandle(hProcess);

    // PROCESS_MEMORY_COUNTERS values are defined as SIZE_T which on 64bits
    // is an (unsigned long long) and on 32bits is an (unsigned int).
    // "_WIN64" is defined if we're running a 64bit Python interpreter not
    // exclusively if the *system* is 64bit.
#if defined(_WIN64)
    return Py_BuildValue(
        "(kKKKKKKKKK)",
        cnt.PageFaultCount,  // unsigned long
        (unsigned long long)cnt.PeakWorkingSetSize,
        (unsigned long long)cnt.WorkingSetSize,
        (unsigned long long)cnt.QuotaPeakPagedPoolUsage,
        (unsigned long long)cnt.QuotaPagedPoolUsage,
        (unsigned long long)cnt.QuotaPeakNonPagedPoolUsage,
        (unsigned long long)cnt.QuotaNonPagedPoolUsage,
        (unsigned long long)cnt.PagefileUsage,
        (unsigned long long)cnt.PeakPagefileUsage,
        (unsigned long long)cnt.PrivateUsage);
#else
    return Py_BuildValue(
        "(kIIIIIIIII)",
        cnt.PageFaultCount,    // unsigned long
        (unsigned int)cnt.PeakWorkingSetSize,
        (unsigned int)cnt.WorkingSetSize,
        (unsigned int)cnt.QuotaPeakPagedPoolUsage,
        (unsigned int)cnt.QuotaPagedPoolUsage,
        (unsigned int)cnt.QuotaPeakNonPagedPoolUsage,
        (unsigned int)cnt.QuotaNonPagedPoolUsage,
        (unsigned int)cnt.PagefileUsage,
        (unsigned int)cnt.PeakPagefileUsage,
        (unsigned int)cnt.PrivateUsage);
#endif
}


static int
psutil_GetProcWsetInformation(
        DWORD pid,
        HANDLE hProcess,
        PMEMORY_WORKING_SET_INFORMATION *wSetInfo)
{
    NTSTATUS status;
    PVOID buffer;
    SIZE_T bufferSize;

    bufferSize = 0x8000;
    buffer = MALLOC_ZERO(bufferSize);
    if (! buffer) {
        PyErr_NoMemory();
        return 1;
    }

    while ((status = NtQueryVirtualMemory(
            hProcess,
            NULL,
            MemoryWorkingSetInformation,
            buffer,
            bufferSize,
            NULL)) == STATUS_INFO_LENGTH_MISMATCH)
    {
        FREE(buffer);
        bufferSize *= 2;
        // Fail if we're resizing the buffer to something very large.
        if (bufferSize > 256 * 1024 * 1024) {
            PyErr_SetString(PyExc_RuntimeError,
                            "NtQueryVirtualMemory bufsize is too large");
            return 1;
        }
        buffer = MALLOC_ZERO(bufferSize);
        if (! buffer) {
            PyErr_NoMemory();
            return 1;
        }
    }

    if (!NT_SUCCESS(status)) {
        if (status == STATUS_ACCESS_DENIED) {
            AccessDenied("NtQueryVirtualMemory");
        }
        else if (psutil_pid_is_running(pid) == 0) {
            NoSuchProcess("psutil_pid_is_running");
        }
        else {
            PyErr_Clear();
            psutil_SetFromNTStatusErr(
                status, "NtQueryVirtualMemory(MemoryWorkingSetInformation)");
        }
        HeapFree(GetProcessHeap(), 0, buffer);
        return 1;
    }

    *wSetInfo = (PMEMORY_WORKING_SET_INFORMATION)buffer;
    return 0;
}


/*
 * Returns the USS of the process.
 * Reference:
 * https://dxr.mozilla.org/mozilla-central/source/xpcom/base/
 *     nsMemoryReporterManager.cpp
 */
static PyObject *
psutil_proc_memory_uss(PyObject *self, PyObject *args) {
    DWORD pid;
    HANDLE hProcess;
    PSUTIL_PROCESS_WS_COUNTERS wsCounters;
    PMEMORY_WORKING_SET_INFORMATION wsInfo;
    ULONG_PTR i;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    hProcess = psutil_handle_from_pid(pid, PROCESS_QUERY_INFORMATION);
    if (hProcess == NULL)
        return NULL;

    if (psutil_GetProcWsetInformation(pid, hProcess, &wsInfo) != 0) {
        CloseHandle(hProcess);
        return NULL;
    }
    memset(&wsCounters, 0, sizeof(PSUTIL_PROCESS_WS_COUNTERS));

    for (i = 0; i < wsInfo->NumberOfEntries; i++) {
        // This is what ProcessHacker does.
        /*
        wsCounters.NumberOfPages++;
        if (wsInfo->WorkingSetInfo[i].ShareCount > 1)
            wsCounters.NumberOfSharedPages++;
        if (wsInfo->WorkingSetInfo[i].ShareCount == 0)
            wsCounters.NumberOfPrivatePages++;
        if (wsInfo->WorkingSetInfo[i].Shared)
            wsCounters.NumberOfShareablePages++;
        */

        // This is what we do: count shared pages that only one process
        // is using as private (USS).
        if (!wsInfo->WorkingSetInfo[i].Shared ||
                wsInfo->WorkingSetInfo[i].ShareCount <= 1) {
            wsCounters.NumberOfPrivatePages++;
        }
    }

    HeapFree(GetProcessHeap(), 0, wsInfo);
    CloseHandle(hProcess);

    return Py_BuildValue("I", wsCounters.NumberOfPrivatePages);
}


/*
 * Return a Python integer indicating the total amount of physical memory
 * in bytes.
 */
static PyObject *
psutil_virtual_mem(PyObject *self, PyObject *args) {
    MEMORYSTATUSEX memInfo;
    memInfo.dwLength = sizeof(MEMORYSTATUSEX);

    if (! GlobalMemoryStatusEx(&memInfo)) {
        PyErr_SetFromWindowsErr(0);
        return NULL;
    }
    return Py_BuildValue("(LLLLLL)",
                         memInfo.ullTotalPhys,      // total
                         memInfo.ullAvailPhys,      // avail
                         memInfo.ullTotalPageFile,  // total page file
                         memInfo.ullAvailPageFile,  // avail page file
                         memInfo.ullTotalVirtual,   // total virtual
                         memInfo.ullAvailVirtual);  // avail virtual
}


/*
 * Return process current working directory as a Python string.
 */
static PyObject *
psutil_proc_cwd(PyObject *self, PyObject *args) {
    DWORD pid;
    int pid_return;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    pid_return = psutil_pid_is_running(pid);
    if (pid_return == 0)
        return NoSuchProcess("psutil_pid_is_running");
    if (pid_return == -1)
        return NULL;

    return psutil_get_cwd(pid);
}


/*
 * Resume or suspends a process
 */
static PyObject *
psutil_proc_suspend_or_resume(PyObject *self, PyObject *args) {
    DWORD pid;
    NTSTATUS status;
    HANDLE hProcess;
    PyObject* suspend;

        if (! PyArg_ParseTuple(args, _Py_PARSE_PID "O", &pid, &suspend))
            return NULL;

    hProcess = psutil_handle_from_pid(pid, PROCESS_SUSPEND_RESUME);
    if (hProcess == NULL)
        return NULL;

    if (PyObject_IsTrue(suspend))
        status = NtSuspendProcess(hProcess);
    else
        status = NtResumeProcess(hProcess);

    if (! NT_SUCCESS(status)) {
        CloseHandle(hProcess);
        return psutil_SetFromNTStatusErr(status, "NtSuspend|ResumeProcess");
    }

    CloseHandle(hProcess);
    Py_RETURN_NONE;
}


static PyObject *
psutil_proc_threads(PyObject *self, PyObject *args) {
    HANDLE hThread = NULL;
    THREADENTRY32 te32 = {0};
    DWORD pid;
    int pid_return;
    int rc;
    FILETIME ftDummy, ftKernel, ftUser;
    HANDLE hThreadSnap = NULL;
    PyObject *py_tuple = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;
    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;
    if (pid == 0) {
        // raise AD instead of returning 0 as procexp is able to
        // retrieve useful information somehow
        AccessDenied("automatically set for PID 0");
        goto error;
    }

    pid_return = psutil_pid_is_running(pid);
    if (pid_return == 0) {
        NoSuchProcess("psutil_pid_is_running");
        goto error;
    }
    if (pid_return == -1)
        goto error;

    hThreadSnap = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    if (hThreadSnap == INVALID_HANDLE_VALUE) {
        PyErr_SetFromOSErrnoWithSyscall("CreateToolhelp32Snapshot");
        goto error;
    }

    // Fill in the size of the structure before using it
    te32.dwSize = sizeof(THREADENTRY32);

    if (! Thread32First(hThreadSnap, &te32)) {
        PyErr_SetFromOSErrnoWithSyscall("Thread32First");
        goto error;
    }

    // Walk the thread snapshot to find all threads of the process.
    // If the thread belongs to the process, increase the counter.
    do {
        if (te32.th32OwnerProcessID == pid) {
            py_tuple = NULL;
            hThread = NULL;
            hThread = OpenThread(THREAD_QUERY_INFORMATION,
                                 FALSE, te32.th32ThreadID);
            if (hThread == NULL) {
                // thread has disappeared on us
                continue;
            }

            rc = GetThreadTimes(hThread, &ftDummy, &ftDummy, &ftKernel,
                                &ftUser);
            if (rc == 0) {
                PyErr_SetFromOSErrnoWithSyscall("GetThreadTimes");
                goto error;
            }

            /*
             * User and kernel times are represented as a FILETIME structure
             * which contains a 64-bit value representing the number of
             * 100-nanosecond intervals since January 1, 1601 (UTC):
             * http://msdn.microsoft.com/en-us/library/ms724284(VS.85).aspx
             * To convert it into a float representing the seconds that the
             * process has executed in user/kernel mode I borrowed the code
             * below from Python's Modules/posixmodule.c
             */
            py_tuple = Py_BuildValue(
                "kdd",
                te32.th32ThreadID,
                (double)(ftUser.dwHighDateTime * HI_T + \
                         ftUser.dwLowDateTime * LO_T),
                (double)(ftKernel.dwHighDateTime * HI_T + \
                         ftKernel.dwLowDateTime * LO_T));
            if (!py_tuple)
                goto error;
            if (PyList_Append(py_retlist, py_tuple))
                goto error;
            Py_CLEAR(py_tuple);

            CloseHandle(hThread);
        }
    } while (Thread32Next(hThreadSnap, &te32));

    CloseHandle(hThreadSnap);
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    if (hThread != NULL)
        CloseHandle(hThread);
    if (hThreadSnap != NULL)
        CloseHandle(hThreadSnap);
    return NULL;
}


static PyObject *
psutil_proc_open_files(PyObject *self, PyObject *args) {
    DWORD pid;
    HANDLE processHandle;
    DWORD access = PROCESS_DUP_HANDLE | PROCESS_QUERY_INFORMATION;
    PyObject *py_retlist;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    processHandle = psutil_handle_from_pid(pid, access);
    if (processHandle == NULL)
        return NULL;

    py_retlist = psutil_get_open_files(pid, processHandle);
    CloseHandle(processHandle);
    return py_retlist;
}


/*
 * Return process username as a "DOMAIN//USERNAME" string.
 */
static PyObject *
psutil_proc_username(PyObject *self, PyObject *args) {
    DWORD pid;
    HANDLE processHandle = NULL;
    HANDLE tokenHandle = NULL;
    PTOKEN_USER user = NULL;
    ULONG bufferSize;
    WCHAR *name = NULL;
    WCHAR *domainName = NULL;
    ULONG nameSize;
    ULONG domainNameSize;
    SID_NAME_USE nameUse;
    PyObject *py_username = NULL;
    PyObject *py_domain = NULL;
    PyObject *py_tuple = NULL;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    processHandle = psutil_handle_from_pid(
        pid, PROCESS_QUERY_LIMITED_INFORMATION);
    if (processHandle == NULL)
        return NULL;

    if (!OpenProcessToken(processHandle, TOKEN_QUERY, &tokenHandle)) {
        PyErr_SetFromOSErrnoWithSyscall("OpenProcessToken");
        goto error;
    }

    CloseHandle(processHandle);
    processHandle = NULL;

    // Get the user SID.
    bufferSize = 0x100;
    while (1) {
        user = malloc(bufferSize);
        if (user == NULL) {
            PyErr_NoMemory();
            goto error;
        }
        if (!GetTokenInformation(tokenHandle, TokenUser, user, bufferSize,
                                 &bufferSize))
        {
            if (GetLastError() == ERROR_INSUFFICIENT_BUFFER) {
                free(user);
                continue;
            }
            else {
                PyErr_SetFromOSErrnoWithSyscall("GetTokenInformation");
                goto error;
            }
        }
        break;
    }

    CloseHandle(tokenHandle);
    tokenHandle = NULL;

    // resolve the SID to a name
    nameSize = 0x100;
    domainNameSize = 0x100;
    while (1) {
        name = malloc(nameSize * sizeof(WCHAR));
        if (name == NULL) {
            PyErr_NoMemory();
            goto error;
        }
        domainName = malloc(domainNameSize * sizeof(WCHAR));
        if (domainName == NULL) {
            PyErr_NoMemory();
            goto error;
        }
        if (!LookupAccountSidW(NULL, user->User.Sid, name, &nameSize,
                               domainName, &domainNameSize, &nameUse))
        {
            if (GetLastError() == ERROR_INSUFFICIENT_BUFFER) {
                free(name);
                free(domainName);
                continue;
            }
            else {
                PyErr_SetFromOSErrnoWithSyscall("LookupAccountSidW");
                goto error;
            }
        }
        break;
    }

    py_domain = PyUnicode_FromWideChar(domainName, wcslen(domainName));
    if (! py_domain)
        goto error;
    py_username = PyUnicode_FromWideChar(name, wcslen(name));
    if (! py_username)
        goto error;
    py_tuple = Py_BuildValue("OO", py_domain, py_username);
    if (! py_tuple)
        goto error;
    Py_DECREF(py_domain);
    Py_DECREF(py_username);

    free(name);
    free(domainName);
    free(user);

    return py_tuple;

error:
    if (processHandle != NULL)
        CloseHandle(processHandle);
    if (tokenHandle != NULL)
        CloseHandle(tokenHandle);
    if (name != NULL)
        free(name);
    if (domainName != NULL)
        free(domainName);
    if (user != NULL)
        free(user);
    Py_XDECREF(py_domain);
    Py_XDECREF(py_username);
    Py_XDECREF(py_tuple);
    return NULL;
}


/*
 * Get process priority as a Python integer.
 */
static PyObject *
psutil_proc_priority_get(PyObject *self, PyObject *args) {
    DWORD pid;
    DWORD priority;
    HANDLE hProcess;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    hProcess = psutil_handle_from_pid(pid, PROCESS_QUERY_LIMITED_INFORMATION);
    if (hProcess == NULL)
        return NULL;

    priority = GetPriorityClass(hProcess);
    if (priority == 0) {
        PyErr_SetFromWindowsErr(0);
        CloseHandle(hProcess);
        return NULL;
    }
    CloseHandle(hProcess);
    return Py_BuildValue("i", priority);
}


/*
 * Set process priority.
 */
static PyObject *
psutil_proc_priority_set(PyObject *self, PyObject *args) {
    DWORD pid;
    int priority;
    int retval;
    HANDLE hProcess;
    DWORD access = PROCESS_QUERY_INFORMATION | PROCESS_SET_INFORMATION;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID "i", &pid, &priority))
        return NULL;
    hProcess = psutil_handle_from_pid(pid, access);
    if (hProcess == NULL)
        return NULL;

    retval = SetPriorityClass(hProcess, priority);
    if (retval == 0) {
        PyErr_SetFromWindowsErr(0);
        CloseHandle(hProcess);
        return NULL;
    }

    CloseHandle(hProcess);
    Py_RETURN_NONE;
}


/*
 * Get process IO priority as a Python integer.
 */
static PyObject *
psutil_proc_io_priority_get(PyObject *self, PyObject *args) {
    DWORD pid;
    HANDLE hProcess;
    DWORD IoPriority;
    NTSTATUS status;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    hProcess = psutil_handle_from_pid(pid, PROCESS_QUERY_LIMITED_INFORMATION);
    if (hProcess == NULL)
        return NULL;

    status = NtQueryInformationProcess(
        hProcess,
        ProcessIoPriority,
        &IoPriority,
        sizeof(DWORD),
        NULL
    );

    CloseHandle(hProcess);
    if (! NT_SUCCESS(status))
        return psutil_SetFromNTStatusErr(status, "NtQueryInformationProcess");
    return Py_BuildValue("i", IoPriority);
}


/*
 * Set process IO priority.
 */
static PyObject *
psutil_proc_io_priority_set(PyObject *self, PyObject *args) {
    DWORD pid;
    DWORD prio;
    HANDLE hProcess;
    NTSTATUS status;
    DWORD access = PROCESS_QUERY_INFORMATION | PROCESS_SET_INFORMATION;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID "i", &pid, &prio))
        return NULL;

    hProcess = psutil_handle_from_pid(pid, access);
    if (hProcess == NULL)
        return NULL;

    status = NtSetInformationProcess(
        hProcess,
        ProcessIoPriority,
        (PVOID)&prio,
        sizeof(DWORD)
    );

    CloseHandle(hProcess);
    if (! NT_SUCCESS(status))
        return psutil_SetFromNTStatusErr(status, "NtSetInformationProcess");
    Py_RETURN_NONE;
}


/*
 * Return a Python tuple referencing process I/O counters.
 */
static PyObject *
psutil_proc_io_counters(PyObject *self, PyObject *args) {
    DWORD pid;
    HANDLE hProcess;
    IO_COUNTERS IoCounters;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    hProcess = psutil_handle_from_pid(pid, PROCESS_QUERY_LIMITED_INFORMATION);
    if (NULL == hProcess)
        return NULL;

    if (! GetProcessIoCounters(hProcess, &IoCounters)) {
        PyErr_SetFromWindowsErr(0);
        CloseHandle(hProcess);
        return NULL;
    }

    CloseHandle(hProcess);
    return Py_BuildValue("(KKKKKK)",
                         IoCounters.ReadOperationCount,
                         IoCounters.WriteOperationCount,
                         IoCounters.ReadTransferCount,
                         IoCounters.WriteTransferCount,
                         IoCounters.OtherOperationCount,
                         IoCounters.OtherTransferCount);
}


/*
 * Return process CPU affinity as a bitmask
 */
static PyObject *
psutil_proc_cpu_affinity_get(PyObject *self, PyObject *args) {
    DWORD pid;
    HANDLE hProcess;
    DWORD_PTR proc_mask;
    DWORD_PTR system_mask;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    hProcess = psutil_handle_from_pid(pid, PROCESS_QUERY_LIMITED_INFORMATION);
    if (hProcess == NULL) {
        return NULL;
    }
    if (GetProcessAffinityMask(hProcess, &proc_mask, &system_mask) == 0) {
        PyErr_SetFromWindowsErr(0);
        CloseHandle(hProcess);
        return NULL;
    }

    CloseHandle(hProcess);
#ifdef _WIN64
    return Py_BuildValue("K", (unsigned long long)proc_mask);
#else
    return Py_BuildValue("k", (unsigned long)proc_mask);
#endif
}


/*
 * Set process CPU affinity
 */
static PyObject *
psutil_proc_cpu_affinity_set(PyObject *self, PyObject *args) {
    DWORD pid;
    HANDLE hProcess;
    DWORD access = PROCESS_QUERY_INFORMATION | PROCESS_SET_INFORMATION;
    DWORD_PTR mask;

#ifdef _WIN64
    if (! PyArg_ParseTuple(args, _Py_PARSE_PID "K", &pid, &mask))
#else
    if (! PyArg_ParseTuple(args, _Py_PARSE_PID "k", &pid, &mask))
#endif
    {
        return NULL;
    }
    hProcess = psutil_handle_from_pid(pid, access);
    if (hProcess == NULL)
        return NULL;

    if (SetProcessAffinityMask(hProcess, mask) == 0) {
        PyErr_SetFromWindowsErr(0);
        CloseHandle(hProcess);
        return NULL;
    }

    CloseHandle(hProcess);
    Py_RETURN_NONE;
}


/*
 * Return True if all process threads are in waiting/suspended state.
 */
static PyObject *
psutil_proc_is_suspended(PyObject *self, PyObject *args) {
    DWORD pid;
    ULONG i;
    PSYSTEM_PROCESS_INFORMATION process;
    PVOID buffer;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (! psutil_get_proc_info(pid, &process, &buffer))
        return NULL;
    for (i = 0; i < process->NumberOfThreads; i++) {
        if (process->Threads[i].ThreadState != Waiting ||
                process->Threads[i].WaitReason != Suspended)
        {
            free(buffer);
            Py_RETURN_FALSE;
        }
    }
    free(buffer);
    Py_RETURN_TRUE;
}


/*
 * Return a Python dict of tuples for disk I/O information
 */
static PyObject *
psutil_users(PyObject *self, PyObject *args) {
    HANDLE hServer = WTS_CURRENT_SERVER_HANDLE;
    WCHAR *buffer_user = NULL;
    LPTSTR buffer_addr = NULL;
    PWTS_SESSION_INFO sessions = NULL;
    DWORD count;
    DWORD i;
    DWORD sessionId;
    DWORD bytes;
    PWTS_CLIENT_ADDRESS address;
    char address_str[50];
    WINSTATION_INFO station_info;
    ULONG returnLen;
    PyObject *py_tuple = NULL;
    PyObject *py_address = NULL;
    PyObject *py_username = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;

    if (WTSEnumerateSessions(hServer, 0, 1, &sessions, &count) == 0) {
        PyErr_SetFromOSErrnoWithSyscall("WTSEnumerateSessions");
        goto error;
    }

    for (i = 0; i < count; i++) {
        py_address = NULL;
        py_tuple = NULL;
        sessionId = sessions[i].SessionId;
        if (buffer_user != NULL)
            WTSFreeMemory(buffer_user);
        if (buffer_addr != NULL)
            WTSFreeMemory(buffer_addr);

        buffer_user = NULL;
        buffer_addr = NULL;

        // username
        bytes = 0;
        if (WTSQuerySessionInformationW(hServer, sessionId, WTSUserName,
                                        &buffer_user, &bytes) == 0) {
            PyErr_SetFromOSErrnoWithSyscall("WTSQuerySessionInformationW");
            goto error;
        }
        if (bytes <= 2)
            continue;

        // address
        bytes = 0;
        if (WTSQuerySessionInformation(hServer, sessionId, WTSClientAddress,
                                       &buffer_addr, &bytes) == 0) {
            PyErr_SetFromOSErrnoWithSyscall("WTSQuerySessionInformation");
            goto error;
        }

        address = (PWTS_CLIENT_ADDRESS)buffer_addr;
        if (address->AddressFamily == 0) {  // AF_INET
            sprintf_s(address_str,
                      _countof(address_str),
                      "%u.%u.%u.%u",
                      address->Address[0],
                      address->Address[1],
                      address->Address[2],
                      address->Address[3]);
            py_address = Py_BuildValue("s", address_str);
            if (!py_address)
                goto error;
        }
        else {
            py_address = Py_None;
        }

        // login time
        if (! WinStationQueryInformationW(
                hServer,
                sessionId,
                WinStationInformation,
                &station_info,
                sizeof(station_info),
                &returnLen))
        {
            PyErr_SetFromOSErrnoWithSyscall("WinStationQueryInformationW");
            goto error;
        }

        py_username = PyUnicode_FromWideChar(buffer_user, wcslen(buffer_user));
        if (py_username == NULL)
            goto error;
        py_tuple = Py_BuildValue(
            "OOd",
            py_username,
            py_address,
            psutil_FiletimeToUnixTime(station_info.ConnectTime)
        );
        if (!py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_CLEAR(py_username);
        Py_CLEAR(py_address);
        Py_CLEAR(py_tuple);
    }

    WTSFreeMemory(sessions);
    WTSFreeMemory(buffer_user);
    WTSFreeMemory(buffer_addr);
    return py_retlist;

error:
    Py_XDECREF(py_username);
    Py_XDECREF(py_tuple);
    Py_XDECREF(py_address);
    Py_DECREF(py_retlist);

    if (sessions != NULL)
        WTSFreeMemory(sessions);
    if (buffer_user != NULL)
        WTSFreeMemory(buffer_user);
    if (buffer_addr != NULL)
        WTSFreeMemory(buffer_addr);
    return NULL;
}


/*
 * Return the number of handles opened by process.
 */
static PyObject *
psutil_proc_num_handles(PyObject *self, PyObject *args) {
    DWORD pid;
    HANDLE hProcess;
    DWORD handleCount;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    hProcess = psutil_handle_from_pid(pid, PROCESS_QUERY_LIMITED_INFORMATION);
    if (NULL == hProcess)
        return NULL;
    if (! GetProcessHandleCount(hProcess, &handleCount)) {
        PyErr_SetFromWindowsErr(0);
        CloseHandle(hProcess);
        return NULL;
    }
    CloseHandle(hProcess);
    return Py_BuildValue("k", handleCount);
}


static char *get_region_protection_string(ULONG protection) {
    switch (protection & 0xff) {
        case PAGE_NOACCESS:
            return "";
        case PAGE_READONLY:
            return "r";
        case PAGE_READWRITE:
            return "rw";
        case PAGE_WRITECOPY:
            return "wc";
        case PAGE_EXECUTE:
            return "x";
        case PAGE_EXECUTE_READ:
            return "xr";
        case PAGE_EXECUTE_READWRITE:
            return "xrw";
        case PAGE_EXECUTE_WRITECOPY:
            return "xwc";
        default:
            return "?";
    }
}


/*
 * Return a list of process's memory mappings.
 */
static PyObject *
psutil_proc_memory_maps(PyObject *self, PyObject *args) {
    MEMORY_BASIC_INFORMATION basicInfo;
    DWORD pid;
    HANDLE hProcess = NULL;
    PVOID baseAddress;
    WCHAR mappedFileName[MAX_PATH];
    LPVOID maxAddr;
    // required by GetMappedFileNameW
    DWORD access = PROCESS_QUERY_INFORMATION | PROCESS_VM_READ;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;
    PyObject *py_str = NULL;

    if (py_retlist == NULL)
        return NULL;
    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;
    hProcess = psutil_handle_from_pid(pid, access);
    if (NULL == hProcess)
        goto error;

    maxAddr = PSUTIL_SYSTEM_INFO.lpMaximumApplicationAddress;
    baseAddress = NULL;

    while (VirtualQueryEx(hProcess, baseAddress, &basicInfo,
                          sizeof(MEMORY_BASIC_INFORMATION)))
    {
        py_tuple = NULL;
        if (baseAddress > maxAddr)
            break;
        if (GetMappedFileNameW(hProcess, baseAddress, mappedFileName,
                               sizeof(mappedFileName)))
        {
            py_str = PyUnicode_FromWideChar(mappedFileName,
                                            wcslen(mappedFileName));
            if (py_str == NULL)
                goto error;
#ifdef _WIN64
           py_tuple = Py_BuildValue(
              "(KsOI)",
              (unsigned long long)baseAddress,
#else
           py_tuple = Py_BuildValue(
              "(ksOI)",
              (unsigned long)baseAddress,
#endif
              get_region_protection_string(basicInfo.Protect),
              py_str,
              basicInfo.RegionSize);

            if (!py_tuple)
                goto error;
            if (PyList_Append(py_retlist, py_tuple))
                goto error;
            Py_CLEAR(py_tuple);
            Py_CLEAR(py_str);
        }
        baseAddress = (PCHAR)baseAddress + basicInfo.RegionSize;
    }

    CloseHandle(hProcess);
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_XDECREF(py_str);
    Py_DECREF(py_retlist);
    if (hProcess != NULL)
        CloseHandle(hProcess);
    return NULL;
}


/*
 * Return a {pid:ppid, ...} dict for all running processes.
 */
static PyObject *
psutil_ppid_map(PyObject *self, PyObject *args) {
    PyObject *py_pid = NULL;
    PyObject *py_ppid = NULL;
    PyObject *py_retdict = PyDict_New();
    HANDLE handle = NULL;
    PROCESSENTRY32 pe = {0};
    pe.dwSize = sizeof(PROCESSENTRY32);

    if (py_retdict == NULL)
        return NULL;
    handle = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (handle == INVALID_HANDLE_VALUE) {
        PyErr_SetFromWindowsErr(0);
        Py_DECREF(py_retdict);
        return NULL;
    }

    if (Process32First(handle, &pe)) {
        do {
            py_pid = PyLong_FromPid(pe.th32ProcessID);
            if (py_pid == NULL)
                goto error;
            py_ppid = PyLong_FromPid(pe.th32ParentProcessID);
            if (py_ppid == NULL)
                goto error;
            if (PyDict_SetItem(py_retdict, py_pid, py_ppid))
                goto error;
            Py_CLEAR(py_pid);
            Py_CLEAR(py_ppid);
        } while (Process32Next(handle, &pe));
    }

    CloseHandle(handle);
    return py_retdict;

error:
    Py_XDECREF(py_pid);
    Py_XDECREF(py_ppid);
    Py_DECREF(py_retdict);
    CloseHandle(handle);
    return NULL;
}


/*
 * Return battery usage stats.
 */
static PyObject *
psutil_sensors_battery(PyObject *self, PyObject *args) {
    SYSTEM_POWER_STATUS sps;

    if (GetSystemPowerStatus(&sps) == 0) {
        PyErr_SetFromWindowsErr(0);
        return NULL;
    }
    return Py_BuildValue(
        "iiiI",
        sps.ACLineStatus,  // whether AC is connected: 0=no, 1=yes, 255=unknown
        // status flag:
        // 1, 2, 4 = high, low, critical
        // 8 = charging
        // 128 = no battery
        sps.BatteryFlag,
        sps.BatteryLifePercent,  // percent
        sps.BatteryLifeTime  // remaining secs
    );
}


/*
 * System memory page size as an int.
 */
static PyObject *
psutil_getpagesize(PyObject *self, PyObject *args) {
    // XXX: we may want to use GetNativeSystemInfo to differentiate
    // page size for WoW64 processes (but am not sure).
    return Py_BuildValue("I", PSUTIL_SYSTEM_INFO.dwPageSize);
}


// ------------------------ Python init ---------------------------

static PyMethodDef
PsutilMethods[] = {
    // --- per-process functions
    {"proc_cmdline", (PyCFunction)(void(*)(void))psutil_proc_cmdline,
        METH_VARARGS | METH_KEYWORDS,
     "Return process cmdline as a list of cmdline arguments"},
    {"proc_environ", psutil_proc_environ, METH_VARARGS,
     "Return process environment data"},
    {"proc_exe", psutil_proc_exe, METH_VARARGS,
     "Return path of the process executable"},
    {"proc_kill", psutil_proc_kill, METH_VARARGS,
     "Kill the process identified by the given PID"},
    {"proc_times", psutil_proc_times, METH_VARARGS,
     "Return tuple of user/kern time for the given PID"},
    {"proc_memory_info", psutil_proc_memory_info, METH_VARARGS,
     "Return a tuple of process memory information"},
    {"proc_memory_uss", psutil_proc_memory_uss, METH_VARARGS,
     "Return the USS of the process"},
    {"proc_cwd", psutil_proc_cwd, METH_VARARGS,
     "Return process current working directory"},
    {"proc_suspend_or_resume", psutil_proc_suspend_or_resume, METH_VARARGS,
     "Suspend or resume a process"},
    {"proc_open_files", psutil_proc_open_files, METH_VARARGS,
     "Return files opened by process"},
    {"proc_username", psutil_proc_username, METH_VARARGS,
     "Return the username of a process"},
    {"proc_threads", psutil_proc_threads, METH_VARARGS,
     "Return process threads information as a list of tuple"},
    {"proc_wait", psutil_proc_wait, METH_VARARGS,
     "Wait for process to terminate and return its exit code."},
    {"proc_priority_get", psutil_proc_priority_get, METH_VARARGS,
     "Return process priority."},
    {"proc_priority_set", psutil_proc_priority_set, METH_VARARGS,
     "Set process priority."},
    {"proc_io_priority_get", psutil_proc_io_priority_get, METH_VARARGS,
     "Return process IO priority."},
    {"proc_io_priority_set", psutil_proc_io_priority_set, METH_VARARGS,
     "Set process IO priority."},
    {"proc_cpu_affinity_get", psutil_proc_cpu_affinity_get, METH_VARARGS,
     "Return process CPU affinity as a bitmask."},
    {"proc_cpu_affinity_set", psutil_proc_cpu_affinity_set, METH_VARARGS,
     "Set process CPU affinity."},
    {"proc_io_counters", psutil_proc_io_counters, METH_VARARGS,
     "Get process I/O counters."},
    {"proc_is_suspended", psutil_proc_is_suspended, METH_VARARGS,
     "Return True if one of the process threads is in a suspended state"},
    {"proc_num_handles", psutil_proc_num_handles, METH_VARARGS,
     "Return the number of handles opened by process."},
    {"proc_memory_maps", psutil_proc_memory_maps, METH_VARARGS,
     "Return a list of process's memory mappings"},

    // --- alternative pinfo interface
    {"proc_info", psutil_proc_info, METH_VARARGS,
     "Various process information"},

    // --- system-related functions
    {"pids", psutil_pids, METH_VARARGS,
     "Returns a list of PIDs currently running on the system"},
    {"ppid_map", psutil_ppid_map, METH_VARARGS,
     "Return a {pid:ppid, ...} dict for all running processes"},
    {"pid_exists", psutil_pid_exists, METH_VARARGS,
     "Determine if the process exists in the current process list."},
    {"cpu_count_logical", psutil_cpu_count_logical, METH_VARARGS,
     "Returns the number of logical CPUs on the system"},
    {"cpu_count_phys", psutil_cpu_count_phys, METH_VARARGS,
     "Returns the number of physical CPUs on the system"},
    {"boot_time", psutil_boot_time, METH_VARARGS,
     "Return the system boot time expressed in seconds since the epoch."},
    {"virtual_mem", psutil_virtual_mem, METH_VARARGS,
     "Return the total amount of physical memory, in bytes"},
    {"cpu_times", psutil_cpu_times, METH_VARARGS,
     "Return system cpu times as a list"},
    {"per_cpu_times", psutil_per_cpu_times, METH_VARARGS,
     "Return system per-cpu times as a list of tuples"},
    {"disk_usage", psutil_disk_usage, METH_VARARGS,
     "Return path's disk total and free as a Python tuple."},
    {"net_io_counters", psutil_net_io_counters, METH_VARARGS,
     "Return dict of tuples of networks I/O information."},
    {"disk_io_counters", psutil_disk_io_counters, METH_VARARGS,
     "Return dict of tuples of disks I/O information."},
    {"users", psutil_users, METH_VARARGS,
     "Return a list of currently connected users."},
    {"disk_partitions", psutil_disk_partitions, METH_VARARGS,
     "Return disk partitions."},
    {"net_connections", psutil_net_connections, METH_VARARGS,
     "Return system-wide connections"},
    {"net_if_addrs", psutil_net_if_addrs, METH_VARARGS,
     "Return NICs addresses."},
    {"net_if_stats", psutil_net_if_stats, METH_VARARGS,
     "Return NICs stats."},
    {"cpu_stats", psutil_cpu_stats, METH_VARARGS,
     "Return NICs stats."},
    {"cpu_freq", psutil_cpu_freq, METH_VARARGS,
     "Return CPU frequency."},
    {"init_loadavg_counter", (PyCFunction)psutil_init_loadavg_counter,
     METH_VARARGS,
     "Initializes the emulated load average calculator."},
    {"getloadavg", (PyCFunction)psutil_get_loadavg, METH_VARARGS,
     "Returns the emulated POSIX-like load average."},
    {"sensors_battery", psutil_sensors_battery, METH_VARARGS,
     "Return battery metrics usage."},
    {"getpagesize", psutil_getpagesize, METH_VARARGS,
     "Return system memory page size."},

    // --- windows services
    {"winservice_enumerate", psutil_winservice_enumerate, METH_VARARGS,
     "List all services"},
    {"winservice_query_config", psutil_winservice_query_config, METH_VARARGS,
     "Return service config"},
    {"winservice_query_status", psutil_winservice_query_status, METH_VARARGS,
     "Return service config"},
    {"winservice_query_descr", psutil_winservice_query_descr, METH_VARARGS,
     "Return the description of a service"},
    {"winservice_start", psutil_winservice_start, METH_VARARGS,
     "Start a service"},
    {"winservice_stop", psutil_winservice_stop, METH_VARARGS,
     "Stop a service"},

    // --- windows API bindings
    {"win32_QueryDosDevice", psutil_win32_QueryDosDevice, METH_VARARGS,
     "QueryDosDevice binding"},

    // --- others
    {"set_testing", psutil_set_testing, METH_NOARGS,
     "Set psutil in testing mode"},

    {NULL, NULL, 0, NULL}
};


struct module_state {
    PyObject *error;
};

#if PY_MAJOR_VERSION >= 3
#define GETSTATE(m) ((struct module_state*)PyModule_GetState(m))
#else
#define GETSTATE(m) (&_state)
static struct module_state _state;
#endif

#if PY_MAJOR_VERSION >= 3

static int psutil_windows_traverse(PyObject *m, visitproc visit, void *arg) {
    Py_VISIT(GETSTATE(m)->error);
    return 0;
}

static int psutil_windows_clear(PyObject *m) {
    Py_CLEAR(GETSTATE(m)->error);
    return 0;
}

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "psutil_windows",
    NULL,
    sizeof(struct module_state),
    PsutilMethods,
    NULL,
    psutil_windows_traverse,
    psutil_windows_clear,
    NULL
};

#define INITERROR return NULL

PyMODINIT_FUNC PyInit__psutil_windows(void)

#else
#define INITERROR return
void init_psutil_windows(void)
#endif
{
    struct module_state *st = NULL;
#if PY_MAJOR_VERSION >= 3
    PyObject *module = PyModule_Create(&moduledef);
#else
    PyObject *module = Py_InitModule("_psutil_windows", PsutilMethods);
#endif
    if (module == NULL)
        INITERROR;

    if (psutil_setup() != 0)
        INITERROR;
    if (psutil_load_globals() != 0)
        INITERROR;
    if (psutil_set_se_debug() != 0)
        INITERROR;

    st = GETSTATE(module);
    st->error = PyErr_NewException("_psutil_windows.Error", NULL, NULL);
    if (st->error == NULL) {
        Py_DECREF(module);
        INITERROR;
    }

    // Exceptions.
    TimeoutExpired = PyErr_NewException(
        "_psutil_windows.TimeoutExpired", NULL, NULL);
    Py_INCREF(TimeoutExpired);
    PyModule_AddObject(module, "TimeoutExpired", TimeoutExpired);

    TimeoutAbandoned = PyErr_NewException(
        "_psutil_windows.TimeoutAbandoned", NULL, NULL);
    Py_INCREF(TimeoutAbandoned);
    PyModule_AddObject(module, "TimeoutAbandoned", TimeoutAbandoned);

    // version constant
    PyModule_AddIntConstant(module, "version", PSUTIL_VERSION);

    // process status constants
    // http://msdn.microsoft.com/en-us/library/ms683211(v=vs.85).aspx
    PyModule_AddIntConstant(
        module, "ABOVE_NORMAL_PRIORITY_CLASS", ABOVE_NORMAL_PRIORITY_CLASS);
    PyModule_AddIntConstant(
        module, "BELOW_NORMAL_PRIORITY_CLASS", BELOW_NORMAL_PRIORITY_CLASS);
    PyModule_AddIntConstant(
        module, "HIGH_PRIORITY_CLASS", HIGH_PRIORITY_CLASS);
    PyModule_AddIntConstant(
        module, "IDLE_PRIORITY_CLASS", IDLE_PRIORITY_CLASS);
    PyModule_AddIntConstant(
        module, "NORMAL_PRIORITY_CLASS", NORMAL_PRIORITY_CLASS);
    PyModule_AddIntConstant(
        module, "REALTIME_PRIORITY_CLASS", REALTIME_PRIORITY_CLASS);

    // connection status constants
    // http://msdn.microsoft.com/en-us/library/cc669305.aspx
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_CLOSED", MIB_TCP_STATE_CLOSED);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_CLOSING", MIB_TCP_STATE_CLOSING);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_CLOSE_WAIT", MIB_TCP_STATE_CLOSE_WAIT);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_LISTEN", MIB_TCP_STATE_LISTEN);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_ESTAB", MIB_TCP_STATE_ESTAB);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_SYN_SENT", MIB_TCP_STATE_SYN_SENT);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_SYN_RCVD", MIB_TCP_STATE_SYN_RCVD);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_FIN_WAIT1", MIB_TCP_STATE_FIN_WAIT1);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_FIN_WAIT2", MIB_TCP_STATE_FIN_WAIT2);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_LAST_ACK", MIB_TCP_STATE_LAST_ACK);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_TIME_WAIT", MIB_TCP_STATE_TIME_WAIT);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_TIME_WAIT", MIB_TCP_STATE_TIME_WAIT);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_DELETE_TCB", MIB_TCP_STATE_DELETE_TCB);
    PyModule_AddIntConstant(
        module, "PSUTIL_CONN_NONE", PSUTIL_CONN_NONE);

    // service status constants
    /*
    PyModule_AddIntConstant(
        module, "SERVICE_CONTINUE_PENDING", SERVICE_CONTINUE_PENDING);
    PyModule_AddIntConstant(
        module, "SERVICE_PAUSE_PENDING", SERVICE_PAUSE_PENDING);
    PyModule_AddIntConstant(
        module, "SERVICE_PAUSED", SERVICE_PAUSED);
    PyModule_AddIntConstant(
        module, "SERVICE_RUNNING", SERVICE_RUNNING);
    PyModule_AddIntConstant(
        module, "SERVICE_START_PENDING", SERVICE_START_PENDING);
    PyModule_AddIntConstant(
        module, "SERVICE_STOP_PENDING", SERVICE_STOP_PENDING);
    PyModule_AddIntConstant(
        module, "SERVICE_STOPPED", SERVICE_STOPPED);
    */

    // ...for internal use in _psutil_windows.py
    PyModule_AddIntConstant(
        module, "INFINITE", INFINITE);
    PyModule_AddIntConstant(
        module, "ERROR_ACCESS_DENIED", ERROR_ACCESS_DENIED);
    PyModule_AddIntConstant(
        module, "ERROR_INVALID_NAME", ERROR_INVALID_NAME);
    PyModule_AddIntConstant(
        module, "ERROR_SERVICE_DOES_NOT_EXIST", ERROR_SERVICE_DOES_NOT_EXIST);
    PyModule_AddIntConstant(
        module, "ERROR_PRIVILEGE_NOT_HELD", ERROR_PRIVILEGE_NOT_HELD);
    PyModule_AddIntConstant(
        module, "WINVER", PSUTIL_WINVER);
    PyModule_AddIntConstant(
        module, "WINDOWS_VISTA", PSUTIL_WINDOWS_VISTA);
    PyModule_AddIntConstant(
        module, "WINDOWS_7", PSUTIL_WINDOWS_7);
    PyModule_AddIntConstant(
        module, "WINDOWS_8", PSUTIL_WINDOWS_8);
    PyModule_AddIntConstant(
        module, "WINDOWS_8_1", PSUTIL_WINDOWS_8_1);
    PyModule_AddIntConstant(
        module, "WINDOWS_10", PSUTIL_WINDOWS_10);

#if PY_MAJOR_VERSION >= 3
    return module;
#endif
}
