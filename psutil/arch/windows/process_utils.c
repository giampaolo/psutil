/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Helper process functions.
 */

#include <Python.h>
#include <windows.h>
#include <Psapi.h>  // EnumProcesses

#include "../../_psutil_common.h"
#include "process_utils.h"


DWORD *
psutil_get_pids(DWORD *numberOfReturnedPIDs) {
    // Win32 SDK says the only way to know if our process array
    // wasn't large enough is to check the returned size and make
    // sure that it doesn't match the size of the array.
    // If it does we allocate a larger array and try again

    // Stores the actual array
    DWORD *procArray = NULL;
    DWORD procArrayByteSz;
    int procArraySz = 0;

    // Stores the byte size of the returned array from enumprocesses
    DWORD enumReturnSz = 0;

    do {
        procArraySz += 1024;
        if (procArray != NULL)
            free(procArray);
        procArrayByteSz = procArraySz * sizeof(DWORD);
        procArray = malloc(procArrayByteSz);
        if (procArray == NULL) {
            PyErr_NoMemory();
            return NULL;
        }
        if (! EnumProcesses(procArray, procArrayByteSz, &enumReturnSz)) {
            free(procArray);
            PyErr_SetFromWindowsErr(0);
            return NULL;
        }
    } while (enumReturnSz == procArraySz * sizeof(DWORD));

    // The number of elements is the returned size / size of each element
    *numberOfReturnedPIDs = enumReturnSz / sizeof(DWORD);

    return procArray;
}

/*
 * Return 1 if PID exists, 0 if not, -1 on error.
 */
int
psutil_pid_in_pids(DWORD pid) {
    DWORD *proclist = NULL;
    DWORD numberOfReturnedPIDs;
    DWORD i;

    proclist = psutil_get_pids(&numberOfReturnedPIDs);
    if (proclist == NULL)
        return -1;
    for (i = 0; i < numberOfReturnedPIDs; i++) {
        if (proclist[i] == pid) {
            free(proclist);
            return 1;
        }
    }
    free(proclist);
    return 0;
}


/*
 * Given a process handle checks whether it's actually running. If it
 * does return the handle, else return NULL with Python exception set.
 * Process handle must have SYNCHRONIZE access right.
 * This is needed because OpenProcess API sucks.
 */
HANDLE
psutil_check_phandle(HANDLE hProcess, DWORD pid) {
    DWORD ret;

    if (hProcess == NULL) {
        if (GetLastError() == ERROR_INVALID_PARAMETER) {
            // Yeah, this is the actual error code in case of
            // "no such process".
            NoSuchProcess("OpenProcess");
            return NULL;
        }
        PyErr_SetFromOSErrnoWithSyscall("OpenProcess");
        return NULL;
    }

    ret = WaitForSingleObject(hProcess, 0);
    switch (ret) {
        case WAIT_TIMEOUT:
            // process still running
            return hProcess;
        case WAIT_OBJECT_0:
            // process has exited
            CloseHandle(hProcess);
            NoSuchProcess("WaitForSingleObject");
            return NULL;
        case WAIT_ABANDONED:
            // Should never happen. We don't know so we look into pids.
            psutil_debug("WaitForSingleObject -> WAIT_ABANDONED (unexpected)");
            if (psutil_pid_in_pids(pid) == 1)
                return hProcess;
            CloseHandle(hProcess);
            NoSuchProcess("WaitForSingleObject -> WAIT_ABANDONED");
            return NULL;
        default:  // WAIT_FAILED
            PyErr_SetFromOSErrnoWithSyscall("WaitForSingleObject");
            CloseHandle(hProcess);
            return NULL;
    }
}


/*
 * A wrapper around OpenProcess setting NSP exception if process no
 * longer exists. *pid* is the process PID, dwDesiredAccess" is the
 * first argument to OpenProcess.
 * Return a process handle or NULL with exception set.
 */
HANDLE
psutil_handle_from_pid(DWORD pid, DWORD access) {
    HANDLE hProcess;

    if (pid == 0) {
        // otherwise we'd get NoSuchProcess
        return AccessDenied("automatically set for PID 0");
    }

    // Needed for WaitForSingleObject. This does not require more
    // privileges and should be the same as PROCESS_QUERY_LIMITED_INFORMATION
    // (tested with "make print-access-denied").
    access |= SYNCHRONIZE;
    hProcess = OpenProcess(access, FALSE, pid);

    if ((hProcess == NULL) && (GetLastError() == ERROR_ACCESS_DENIED)) {
        PyErr_SetFromOSErrnoWithSyscall("OpenProcess");
        return NULL;
    }

    hProcess = psutil_check_phandle(hProcess, pid);

    if (PSUTIL_TESTING) {
        // XXX: racy
        if (hProcess == NULL) {
            if (psutil_pid_in_pids(pid) == 1) {
                PyErr_SetString(PyExc_AssertionError,
                                "OpenProcess failed but PID exists");
                return NULL;
            }
        }
        else {
            if (psutil_pid_in_pids(pid) == 0) {
                PyErr_SetString(PyExc_AssertionError,
                                "OpenProcess succeeded but PID doesn't exist");
                return NULL;
            }
        }
    }
    return hProcess;
}


/*
/* Check for PID existance by using OpenProcess() + WaitForSingleObject.
/* Return 1 if pid exists else 0.
 */
int
psutil_pid_is_running(DWORD pid) {
    HANDLE hProcess;

    // Special case for PID 0 System Idle Process
    if (pid == 0)
        return 1;
    if (pid < 0)
        return 0;

    hProcess = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE,
                           FALSE, pid);

    // Access denied means there's a process to deny access to.
    if ((hProcess == NULL) && (GetLastError() == ERROR_ACCESS_DENIED))
        return 1;

    hProcess = psutil_check_phandle(hProcess, pid);
    if (hProcess == NULL) {
        PyErr_Clear();
        SetLastError(0);
        return 0;
    }
    else {
        CloseHandle(hProcess);
        return 1;
    }
}
