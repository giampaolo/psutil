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
#include <tlhelp32.h>  // threads(), PROCESSENTRY32

// Link with Iphlpapi.lib
#pragma comment(lib, "IPHLPAPI.lib")

#include "../../_psutil_common.h"
#include "proc.h"
#include "proc_info.h"
#include "proc_handles.h"
#include "proc_utils.h"


// Raised by Process.wait().
PyObject *TimeoutExpired;
PyObject *TimeoutAbandoned;


/*
 * Return 1 if PID exists in the current process list, else 0.
 */
PyObject *
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
PyObject *
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
PyObject *
psutil_proc_kill(PyObject *self, PyObject *args) {
    HANDLE hProcess;
    DWORD pid;
    DWORD access = PROCESS_TERMINATE | PROCESS_QUERY_LIMITED_INFORMATION;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (pid == 0)
        return AccessDenied("automatically set for PID 0");

    hProcess = psutil_handle_from_pid(pid, access);
    if (hProcess == NULL) {
        return NULL;
    }

    if (! TerminateProcess(hProcess, SIGTERM)) {
        // ERROR_ACCESS_DENIED may happen if the process already died. See:
        // https://github.com/giampaolo/psutil/issues/1099
        // http://bugs.python.org/issue14252
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
PyObject *
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
            PyErr_SetFromOSErrnoWithSyscall("OpenProcess");
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
PyObject *
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
            NoSuchProcess("GetProcessTimes -> ERROR_ACCESS_DENIED");
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
 * Return process executable path. Works for all processes regardless of
 * privilege. NtQuerySystemInformation has some sort of internal cache,
 * since it succeeds even when a process is gone (but not if a PID never
 * existed).
 */
PyObject *
psutil_proc_exe(PyObject *self, PyObject *args) {
    DWORD pid;
    NTSTATUS status;
    PVOID buffer = NULL;
    ULONG bufferSize = 0x104 * 2; // WIN_MAX_PATH * sizeof(wchar_t)
    SYSTEM_PROCESS_ID_INFORMATION processIdInfo;
    PyObject *py_exe;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    if (pid == 0)
        return AccessDenied("automatically set for PID 0");

    // ...because NtQuerySystemInformation can succeed for terminated
    // processes.
    if (psutil_pid_is_running(pid) == 0)
        return NoSuchProcess("psutil_pid_is_running -> 0");

    buffer = MALLOC_ZERO(bufferSize);
    if (! buffer) {
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
        NULL);

    if ((status == STATUS_INFO_LENGTH_MISMATCH) &&
            (processIdInfo.ImageName.MaximumLength <= bufferSize))
    {
        // Required length was NOT stored in MaximumLength (WOW64 issue).
        ULONG maxBufferSize = 0x7FFF * 2;  // NTFS_MAX_PATH * sizeof(wchar_t)
        do {
            // Iteratively double the size of the buffer up to maxBufferSize
            bufferSize *= 2;
            FREE(buffer);
            buffer = MALLOC_ZERO(bufferSize);
            if (! buffer) {
                PyErr_NoMemory();
                return NULL;
            }

            processIdInfo.ImageName.MaximumLength = (USHORT)bufferSize;
            processIdInfo.ImageName.Buffer = buffer;

            status = NtQuerySystemInformation(
                SystemProcessIdInformation,
                &processIdInfo,
                sizeof(SYSTEM_PROCESS_ID_INFORMATION),
                NULL);
        } while ((status == STATUS_INFO_LENGTH_MISMATCH) &&
                    (bufferSize <= maxBufferSize));
    }
    else if (status == STATUS_INFO_LENGTH_MISMATCH) {
        // Required length is stored in MaximumLength.
        FREE(buffer);
        buffer = MALLOC_ZERO(processIdInfo.ImageName.MaximumLength);
        if (! buffer) {
            PyErr_NoMemory();
            return NULL;
        }

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
            NoSuchProcess("psutil_pid_is_running -> 0");
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
PyObject *
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
            AccessDenied("NtQueryVirtualMemory -> STATUS_ACCESS_DENIED");
        }
        else if (psutil_pid_is_running(pid) == 0) {
            NoSuchProcess("psutil_pid_is_running -> 0");
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
PyObject *
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
 * Resume or suspends a process
 */
PyObject *
psutil_proc_suspend_or_resume(PyObject *self, PyObject *args) {
    DWORD pid;
    NTSTATUS status;
    HANDLE hProcess;
    DWORD access = PROCESS_SUSPEND_RESUME | PROCESS_QUERY_LIMITED_INFORMATION;
    PyObject* suspend;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID "O", &pid, &suspend))
        return NULL;

    hProcess = psutil_handle_from_pid(pid, access);
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


PyObject *
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
        AccessDenied("forced for PID 0");
        goto error;
    }

    pid_return = psutil_pid_is_running(pid);
    if (pid_return == 0) {
        NoSuchProcess("psutil_pid_is_running -> 0");
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


PyObject *
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


static PTOKEN_USER
_psutil_user_token_from_pid(DWORD pid) {
    HANDLE hProcess = NULL;
    HANDLE hToken = NULL;
    PTOKEN_USER userToken = NULL;
    ULONG bufferSize = 0x100;

    hProcess = psutil_handle_from_pid(pid, PROCESS_QUERY_LIMITED_INFORMATION);
    if (hProcess == NULL)
        return NULL;

    if (!OpenProcessToken(hProcess, TOKEN_QUERY, &hToken)) {
        PyErr_SetFromOSErrnoWithSyscall("OpenProcessToken");
        goto error;
    }

    // Get the user SID.
    while (1) {
        userToken = malloc(bufferSize);
        if (userToken == NULL) {
            PyErr_NoMemory();
            goto error;
        }
        if (!GetTokenInformation(hToken, TokenUser, userToken, bufferSize,
                                 &bufferSize))
        {
            if (GetLastError() == ERROR_INSUFFICIENT_BUFFER) {
                free(userToken);
                continue;
            }
            else {
                PyErr_SetFromOSErrnoWithSyscall("GetTokenInformation");
                goto error;
            }
        }
        break;
    }

    CloseHandle(hProcess);
    CloseHandle(hToken);
    return userToken;

error:
    if (hProcess != NULL)
        CloseHandle(hProcess);
    if (hToken != NULL)
        CloseHandle(hToken);
    return NULL;
}


/*
 * Return process username as a "DOMAIN//USERNAME" string.
 */
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

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    userToken = _psutil_user_token_from_pid(pid);
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
        if (!LookupAccountSidW(NULL, userToken->User.Sid, userName, &nameSize,
                               domainName, &domainNameSize, &nameUse))
        {
            if (GetLastError() == ERROR_INSUFFICIENT_BUFFER) {
                free(userName);
                free(domainName);
                continue;
            }
            else if (GetLastError() == ERROR_NONE_MAPPED) {
                // From MS doc:
                // https://docs.microsoft.com/en-us/windows/win32/api/winbase/
                //     nf-winbase-lookupaccountsida
                // If the function cannot find an account name for the SID,
                // GetLastError returns ERROR_NONE_MAPPED. This can occur if
                // a network time-out prevents the function from finding the
                // name. It also occurs for SIDs that have no corresponding
                // account name, such as a logon SID that identifies a logon
                // session.
                AccessDenied("LookupAccountSidW -> ERROR_NONE_MAPPED");
                goto error;
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
    py_username = PyUnicode_FromWideChar(userName, wcslen(userName));
    if (! py_username)
        goto error;
    py_tuple = Py_BuildValue("OO", py_domain, py_username);
    if (! py_tuple)
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


/*
 * Get process priority as a Python integer.
 */
PyObject *
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
PyObject *
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
PyObject *
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
PyObject *
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
PyObject *
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
PyObject *
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
PyObject *
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
PyObject *
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
 * Return the number of handles opened by process.
 */
PyObject *
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
PyObject *
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
