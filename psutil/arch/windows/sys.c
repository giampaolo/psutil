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
#include "../../arch/all/init.h"


// The number of seconds passed since boot. This is a monotonic timer,
// not affected by system clock updates. On Windows 7+ it also includes
// the time spent during suspend / hybernate.
PyObject *
psutil_uptime(PyObject *self, PyObject *args) {
    double uptimeSeconds;
    ULONGLONG interruptTime100ns = 0;

    if (QueryInterruptTime) {  // Windows 7+
        QueryInterruptTime(&interruptTime100ns);
        // Convert from 100-nanosecond to seconds.
        uptimeSeconds = interruptTime100ns / 10000000.0;
    }
    else {
        // Convert from milliseconds to seconds.
        uptimeSeconds = (double)GetTickCount64() / 1000.0;
    }
    return Py_BuildValue("d", uptimeSeconds);
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
        psutil_PyErr_SetFromOSErrnoWithSyscall("WTSEnumerateSessionsW");
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
            psutil_PyErr_SetFromOSErrnoWithSyscall(
                "WTSQuerySessionInformationW"
            );
            goto error;
        }
        if (bytes <= 2)
            continue;

        // address
        bytes = 0;
        if (WTSQuerySessionInformationW(hServer, sessionId, WTSClientAddress,
                                        &buffer_addr, &bytes) == 0) {
            psutil_PyErr_SetFromOSErrnoWithSyscall(
                "WTSQuerySessionInformationW"
            );
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
            psutil_PyErr_SetFromOSErrnoWithSyscall(
                "WTSQuerySessionInformationW"
            );
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


/*
 * Converts a DOS path name to an NT path name
 */
PyObject *
psutil_RtlDosPathNameToNtPathName(PyObject *self, PyObject *args) {
    PyObject *py_dospath;
    wchar_t *dospath;
    UNICODE_STRING ntpath;
    NTSTATUS status;

    if (RtlDosPathNameToNtPathName_U_WithStatus == NULL) {
        psutil_debug("RtlDosPathNameToNtPathName_U_WithStatus not found");
        Py_RETURN_NONE;
    }

    if (!PyArg_ParseTuple(args, "U", &py_dospath))
        return NULL;

    dospath = PyUnicode_AsWideCharString(py_dospath, NULL);

    if (dospath == NULL)
        return NULL;

    memset(&ntpath, 0, sizeof(ntpath));

    status = RtlDosPathNameToNtPathName_U_WithStatus(
        dospath, &ntpath, NULL, NULL);

    if (!NT_SUCCESS(status)) {
        psutil_SetFromNTStatusErr(
            status, "RtlDosPathNameToNtPathName_U_WithStatus");

        PyMem_Free(dospath);
        return NULL;
    }

    PyMem_Free(dospath);

    return PyUnicode_FromWideChar(ntpath.Buffer, ntpath.Length / 2);
}


/*
 * Opens a DOS or NT path and returns the resolved name
 */
PyObject *
psutil_GetFinalPathName(PyObject *self, PyObject *args, PyObject *kwargs) {
    PyObject *py_path;
    wchar_t *path;
    wchar_t *retpath = NULL;
    int retpathlen;
    int to_nt_path = 0;
    int from_nt_path = 0;
    DWORD flags;
    HANDLE hFile;
    NTSTATUS status;
    UNICODE_STRING nt_path;
    OBJECT_ATTRIBUTES objattr;
    IO_STATUS_BLOCK iosb;
    PyObject *py_retpath = NULL;
    ULONG err;

    char *keywords[4] = {"path", "from_nt", "to_nt", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "U|pp", keywords,
                                     &py_path, &from_nt_path, &to_nt_path))
        return NULL;

    flags = to_nt_path ? VOLUME_NAME_NT : VOLUME_NAME_DOS;

    path = PyUnicode_AsWideCharString(py_path, NULL);

    if (path == NULL)
        return NULL;

    if (from_nt_path) {
        if (NtOpenFile == NULL) {
            psutil_debug("NtOpenFile not found");
            py_retpath = Py_None;
            goto error;
        }

        nt_path.Buffer = path;
        nt_path.Length = (USHORT)(wcslen(path) * sizeof(wchar_t));
        nt_path.MaximumLength = nt_path.Length;
        InitializeObjectAttributes(&objattr, &nt_path, 0, NULL, NULL);

        status = NtOpenFile(
            &hFile, FILE_READ_ATTRIBUTES, &objattr, &iosb,
            FILE_SHARE_READ | FILE_SHARE_WRITE, 0);

        if (!NT_SUCCESS(status)) {
            if (NT_NTWIN32(status)) {
                err = WIN32_FROM_NTSTATUS(status);
            } else {
                err = RtlNtStatusToDosErrorNoTeb(status);
            }

            PyErr_SetExcFromWindowsErrWithFilenameObject(PyExc_OSError, err, py_path);
            goto error;
        }
    } else {
        hFile = CreateFileW(
            path, FILE_READ_ATTRIBUTES,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            NULL, OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS, NULL);

        if (hFile == INVALID_HANDLE_VALUE) {
            PyErr_SetExcFromWindowsErrWithFilenameObject(PyExc_OSError, 0, py_path);
            goto error;
        }
    }

    retpathlen = GetFinalPathNameByHandleW(hFile, NULL, 0, flags);

    retpath = MALLOC_ZERO(retpathlen * sizeof(wchar_t) * 2);

    if (!retpath) {
        PyErr_NoMemory();
        goto error;
    }

    retpathlen = GetFinalPathNameByHandleW(hFile, retpath, retpathlen * 2, flags);

    CloseHandle(hFile);
    PyMem_Free(path);

    py_retpath = PyUnicode_FromWideChar(retpath, retpathlen);

    FREE(retpath);

    return py_retpath;

error:
    PyMem_Free(path);
    return py_retpath;
}
