/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

/*
System related functions. Original code moved in here from
psutil/_psutil_windows.c in 2023. For reference, here's the GIT blame
history before the move:

* boot_time(): https://github.com/giampaolo/psutil/blame/efd7ed3/psutil/_psutil_windows.c#L51-L60
* users(): https://github.com/giampaolo/psutil/blame/efd7ed3/psutil/_psutil_windows.c#L1103-L1244
*/

#include <Python.h>
#include <windows.h>

#include "ntextapi.h"
#include "../../_psutil_common.h"


// Return a Python float representing the system uptime expressed in
// seconds since the epoch.
PyObject *
psutil_boot_time(PyObject *self, PyObject *args) {
    ULONGLONG upTime;
    FILETIME fileTime;

    GetSystemTimeAsFileTime(&fileTime);
    // Number of milliseconds that have elapsed since the system was started.
    upTime = GetTickCount64() / 1000ull;
    return Py_BuildValue("d", psutil_FiletimeToUnixTime(fileTime) - upTime);
}


PyObject *
psutil_users(PyObject *self, PyObject *args) {
    HANDLE hServer = WTS_CURRENT_SERVER_HANDLE;
    LPWSTR buffer_user = NULL;
    LPWSTR buffer_addr = NULL;
    LPWSTR buffer_info = NULL;
    PWTS_SESSION_INFOW sessions = NULL;
    DWORD count;
    DWORD i;
    DWORD sessionId;
    DWORD bytes;
    PWTS_CLIENT_ADDRESS address;
    char address_str[50];
    PWTSINFOW wts_info;
    PyObject *py_tuple = NULL;
    PyObject *py_address = NULL;
    PyObject *py_username = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;

    if (WTSEnumerateSessionsW == NULL ||
        WTSQuerySessionInformationW == NULL ||
        WTSFreeMemory == NULL) {
            // If we don't run in an environment that is a Remote Desktop Services environment
            // the Wtsapi32 proc might not be present.
            // https://docs.microsoft.com/en-us/windows/win32/termserv/run-time-linking-to-wtsapi32-dll
            return py_retlist;
    }

    if (WTSEnumerateSessionsW(hServer, 0, 1, &sessions, &count) == 0) {
        if (ERROR_CALL_NOT_IMPLEMENTED == GetLastError()) {
            // On Windows Nano server, the Wtsapi32 API can be present, but return WinError 120.
            return py_retlist;
        }
        PyErr_SetFromOSErrnoWithSyscall("WTSEnumerateSessionsW");
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
        if (buffer_info != NULL)
            WTSFreeMemory(buffer_info);

        buffer_user = NULL;
        buffer_addr = NULL;
        buffer_info = NULL;

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
        if (WTSQuerySessionInformationW(hServer, sessionId, WTSClientAddress,
                                        &buffer_addr, &bytes) == 0) {
            PyErr_SetFromOSErrnoWithSyscall("WTSQuerySessionInformationW");
            goto error;
        }

        address = (PWTS_CLIENT_ADDRESS)buffer_addr;
        if (address->AddressFamily == 2) {  // AF_INET == 2
            sprintf_s(address_str,
                      _countof(address_str),
                      "%u.%u.%u.%u",
                      // The IP address is offset by two bytes from the start of the Address member of the WTS_CLIENT_ADDRESS structure.
                      address->Address[2],
                      address->Address[3],
                      address->Address[4],
                      address->Address[5]);
            py_address = Py_BuildValue("s", address_str);
            if (!py_address)
                goto error;
        }
        else {
            Py_INCREF(Py_None);
            py_address = Py_None;
        }

        // login time
        bytes = 0;
        if (WTSQuerySessionInformationW(hServer, sessionId, WTSSessionInfo,
                                        &buffer_info, &bytes) == 0) {
            PyErr_SetFromOSErrnoWithSyscall("WTSQuerySessionInformationW");
            goto error;
        }
        wts_info = (PWTSINFOW)buffer_info;

        py_username = PyUnicode_FromWideChar(buffer_user, wcslen(buffer_user));
        if (py_username == NULL)
            goto error;

        py_tuple = Py_BuildValue(
            "OOd",
            py_username,
            py_address,
            psutil_LargeIntegerToUnixTime(wts_info->ConnectTime)
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
    WTSFreeMemory(buffer_info);
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
    if (buffer_info != NULL)
        WTSFreeMemory(buffer_info);
    return NULL;
}
