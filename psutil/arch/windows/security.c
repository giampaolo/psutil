/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// Security related functions for Windows platform (Set privileges such
// as SE DEBUG).

#include <Python.h>
#include <windows.h>

#include "../../arch/all/init.h"


// Enable or disable `Privilege` on `hToken`. Return 0 on success, else
// the Win32 error code.
static DWORD
psutil_set_privilege(HANDLE hToken, LPCTSTR Privilege, BOOL bEnablePrivilege) {
    TOKEN_PRIVILEGES tp;
    LUID luid;
    // Zeroed because AdjustTokenPrivileges() leaves Privileges[0]
    // untouched when the token doesn't hold the privilege, and we OR
    // into its Attributes below.
    TOKEN_PRIVILEGES tpPrevious = {0};
    DWORD cbPrevious = sizeof(TOKEN_PRIVILEGES);

    if (!LookupPrivilegeValue(NULL, Privilege, &luid)) {
        psutil_debug("LookupPrivilegeValue() failed");
        return GetLastError();
    }

    // first pass.  get current privilege setting
    tp.PrivilegeCount = 1;
    tp.Privileges[0].Luid = luid;
    tp.Privileges[0].Attributes = 0;

    if (!AdjustTokenPrivileges(
            hToken,
            FALSE,
            &tp,
            sizeof(TOKEN_PRIVILEGES),
            &tpPrevious,
            &cbPrevious
        ))
    {
        psutil_debug("AdjustTokenPrivileges() failed (1/2)");
        return GetLastError();
    }

    // Second pass. Set privilege based on previous setting.
    tpPrevious.PrivilegeCount = 1;
    tpPrevious.Privileges[0].Luid = luid;

    if (bEnablePrivilege)
        tpPrevious.Privileges[0].Attributes |= (SE_PRIVILEGE_ENABLED);
    else
        tpPrevious.Privileges[0].Attributes ^=
            (SE_PRIVILEGE_ENABLED & tpPrevious.Privileges[0].Attributes);

    if (!AdjustTokenPrivileges(
            hToken, FALSE, &tpPrevious, cbPrevious, NULL, NULL
        ))
    {
        psutil_debug("AdjustTokenPrivileges() failed (2/2)");
        return GetLastError();
    }

    return 0;
}


// Return the token of the current process, or NULL, in which case
// `err` is set to the Win32 error code.
static HANDLE
psutil_get_thisproc_token(DWORD *err) {
    HANDLE hToken = NULL;
    HANDLE me = GetCurrentProcess();

    if (!OpenProcessToken(me, TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, &hToken))
    {
        // ERROR_NO_TOKEN means "the thread is not impersonating", which
        // is an OpenThreadToken condition. A process always has a
        // primary token, so this branch is likely unreachable.
        if (GetLastError() == ERROR_NO_TOKEN) {
            if (!ImpersonateSelf(SecurityImpersonation)) {
                psutil_debug("ImpersonateSelf() failed");
                *err = GetLastError();
                return NULL;
            }
            if (!OpenProcessToken(
                    me, TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, &hToken
                ))
            {
                psutil_debug("OpenProcessToken() failed");
                *err = GetLastError();
                RevertToSelf();
                return NULL;
            }
        }
        else {
            psutil_debug("OpenProcessToken() failed");
            *err = GetLastError();
            return NULL;
        }
    }

    return hToken;
}


static void
psutil_warn(DWORD err) {
    char *msg =
        "psutil module couldn't set SE DEBUG mode for this process; "
        "please file an issue against psutil bug tracker";

    psutil_debug("%s (err=%lu)", msg, (unsigned long)err);
    if (err != ERROR_ACCESS_DENIED) {
        if (PyErr_WarnEx(PyExc_RuntimeWarning, msg, 1) != 0)
            PyErr_Clear();  // -W error: we don't want to fail on import
    }
}


// Set this process in SE DEBUG mode so that we have more chances of
// querying processes owned by other users, including many owned by
// Administrator and Local System.
// https://docs.microsoft.com/windows-hardware/drivers/debugger/debug-privilege
// This is executed on module import and we don't crash on error.
int
psutil_set_se_debug() {
    HANDLE hToken;
    DWORD err = 0;

    if ((hToken = psutil_get_thisproc_token(&err)) == NULL) {
        psutil_warn(err);
        return 0;
    }

    err = psutil_set_privilege(hToken, SE_DEBUG_NAME, TRUE);
    if (err != 0)
        psutil_warn(err);

    RevertToSelf();  // in case psutil_get_thisproc_token() impersonated
    CloseHandle(hToken);
    return 0;
}
