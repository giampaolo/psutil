/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>
#include <Winsvc.h>

#include "services.h"


/*
 * Enumerate all services.
 */
PyObject *
psutil_winservice_enumerate(PyObject *self, PyObject *args) {
    ENUM_SERVICE_STATUS *lpService = NULL;
    SC_HANDLE sc = NULL;
    BOOL ok;
    DWORD bytesNeeded = 0;
    DWORD srvCount;
    DWORD resumeHandle = 0;
    DWORD dwBytes = 0;
    DWORD i;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;

    if (py_retlist == NULL)
        return NULL;

    sc = OpenSCManager(NULL, NULL, SC_MANAGER_ENUMERATE_SERVICE);
    if (sc == NULL) {
        PyErr_SetFromWindowsErr(0);
        return NULL;
    }

    for (;;) {
        ok = EnumServicesStatus(
            sc, SERVICE_WIN32, SERVICE_STATE_ALL, lpService, dwBytes,
            &bytesNeeded, &srvCount, &resumeHandle);
        if (ok || (GetLastError() != ERROR_MORE_DATA))
            break;
        if (lpService)
            free(lpService);
        dwBytes = bytesNeeded;
        lpService = (ENUM_SERVICE_STATUS*)malloc(dwBytes);
    }

    for (i = 0; i < srvCount; i++) {
        py_tuple = Py_BuildValue(
            "(ssi)",
            lpService[i].lpServiceName,  // name
            lpService[i].lpDisplayName,  // display name
            lpService[i].ServiceStatus.dwCurrentState  // status
        );
        if (py_tuple == NULL)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_DECREF(py_tuple);
    }

    CloseServiceHandle(sc);
    free(lpService);
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    if (sc != NULL)
        CloseServiceHandle(sc);
    if (lpService != NULL)
        free(lpService);
    return NULL;
}
