/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Security related functions for Windows platform (Set privileges such as
 * SeDebug), as well as security helper functions.
 */

#include <windows.h>
#include <Python.h>
#include "../../_psutil_common.h"


static BOOL
psutil_set_privilege(HANDLE hToken, LPCTSTR Privilege, BOOL bEnablePrivilege) {
    TOKEN_PRIVILEGES tp;
    LUID luid;
    TOKEN_PRIVILEGES tpPrevious;
    DWORD cbPrevious = sizeof(TOKEN_PRIVILEGES);

    if (! LookupPrivilegeValue(NULL, Privilege, &luid)) {
        PyErr_SetFromOSErrnoWithSyscall("LookupPrivilegeValue");
        return 1;
    }

    // first pass.  get current privilege setting
    tp.PrivilegeCount = 1;
    tp.Privileges[0].Luid = luid;
    tp.Privileges[0].Attributes = 0;

    if (! AdjustTokenPrivileges(
            hToken,
            FALSE,
            &tp,
            sizeof(TOKEN_PRIVILEGES),
            &tpPrevious,
            &cbPrevious))
    {
        PyErr_SetFromOSErrnoWithSyscall("AdjustTokenPrivileges");
        return 1;
    }

    // second pass. set privilege based on previous setting
    tpPrevious.PrivilegeCount = 1;
    tpPrevious.Privileges[0].Luid = luid;

    if (bEnablePrivilege)
        tpPrevious.Privileges[0].Attributes |= (SE_PRIVILEGE_ENABLED);
    else
        tpPrevious.Privileges[0].Attributes ^=
            (SE_PRIVILEGE_ENABLED & tpPrevious.Privileges[0].Attributes);

    if (! AdjustTokenPrivileges(
            hToken,
            FALSE,
            &tpPrevious,
            cbPrevious,
            NULL,
            NULL))
    {
        PyErr_SetFromOSErrnoWithSyscall("AdjustTokenPrivileges");
        return 1;
    }

    return 0;
}


static HANDLE
psutil_get_thisproc_token() {
    HANDLE hToken = NULL;
    HANDLE me = GetCurrentProcess();

    if (! OpenProcessToken(
            me, TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, &hToken))
    {
        if (GetLastError() == ERROR_NO_TOKEN)
        {
            if (! ImpersonateSelf(SecurityImpersonation)) {
                PyErr_SetFromOSErrnoWithSyscall("ImpersonateSelf");
                return NULL;
            }
            if (! OpenProcessToken(
                    me, TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, &hToken))
            {
                PyErr_SetFromOSErrnoWithSyscall("OpenProcessToken");
                return NULL;
            }
        }
        else {
            PyErr_SetFromOSErrnoWithSyscall("OpenProcessToken");
            return NULL;
        }
    }

    return hToken;
}


/*
 * Set this process in SE DEBUG mode so that we have more chances of
 * querying processes owned by other users, including many owned by
 * Administrator and Local System.
 * https://docs.microsoft.com/windows-hardware/drivers/debugger/debug-privilege
 */
int
psutil_set_se_debug() {
    HANDLE hToken;
    int err = 1;

    if ((hToken = psutil_get_thisproc_token()) == NULL)
        return 1;

    // enable SeDebugPrivilege (open any process)
    if (psutil_set_privilege(hToken, SE_DEBUG_NAME, TRUE) == 0)
        err = 0;

    RevertToSelf();
    CloseHandle(hToken);
    return err;
}
