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

#include "../../arch/all/init.h"


// Return 1 if PID exists, 0 if not, -1 on error.
int
psutil_pid_in_pids(DWORD pid) {
    DWORD *pids_array = NULL;
    int pids_count = 0;
    int i;

    if (_psutil_pids(&pids_array, &pids_count) != 0)
        return -1;

    for (i = 0; i < pids_count; i++) {
        if (pids_array[i] == pid) {
            free(pids_array);
            return 1;
        }
    }

    free(pids_array);
    return 0;
}


// Given a process handle checks whether it's actually running. If it
// does return the handle, else return NULL with Python exception set.
// This is needed because OpenProcess API sucks.
HANDLE
psutil_check_phandle(HANDLE hProcess, DWORD pid, int check_exit_code) {
    DWORD exitCode;

    if (hProcess == NULL) {
        if (GetLastError() == ERROR_INVALID_PARAMETER) {
            // Yeah, this is the actual error code in case of
            // "no such process".
            NoSuchProcess("OpenProcess -> ERROR_INVALID_PARAMETER");
            return NULL;
        }
        if (GetLastError() == ERROR_SUCCESS) {
            // Yeah, it's this bad.
            // https://github.com/giampaolo/psutil/issues/1877
            if (psutil_pid_in_pids(pid) == 1) {
                psutil_debug("OpenProcess -> ERROR_SUCCESS turned into AD");
                AccessDenied("OpenProcess -> ERROR_SUCCESS");
            }
            else {
                psutil_debug("OpenProcess -> ERROR_SUCCESS turned into NSP");
                NoSuchProcess("OpenProcess -> ERROR_SUCCESS");
            }
            return NULL;
        }
        psutil_oserror_wsyscall("OpenProcess");
        return NULL;
    }

    if (check_exit_code == 0)
        return hProcess;

    if (GetExitCodeProcess(hProcess, &exitCode)) {
        // XXX - maybe STILL_ACTIVE is not fully reliable as per:
        // http://stackoverflow.com/questions/1591342/#comment47830782_1591379
        if (exitCode == STILL_ACTIVE) {
            return hProcess;
        }
        if (psutil_pid_in_pids(pid) == 1) {
            return hProcess;
        }
        CloseHandle(hProcess);
        NoSuchProcess("GetExitCodeProcess != STILL_ACTIVE");
        return NULL;
    }

    if (GetLastError() == ERROR_ACCESS_DENIED) {
        psutil_debug("GetExitCodeProcess -> ERROR_ACCESS_DENIED (ignored)");
        SetLastError(0);
        return hProcess;
    }
    psutil_oserror_wsyscall("GetExitCodeProcess");
    CloseHandle(hProcess);
    return NULL;
}


// A wrapper around OpenProcess setting NSP exception if process no
// longer exists. *pid* is the process PID, *access* is the first
// argument to OpenProcess.
// Return a process handle or NULL with exception set.
HANDLE
psutil_handle_from_pid(DWORD pid, DWORD access) {
    HANDLE hProcess;

    if (pid == 0) {
        // otherwise we'd get NoSuchProcess
        return AccessDenied("automatically set for PID 0");
    }

    hProcess = OpenProcess(access, FALSE, pid);

    if ((hProcess == NULL) && (GetLastError() == ERROR_ACCESS_DENIED)) {
        psutil_oserror_wsyscall("OpenProcess");
        return NULL;
    }

    hProcess = psutil_check_phandle(hProcess, pid, 1);
    return hProcess;
}


// Check for PID existence. Return 1 if pid exists, 0 if not, -1 on error.
int
psutil_pid_is_running(DWORD pid) {
    HANDLE hProcess;

    // Special case for PID 0 System Idle Process
    if (pid == 0)
        return 1;
    if (pid < 0)
        return 0;

    hProcess = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);

    if (hProcess != NULL) {
        hProcess = psutil_check_phandle(hProcess, pid, 1);
        if (hProcess != NULL) {
            CloseHandle(hProcess);
            return 1;
        }
        CloseHandle(hProcess);
    }

    PyErr_Clear();
    return psutil_pid_in_pids(pid);
}
