/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

/*
 * Process related functions. Original code was moved in here from
 * psutil/_psutil_windows.c in 2023. For reference, here's the GIT blame
 * history before the move:
 * https://github.com/giampaolo/psutil/blame/59504a5/psutil/_psutil_windows.c
 */

// Fixes clash between winsock2.h and windows.h
#define WIN32_LEAN_AND_MEAN

#include <Python.h>
#include <windows.h>
#include <Psapi.h>  // memory_info(), memory_maps()
#include <signal.h>

#include "../../arch/all/init.h"


// Raised by Process.wait().
PyObject *TimeoutExpired;
PyObject *TimeoutAbandoned;


// Return 1 if PID exists in the current process list, else 0.
PyObject *
psutil_pid_exists(PyObject *self, PyObject *args) {
    DWORD pid;
    int status;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    status = psutil_pid_is_running(pid);
    if (-1 == status)
        return NULL;  // exception raised in psutil_pid_is_running()
    return PyBool_FromLong(status);
}


// Get various process info by using NtQuerySystemInformation. We use
// this as a fallback when faster functions fail with access denied.
// This is slower because it iterates over all processes.
PyObject *
psutil_proc_oneshot(PyObject *self, PyObject *args) {
    DWORD pid;
    PSYSTEM_PROCESS_INFORMATION proc;
    PVOID buffer = NULL;
    ULONG i;
    ULONG ctx_switches = 0;
    int suspended = 1;  // a process with no threads counts as suspended
    double user_time;
    double kernel_time;
    double create_time;
    PyObject *dict = PyDict_New();

    if (!dict)
        return NULL;
    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;
    if (psutil_proc_table_entry(pid, &proc, &buffer) != 0)
        goto error;

    for (i = 0; i < proc->NumberOfThreads; i++) {
        ctx_switches += proc->Threads[i].ContextSwitches;
        if (proc->Threads[i].ThreadState != Waiting
            || proc->Threads[i].WaitReason != Suspended)
        {
            suspended = 0;
        }
    }

    user_time = (double)proc->UserTime.HighPart * HI_T
                + (double)proc->UserTime.LowPart * LO_T;
    kernel_time = (double)proc->KernelTime.HighPart * HI_T
                  + (double)proc->KernelTime.LowPart * LO_T;

    // Convert the LARGE_INTEGER union to a Unix time.
    // It's the best I could find by googling and borrowing code here
    // and there. The time returned has a precision of 1 second.
    if (0 == pid || 4 == pid) {
        // the python module will translate this into BOOT_TIME later
        create_time = 0;
    }
    else {
        create_time = psutil_LargeIntegerToUnixTime(proc->CreateTime);
    }

    // clang-format off
    if (!pydict_add(dict, "num_handles", "k", proc->HandleCount)) goto error;
    if (!pydict_add(dict, "ctx_switches", "k", ctx_switches)) goto error;
    if (!pydict_add(dict, "is_suspended", "i", suspended)) goto error;
    if (!pydict_add(dict, "user_time", "d", user_time)) goto error;
    if (!pydict_add(dict, "kernel_time", "d", kernel_time)) goto error;
    if (!pydict_add(dict, "create_time", "d", create_time)) goto error;
    if (!pydict_add(dict, "num_threads", "k", proc->NumberOfThreads)) goto error;
    // I/O
    if (!pydict_add(dict, "io_rcount", "K", proc->ReadOperationCount.QuadPart)) goto error;
    if (!pydict_add(dict, "io_wcount", "K", proc->WriteOperationCount.QuadPart)) goto error;
    if (!pydict_add(dict, "io_rbytes", "K", proc->ReadTransferCount.QuadPart)) goto error;
    if (!pydict_add(dict, "io_wbytes", "K", proc->WriteTransferCount.QuadPart)) goto error;
    if (!pydict_add(dict, "io_count_others", "K", proc->OtherOperationCount.QuadPart)) goto error;
    if (!pydict_add(dict, "io_bytes_others", "K", proc->OtherTransferCount.QuadPart)) goto error;
    // proc memory
    if (!pydict_add(dict, "PageFaultCount", "K", (ULONGLONG)proc->PageFaultCount)) goto error;
    if (!pydict_add(dict, "HardFaultCount", "K", (ULONGLONG)proc->HardFaultCount)) goto error;
    if (!pydict_add(dict, "PeakWorkingSetSize", "K", (ULONGLONG)proc->PeakWorkingSetSize)) goto error;
    if (!pydict_add(dict, "WorkingSetSize", "K", (ULONGLONG)proc->WorkingSetSize)) goto error;
    if (!pydict_add(dict, "QuotaPeakPagedPoolUsage", "K", (ULONGLONG)proc->QuotaPeakPagedPoolUsage)) goto error;
    if (!pydict_add(dict, "QuotaPagedPoolUsage", "K", (ULONGLONG)proc->QuotaPagedPoolUsage)) goto error;
    if (!pydict_add(dict, "QuotaPeakNonPagedPoolUsage", "K", (ULONGLONG)proc->QuotaPeakNonPagedPoolUsage)) goto error;
    if (!pydict_add(dict, "QuotaNonPagedPoolUsage", "K", (ULONGLONG)proc->QuotaNonPagedPoolUsage)) goto error;
    if (!pydict_add(dict, "PagefileUsage", "K", (ULONGLONG)proc->PagefileUsage)) goto error;
    if (!pydict_add(dict, "PeakPagefileUsage", "K", (ULONGLONG)proc->PeakPagefileUsage)) goto error;
    if (!pydict_add(dict, "PrivatePageCount", "K", (ULONGLONG)proc->PrivatePageCount)) goto error;
    if (!pydict_add(dict, "VirtualSize", "K", (ULONGLONG)proc->VirtualSize)) goto error;
    if (!pydict_add(dict, "PeakVirtualSize", "K", (ULONGLONG)proc->PeakVirtualSize)) goto error;
    // clang-format on

    free(buffer);
    return dict;

error:
    if (buffer != NULL)
        free(buffer);
    Py_DECREF(dict);
    return NULL;
}


PyObject *
psutil_proc_kill(PyObject *self, PyObject *args) {
    HANDLE hProcess;
    DWORD pid;
    DWORD access = PROCESS_TERMINATE | PROCESS_QUERY_LIMITED_INFORMATION;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (pid == 0)
        return psutil_oserror_ad("automatically set for PID 0");

    hProcess = psutil_handle_from_pid(pid, access);
    if (hProcess == NULL) {
        return NULL;
    }

    if (!TerminateProcess(hProcess, SIGTERM)) {
        // ERROR_ACCESS_DENIED may happen if the process already died. See:
        // https://github.com/giampaolo/psutil/issues/1099
        // http://bugs.python.org/issue14252
        if (GetLastError() != ERROR_ACCESS_DENIED) {
            psutil_oserror_wsyscall("TerminateProcess");
            CloseHandle(hProcess);
            return NULL;
        }
    }

    CloseHandle(hProcess);
    Py_RETURN_NONE;
}


PyObject *
psutil_proc_wait(PyObject *self, PyObject *args) {
    HANDLE hProcess;
    DWORD ExitCode;
    DWORD retVal;
    DWORD pid;
    long timeout;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID "l", &pid, &timeout))
        return NULL;
    if (pid == 0)
        return psutil_oserror_ad("automatically set for PID 0");

    hProcess = OpenProcess(
        SYNCHRONIZE | PROCESS_QUERY_INFORMATION, FALSE, pid
    );
    if (hProcess == NULL) {
        if (GetLastError() == ERROR_INVALID_PARAMETER) {
            // no such process; we do not want to raise NSP but
            // return None instead.
            Py_RETURN_NONE;
        }
        else {
            psutil_oserror_wsyscall("OpenProcess");
            return NULL;
        }
    }

    // wait until the process has terminated
    Py_BEGIN_ALLOW_THREADS
    retVal = WaitForSingleObject(hProcess, timeout);
    Py_END_ALLOW_THREADS

    // handle return code
    if (retVal == WAIT_FAILED) {
        psutil_oserror_wsyscall("WaitForSingleObject");
        CloseHandle(hProcess);
        return NULL;
    }
    if (retVal == WAIT_TIMEOUT) {
        PyErr_SetString(
            TimeoutExpired, "WaitForSingleObject() returned WAIT_TIMEOUT"
        );
        CloseHandle(hProcess);
        return NULL;
    }
    if (retVal == WAIT_ABANDONED) {
        psutil_debug("WaitForSingleObject() -> WAIT_ABANDONED");
        PyErr_SetString(
            TimeoutAbandoned, "WaitForSingleObject() returned WAIT_ABANDONED"
        );
        CloseHandle(hProcess);
        return NULL;
    }

    // WaitForSingleObject() returned WAIT_OBJECT_0. It means the
    // process is gone so we can get its process exit code. The PID
    // may still stick around though but we'll handle that from Python.
    if (GetExitCodeProcess(hProcess, &ExitCode) == 0) {
        psutil_oserror_wsyscall("GetExitCodeProcess");
        CloseHandle(hProcess);
        return NULL;
    }

    CloseHandle(hProcess);

    return PyLong_FromLong((long)ExitCode);
}


// Return (user_time, kernel_time, create_time).
PyObject *
psutil_proc_times(PyObject *self, PyObject *args) {
    DWORD pid;
    HANDLE hProcess;
    FILETIME ftCreate, ftExit, ftKernel, ftUser;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    hProcess = psutil_handle_from_pid(pid, PROCESS_QUERY_LIMITED_INFORMATION);

    if (hProcess == NULL)
        return NULL;
    if (!GetProcessTimes(hProcess, &ftCreate, &ftExit, &ftKernel, &ftUser)) {
        if (GetLastError() == ERROR_ACCESS_DENIED) {
            // usually means the process has died so we throw a NoSuchProcess
            // here
            psutil_oserror_nsp("GetProcessTimes -> ERROR_ACCESS_DENIED");
        }
        else {
            psutil_oserror();
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
        (double)(ftUser.dwHighDateTime * HI_T + ftUser.dwLowDateTime * LO_T),
        (double)(ftKernel.dwHighDateTime * HI_T + ftKernel.dwLowDateTime * LO_T
        ),
        psutil_FiletimeToUnixTime(ftCreate)
    );
}


// Return process executable path. Works for all processes regardless
// of privilege. NtQuerySystemInformation has some sort of internal
// cache, since it succeeds even when a process is gone (but not if a
// PID never existed).
PyObject *
psutil_proc_exe(PyObject *self, PyObject *args) {
    DWORD pid;
    NTSTATUS status;
    PVOID buffer = NULL;
    ULONG bufferSize = 0x104 * 2;  // WIN_MAX_PATH * sizeof(wchar_t)
    SYSTEM_PROCESS_ID_INFORMATION processIdInfo;
    PyObject *py_exe;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    if (pid == 0)
        return psutil_oserror_ad("automatically set for PID 0");

    // ...because NtQuerySystemInformation can succeed for terminated
    // processes.
    if (psutil_check_pid_running(pid) != 0)
        return NULL;

    buffer = MALLOC_ZERO(bufferSize);
    if (!buffer) {
        PyErr_NoMemory();
        return NULL;
    }

    processIdInfo.ProcessId = (HANDLE)(ULONG_PTR)pid;
    processIdInfo.ImageName.Length = 0;
    processIdInfo.ImageName.MaximumLength = (USHORT)bufferSize;
    processIdInfo.ImageName.Buffer = buffer;

    status = NtQuerySystemInformation(
        SystemProcessIdInformation,
        &processIdInfo,
        sizeof(SYSTEM_PROCESS_ID_INFORMATION),
        NULL
    );

    if ((status == STATUS_INFO_LENGTH_MISMATCH)
        && (processIdInfo.ImageName.MaximumLength <= bufferSize))
    {
        // Required length was NOT stored in MaximumLength (WOW64 issue).
        ULONG maxBufferSize = 0x7FFF * 2;  // NTFS_MAX_PATH * sizeof(wchar_t)
        do {
            // Iteratively double the size of the buffer up to maxBufferSize
            bufferSize *= 2;
            FREE(buffer);
            buffer = MALLOC_ZERO(bufferSize);
            if (!buffer) {
                PyErr_NoMemory();
                return NULL;
            }

            processIdInfo.ImageName.MaximumLength = (USHORT)bufferSize;
            processIdInfo.ImageName.Buffer = buffer;

            status = NtQuerySystemInformation(
                SystemProcessIdInformation,
                &processIdInfo,
                sizeof(SYSTEM_PROCESS_ID_INFORMATION),
                NULL
            );
        } while ((status == STATUS_INFO_LENGTH_MISMATCH)
                 && (bufferSize <= maxBufferSize));
    }
    else if (status == STATUS_INFO_LENGTH_MISMATCH) {
        // Required length is stored in MaximumLength.
        FREE(buffer);
        buffer = MALLOC_ZERO(processIdInfo.ImageName.MaximumLength);
        if (!buffer) {
            PyErr_NoMemory();
            return NULL;
        }

        processIdInfo.ImageName.Buffer = buffer;

        status = NtQuerySystemInformation(
            SystemProcessIdInformation,
            &processIdInfo,
            sizeof(SYSTEM_PROCESS_ID_INFORMATION),
            NULL
        );
    }

    if (!NT_SUCCESS(status)) {
        FREE(buffer);
        if (psutil_pid_is_running(pid) == 0)
            psutil_oserror_nsp("psutil_pid_is_running -> 0");
        else
            psutil_SetFromNTStatusErr(status, "NtQuerySystemInformation");
        return NULL;
    }

    if (processIdInfo.ImageName.Buffer == NULL) {
        // Happens for PID 4.
        py_exe = PyUnicode_FromString("");
    }
    else {
        py_exe = PyUnicode_FromWideChar(
            processIdInfo.ImageName.Buffer, processIdInfo.ImageName.Length / 2
        );
    }
    FREE(buffer);
    return py_exe;
}


PyObject *
psutil_proc_memory_info(PyObject *self, PyObject *args) {
    HANDLE hProcess;
    DWORD pid;
    PROCESS_MEMORY_COUNTERS_EX cnt;
    PyObject *dict = PyDict_New();

    if (!dict)
        return NULL;
    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;

    hProcess = psutil_handle_from_pid(pid, PROCESS_QUERY_LIMITED_INFORMATION);
    if (NULL == hProcess)
        goto error;

    if (!GetProcessMemoryInfo(
            hProcess, (PPROCESS_MEMORY_COUNTERS)&cnt, sizeof(cnt)
        ))
    {
        psutil_oserror();
        CloseHandle(hProcess);
        goto error;
    }
    CloseHandle(hProcess);

    // clang-format off
    if (!pydict_add(dict, "PageFaultCount", "K", (ULONGLONG)cnt.PageFaultCount)) goto error;
    if (!pydict_add(dict, "PeakWorkingSetSize", "K", (ULONGLONG)cnt.PeakWorkingSetSize)) goto error;
    if (!pydict_add(dict, "WorkingSetSize", "K", (ULONGLONG)cnt.WorkingSetSize)) goto error;
    if (!pydict_add(dict, "QuotaPeakPagedPoolUsage", "K", (ULONGLONG)cnt.QuotaPeakPagedPoolUsage)) goto error;
    if (!pydict_add(dict, "QuotaPagedPoolUsage", "K", (ULONGLONG)cnt.QuotaPagedPoolUsage)) goto error;
    if (!pydict_add(dict, "QuotaPeakNonPagedPoolUsage", "K", (ULONGLONG)cnt.QuotaPeakNonPagedPoolUsage)) goto error;
    if (!pydict_add(dict, "QuotaNonPagedPoolUsage", "K", (ULONGLONG)cnt.QuotaNonPagedPoolUsage)) goto error;
    if (!pydict_add(dict, "PagefileUsage", "K", (ULONGLONG)cnt.PagefileUsage)) goto error;
    if (!pydict_add(dict, "PeakPagefileUsage", "K", (ULONGLONG)cnt.PeakPagefileUsage)) goto error;
    if (!pydict_add(dict, "PrivateUsage", "K", (ULONGLONG)cnt.PrivateUsage)) goto error;
    // clang-format on
    return dict;

error:
    Py_DECREF(dict);
    return NULL;
}


static int
psutil_GetProcWsetInformation(
    DWORD pid, HANDLE hProcess, PMEMORY_WORKING_SET_INFORMATION *wSetInfo
) {
    NTSTATUS status;
    PVOID buffer;
    SIZE_T bufferSize;

    bufferSize = 0x8000;
    buffer = MALLOC_ZERO(bufferSize);
    if (!buffer) {
        PyErr_NoMemory();
        return -1;
    }

    while ((status = NtQueryVirtualMemory(
                hProcess,
                NULL,
                MemoryWorkingSetInformation,
                buffer,
                bufferSize,
                NULL
            ))
           == STATUS_INFO_LENGTH_MISMATCH)
    {
        FREE(buffer);
        bufferSize *= 2;
        // Fail if we're resizing the buffer to something very large.
        if (bufferSize > 256 * 1024 * 1024) {
            psutil_runtime_error("NtQueryVirtualMemory bufsize is too large");
            return -1;
        }
        buffer = MALLOC_ZERO(bufferSize);
        if (!buffer) {
            PyErr_NoMemory();
            return -1;
        }
    }

    if (!NT_SUCCESS(status)) {
        if (status == STATUS_ACCESS_DENIED) {
            psutil_oserror_ad("NtQueryVirtualMemory -> STATUS_ACCESS_DENIED");
        }
        else if (psutil_pid_is_running(pid) == 0) {
            psutil_oserror_nsp("psutil_pid_is_running -> 0");
        }
        else {
            PyErr_Clear();
            psutil_SetFromNTStatusErr(
                status, "NtQueryVirtualMemory(MemoryWorkingSetInformation)"
            );
        }
        FREE(buffer);
        return -1;
    }

    *wSetInfo = (PMEMORY_WORKING_SET_INFORMATION)buffer;
    return 0;
}


// Returns the USS of the process.
// Reference:
// https://dxr.mozilla.org/mozilla-central/source/xpcom/base/nsMemoryReporterManager.cpp
PyObject *
psutil_proc_memory_uss(PyObject *self, PyObject *args) {
    DWORD pid;
    HANDLE hProcess;
    PSUTIL_PROCESS_WS_COUNTERS wsCounters;
    PMEMORY_WORKING_SET_INFORMATION wsInfo;
    ULONG_PTR i;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
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
        if (!wsInfo->WorkingSetInfo[i].Shared
            || wsInfo->WorkingSetInfo[i].ShareCount <= 1)
        {
            wsCounters.NumberOfPrivatePages++;
        }
    }

    FREE(wsInfo);
    CloseHandle(hProcess);

    return Py_BuildValue("I", wsCounters.NumberOfPrivatePages);
}


// Resume or suspends a process.
PyObject *
psutil_proc_suspend_or_resume(PyObject *self, PyObject *args) {
    DWORD pid;
    NTSTATUS status;
    HANDLE hProcess;
    DWORD access = PROCESS_SUSPEND_RESUME | PROCESS_QUERY_LIMITED_INFORMATION;
    int suspend;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID "p", &pid, &suspend))
        return NULL;

    hProcess = psutil_handle_from_pid(pid, access);
    if (hProcess == NULL)
        return NULL;

    if (suspend)
        status = NtSuspendProcess(hProcess);
    else
        status = NtResumeProcess(hProcess);

    if (!NT_SUCCESS(status)) {
        CloseHandle(hProcess);
        return psutil_SetFromNTStatusErr(status, "NtSuspend|ResumeProcess");
    }

    CloseHandle(hProcess);
    Py_RETURN_NONE;
}


PyObject *
psutil_proc_threads(PyObject *self, PyObject *args) {
    DWORD pid;
    ULONG i;
    PSYSTEM_PROCESS_INFORMATION process;
    PVOID buffer;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;
    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;
    if (psutil_proc_table_entry(pid, &process, &buffer) != 0)
        goto error;

    for (i = 0; i < process->NumberOfThreads; i++) {
        SYSTEM_THREAD_INFORMATION *thread = &process->Threads[i];

        // Times count 100-nanosecond intervals, turn them into secs.
        if (!pylist_append_fmt(
                py_retlist,
                "kdd",
                (DWORD)(ULONG_PTR)thread->ClientId.UniqueThread,
                (double)thread->UserTime.HighPart * HI_T
                    + (double)thread->UserTime.LowPart * LO_T,
                (double)thread->KernelTime.HighPart * HI_T
                    + (double)thread->KernelTime.LowPart * LO_T
            ))
        {
            free(buffer);
            goto error;
        }
    }

    free(buffer);
    return py_retlist;

error:
    Py_DECREF(py_retlist);
    return NULL;
}


PyObject *
psutil_proc_open_files(PyObject *self, PyObject *args) {
    DWORD pid;
    HANDLE processHandle;
    DWORD access = PROCESS_DUP_HANDLE | PROCESS_QUERY_INFORMATION;
    PyObject *py_retlist;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    processHandle = psutil_handle_from_pid(pid, access);
    if (processHandle == NULL)
        return NULL;

    py_retlist = psutil_get_open_files(processHandle);
    CloseHandle(processHandle);
    return py_retlist;
}


static PTOKEN_USER
user_token_from_pid(DWORD pid) {
    HANDLE hProcess = NULL;
    HANDLE hToken = NULL;
    PTOKEN_USER userToken = NULL;
    ULONG bufferSize = 0x100;

    hProcess = psutil_handle_from_pid(pid, PROCESS_QUERY_LIMITED_INFORMATION);
    if (hProcess == NULL)
        return NULL;

    if (!OpenProcessToken(hProcess, TOKEN_QUERY, &hToken)) {
        psutil_oserror_wsyscall("OpenProcessToken");
        goto error;
    }

    // Get the user SID.
    while (1) {
        userToken = malloc(bufferSize);
        if (userToken == NULL) {
            PyErr_NoMemory();
            goto error;
        }
        if (!GetTokenInformation(
                hToken, TokenUser, userToken, bufferSize, &bufferSize
            ))
        {
            if (GetLastError() == ERROR_INSUFFICIENT_BUFFER) {
                free(userToken);
                userToken = NULL;
                continue;
            }
            else {
                psutil_oserror_wsyscall("GetTokenInformation");
                goto error;
            }
        }
        break;
    }

    CloseHandle(hProcess);
    CloseHandle(hToken);
    return userToken;

error:
    if (userToken != NULL)
        free(userToken);
    if (hProcess != NULL)
        CloseHandle(hProcess);
    if (hToken != NULL)
        CloseHandle(hToken);
    return NULL;
}


// Return process username as a "DOMAIN//USERNAME" string.
PyObject *
psutil_proc_username(PyObject *self, PyObject *args) {
    DWORD pid;
    PTOKEN_USER userToken = NULL;
    WCHAR *userName = NULL;
    WCHAR *domainName = NULL;
    ULONG nameSize = 0x100;
    ULONG domainNameSize = 0x100;
    SID_NAME_USE nameUse;
    PyObject *py_username = NULL;
    PyObject *py_domain = NULL;
    PyObject *py_tuple = NULL;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    userToken = user_token_from_pid(pid);
    if (userToken == NULL)
        return NULL;

    // resolve the SID to a name
    while (1) {
        userName = malloc(nameSize * sizeof(WCHAR));
        if (userName == NULL) {
            PyErr_NoMemory();
            goto error;
        }
        domainName = malloc(domainNameSize * sizeof(WCHAR));
        if (domainName == NULL) {
            PyErr_NoMemory();
            goto error;
        }
        if (!LookupAccountSidW(
                NULL,
                userToken->User.Sid,
                userName,
                &nameSize,
                domainName,
                &domainNameSize,
                &nameUse
            ))
        {
            if (GetLastError() == ERROR_INSUFFICIENT_BUFFER) {
                free(userName);
                free(domainName);
                continue;
            }
            else if (GetLastError() == ERROR_NONE_MAPPED) {
                // From MS doc:
                // https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-lookupaccountsida
                // If the function cannot find an account name for the SID,
                // GetLastError returns ERROR_NONE_MAPPED. This can occur if
                // a network time-out prevents the function from finding the
                // name. It also occurs for SIDs that have no corresponding
                // account name, such as a logon SID that identifies a logon
                // session.
                psutil_oserror_ad("LookupAccountSidW -> ERROR_NONE_MAPPED");
                goto error;
            }
            else {
                psutil_oserror_wsyscall("LookupAccountSidW");
                goto error;
            }
        }
        break;
    }

    py_domain = PyUnicode_FromWideChar(domainName, wcslen(domainName));
    if (!py_domain)
        goto error;
    py_username = PyUnicode_FromWideChar(userName, wcslen(userName));
    if (!py_username)
        goto error;
    py_tuple = Py_BuildValue("OO", py_domain, py_username);
    if (!py_tuple)
        goto error;
    Py_DECREF(py_domain);
    Py_DECREF(py_username);

    free(userName);
    free(domainName);
    free(userToken);
    return py_tuple;

error:
    if (userName != NULL)
        free(userName);
    if (domainName != NULL)
        free(domainName);
    if (userToken != NULL)
        free(userToken);
    Py_XDECREF(py_domain);
    Py_XDECREF(py_username);
    Py_XDECREF(py_tuple);
    return NULL;
}


// Get process priority as a Python integer.
PyObject *
psutil_proc_priority_get(PyObject *self, PyObject *args) {
    DWORD pid;
    DWORD priority;
    HANDLE hProcess;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    hProcess = psutil_handle_from_pid(pid, PROCESS_QUERY_LIMITED_INFORMATION);
    if (hProcess == NULL)
        return NULL;

    priority = GetPriorityClass(hProcess);
    if (priority == 0) {
        psutil_oserror();
        CloseHandle(hProcess);
        return NULL;
    }
    CloseHandle(hProcess);
    return Py_BuildValue("i", priority);
}


// Set process priority.
PyObject *
psutil_proc_priority_set(PyObject *self, PyObject *args) {
    DWORD pid;
    int priority;
    int retval;
    HANDLE hProcess;
    DWORD access = PROCESS_QUERY_INFORMATION | PROCESS_SET_INFORMATION;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID "i", &pid, &priority))
        return NULL;
    hProcess = psutil_handle_from_pid(pid, access);
    if (hProcess == NULL)
        return NULL;

    retval = SetPriorityClass(hProcess, priority);
    if (retval == 0) {
        psutil_oserror();
        CloseHandle(hProcess);
        return NULL;
    }

    CloseHandle(hProcess);
    Py_RETURN_NONE;
}


PyObject *
psutil_proc_io_priority_get(PyObject *self, PyObject *args) {
    DWORD pid;
    HANDLE hProcess;
    DWORD IoPriority;
    NTSTATUS status;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    hProcess = psutil_handle_from_pid(pid, PROCESS_QUERY_LIMITED_INFORMATION);
    if (hProcess == NULL)
        return NULL;

    status = NtQueryInformationProcess(
        hProcess, ProcessIoPriority, &IoPriority, sizeof(DWORD), NULL
    );

    CloseHandle(hProcess);
    if (!NT_SUCCESS(status))
        return psutil_SetFromNTStatusErr(status, "NtQueryInformationProcess");
    return Py_BuildValue("i", IoPriority);
}


PyObject *
psutil_proc_io_priority_set(PyObject *self, PyObject *args) {
    DWORD pid;
    DWORD prio;
    HANDLE hProcess;
    NTSTATUS status;
    DWORD access = PROCESS_QUERY_INFORMATION | PROCESS_SET_INFORMATION;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID "i", &pid, &prio))
        return NULL;

    hProcess = psutil_handle_from_pid(pid, access);
    if (hProcess == NULL)
        return NULL;

    status = NtSetInformationProcess(
        hProcess, ProcessIoPriority, (PVOID)&prio, sizeof(DWORD)
    );

    CloseHandle(hProcess);
    if (!NT_SUCCESS(status))
        return psutil_SetFromNTStatusErr(status, "NtSetInformationProcess");
    Py_RETURN_NONE;
}


PyObject *
psutil_proc_io_counters(PyObject *self, PyObject *args) {
    DWORD pid;
    HANDLE hProcess;
    IO_COUNTERS IoCounters;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    hProcess = psutil_handle_from_pid(pid, PROCESS_QUERY_LIMITED_INFORMATION);
    if (NULL == hProcess)
        return NULL;

    if (!GetProcessIoCounters(hProcess, &IoCounters)) {
        psutil_oserror();
        CloseHandle(hProcess);
        return NULL;
    }

    CloseHandle(hProcess);
    return Py_BuildValue(
        "(KKKKKK)",
        IoCounters.ReadOperationCount,
        IoCounters.WriteOperationCount,
        IoCounters.ReadTransferCount,
        IoCounters.WriteTransferCount,
        IoCounters.OtherOperationCount,
        IoCounters.OtherTransferCount
    );
}


// Return process CPU affinity as a bitmask.
PyObject *
psutil_proc_cpu_affinity_get(PyObject *self, PyObject *args) {
    DWORD pid;
    HANDLE hProcess;
    DWORD_PTR proc_mask;
    DWORD_PTR system_mask;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    hProcess = psutil_handle_from_pid(pid, PROCESS_QUERY_LIMITED_INFORMATION);
    if (hProcess == NULL) {
        return NULL;
    }
    if (GetProcessAffinityMask(hProcess, &proc_mask, &system_mask) == 0) {
        psutil_oserror();
        CloseHandle(hProcess);
        return NULL;
    }

    CloseHandle(hProcess);
    return Py_BuildValue("K", (unsigned long long)proc_mask);
}


PyObject *
psutil_proc_cpu_affinity_set(PyObject *self, PyObject *args) {
    DWORD pid;
    HANDLE hProcess;
    DWORD access = PROCESS_QUERY_INFORMATION | PROCESS_SET_INFORMATION;
    DWORD_PTR mask;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID "K", &pid, &mask))
        return NULL;
    hProcess = psutil_handle_from_pid(pid, access);
    if (hProcess == NULL)
        return NULL;

    if (SetProcessAffinityMask(hProcess, mask) == 0) {
        psutil_oserror();
        CloseHandle(hProcess);
        return NULL;
    }

    CloseHandle(hProcess);
    Py_RETURN_NONE;
}


PyObject *
psutil_proc_num_handles(PyObject *self, PyObject *args) {
    DWORD pid;
    HANDLE hProcess;
    DWORD handleCount;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    hProcess = psutil_handle_from_pid(pid, PROCESS_QUERY_LIMITED_INFORMATION);
    if (NULL == hProcess)
        return NULL;
    if (!GetProcessHandleCount(hProcess, &handleCount)) {
        psutil_oserror();
        CloseHandle(hProcess);
        return NULL;
    }
    CloseHandle(hProcess);
    return Py_BuildValue("k", handleCount);
}


static char *
get_region_protection_string(ULONG protection) {
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


PyObject *
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
    PyObject *py_str = NULL;

    if (py_retlist == NULL)
        return NULL;
    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;
    hProcess = psutil_handle_from_pid(pid, access);
    if (NULL == hProcess)
        goto error;

    maxAddr = PSUTIL_SYSTEM_INFO.lpMaximumApplicationAddress;
    baseAddress = NULL;

    while (VirtualQueryEx(
        hProcess, baseAddress, &basicInfo, sizeof(MEMORY_BASIC_INFORMATION)
    ))
    {
        if (baseAddress > maxAddr)
            break;
        // nSize is in characters, not bytes.
        if (GetMappedFileNameW(
                hProcess,
                baseAddress,
                mappedFileName,
                sizeof(mappedFileName) / sizeof(WCHAR)
            ))
        {
            py_str = PyUnicode_FromWideChar(
                mappedFileName, wcslen(mappedFileName)
            );
            if (py_str == NULL)
                goto error;
            if (!pylist_append_fmt(
                    py_retlist,
                    "(KsOI)",
                    (unsigned long long)baseAddress,
                    get_region_protection_string(basicInfo.Protect),
                    py_str,
                    basicInfo.RegionSize
                ))
            {
                goto error;
            }
            Py_CLEAR(py_str);
        }
        baseAddress = (PCHAR)baseAddress + basicInfo.RegionSize;
    }

    CloseHandle(hProcess);
    return py_retlist;

error:
    Py_XDECREF(py_str);
    Py_DECREF(py_retlist);
    if (hProcess != NULL)
        CloseHandle(hProcess);
    return NULL;
}


// Return the parent PID. Needs a handle, so it can fail with
// AccessDenied; the Python layer falls back to ppid_map() then.
PyObject *
psutil_proc_ppid(PyObject *self, PyObject *args) {
    DWORD pid;
    HANDLE hProcess;
    NTSTATUS status;
    PROCESS_BASIC_INFORMATION pbi;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    hProcess = psutil_handle_from_pid(pid, PROCESS_QUERY_LIMITED_INFORMATION);
    if (hProcess == NULL)
        return NULL;

    status = NtQueryInformationProcess(
        hProcess, ProcessBasicInformation, &pbi, sizeof(pbi), NULL
    );
    CloseHandle(hProcess);
    if (!NT_SUCCESS(status)) {
        psutil_SetFromNTStatusErr(
            status, "NtQueryInformationProcess(ProcessBasicInformation)"
        );
        return NULL;
    }

    return PyLong_FromPid((DWORD)pbi.InheritedFromUniqueProcessId);
}


// Return a {pid:ppid, ...} dict for all running processes.
PyObject *
psutil_ppid_map(PyObject *self, PyObject *args) {
    PyObject *py_pid = NULL;
    PyObject *py_ppid = NULL;
    PyObject *py_retdict = PyDict_New();
    PVOID buffer;
    PSYSTEM_PROCESS_INFORMATION process;

    if (py_retdict == NULL)
        return NULL;
    if (psutil_proc_table(&buffer) != 0) {
        Py_DECREF(py_retdict);
        return NULL;
    }

    process = PSUTIL_FIRST_PROCESS(buffer);
    do {
        DWORD pid = (DWORD)(ULONG_PTR)process->UniqueProcessId;
        DWORD ppid = (DWORD)(ULONG_PTR)process->InheritedFromUniqueProcessId;

        py_pid = PyLong_FromPid(pid);
        if (py_pid == NULL)
            goto error;
        py_ppid = PyLong_FromPid(ppid);
        if (py_ppid == NULL)
            goto error;
        if (PyDict_SetItem(py_retdict, py_pid, py_ppid))
            goto error;
        Py_CLEAR(py_pid);
        Py_CLEAR(py_ppid);
    } while ((process = PSUTIL_NEXT_PROCESS(process)));

    free(buffer);
    return py_retdict;

error:
    Py_XDECREF(py_pid);
    Py_XDECREF(py_ppid);
    Py_DECREF(py_retdict);
    free(buffer);
    return NULL;
}
