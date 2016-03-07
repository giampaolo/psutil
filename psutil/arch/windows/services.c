/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>
#include <Winsvc.h>

#include "services.h"


// XXX - expose these as constants?
static const char *
get_startup_string(DWORD startup) {  // startup
    switch (startup) {
        case SERVICE_AUTO_START:
            return "automatic";
        case SERVICE_DEMAND_START:
            return "manual";
        case SERVICE_DISABLED:
            return "disabled";
/*
        // drivers only
        case SERVICE_BOOT_START:
            return "boot-start";
        case SERVICE_SYSTEM_START:
            return "system-start";
*/
        default:
            return "unknown";
    }
}


/*
 * Enumerate all services.
 */
PyObject *
psutil_winservice_enumerate(PyObject *self, PyObject *args) {
    ENUM_SERVICE_STATUS_PROCESS *lpService = NULL;
    SC_HANDLE sc = NULL;
    BOOL ok;
    DWORD bytesNeeded = 0;
    DWORD srvCount;
    DWORD resumeHandle = 0;
    DWORD dwBytes = 0;
    DWORD i;
    SC_HANDLE hService = NULL;
    QUERY_SERVICE_CONFIG *qsc = NULL;
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
        ok = EnumServicesStatusEx(
            sc,
            SC_ENUM_PROCESS_INFO,
            SERVICE_WIN32,  // XXX - extend this to include drivers etc.?
            SERVICE_STATE_ALL,
            (LPBYTE)lpService,
            dwBytes,
            &bytesNeeded,
            &srvCount,
            &resumeHandle,
            NULL);
        if (ok || (GetLastError() != ERROR_MORE_DATA))
            break;
        if (lpService)
            free(lpService);
        dwBytes = bytesNeeded;
        lpService = (ENUM_SERVICE_STATUS_PROCESS*)malloc(dwBytes);
    }

    for (i = 0; i < srvCount; i++) {
        // Get service handler.
        hService = OpenService(sc, lpService[i].lpServiceName,
                               SERVICE_QUERY_CONFIG);
        if (hService == NULL) {
            PyErr_SetFromWindowsErr(0);
            goto error;
        }

        // Query service config to get the binary path. First call to
        // QueryServiceConfig() is necessary to get the right size.
        bytesNeeded = 0;
        QueryServiceConfig(hService, NULL, 0, &bytesNeeded);
        if (GetLastError() != ERROR_INSUFFICIENT_BUFFER) {
            PyErr_SetFromWindowsErr(0);
            goto error;
        }
        qsc = (QUERY_SERVICE_CONFIG *)malloc(bytesNeeded);
        ok = QueryServiceConfig(hService, qsc, bytesNeeded, &bytesNeeded);
        if (ok == 0) {
            PyErr_SetFromWindowsErr(0);
            goto error;
        }

        // Construct the result.
        py_tuple = Py_BuildValue(
            "(ssiksss)",
            lpService[i].lpServiceName,  // name
            lpService[i].lpDisplayName,  // display_name
            lpService[i].ServiceStatusProcess.dwCurrentState,  // status
            lpService[i].ServiceStatusProcess.dwProcessId,  // pid
            // TODO: handle encoding errs
            qsc->lpBinaryPathName,  // binpath
            qsc->lpServiceStartName,  // username
            get_startup_string(qsc->dwStartType)  // startup
        );
        if (py_tuple == NULL)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_DECREF(py_tuple);

        // free stuff
        CloseServiceHandle(hService);
        free(qsc);
    }

    CloseServiceHandle(sc);
    free(lpService);
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    if (hService != NULL)
        CloseServiceHandle(hService);
    if (qsc != NULL)
        free(qsc);
    if (sc != NULL)
        CloseServiceHandle(sc);
    if (lpService != NULL)
        free(lpService);
    return NULL;
}


/*
 * Get service description.
 */
PyObject *
psutil_winservice_get_srv_descr(PyObject *self, PyObject *args) {
    ENUM_SERVICE_STATUS_PROCESS *lpService = NULL;
    SC_HANDLE sc = NULL;
    BOOL ok;
    DWORD bytesNeeded = 0;
    DWORD resumeHandle = 0;
    DWORD dwBytes = 0;
    SC_HANDLE hService = NULL;
    SERVICE_DESCRIPTION *scd = NULL;
    char *service_name;
    PyObject *py_retstr = NULL;

    if (!PyArg_ParseTuple(args, "s", &service_name))
        return NULL;

    sc = OpenSCManager(NULL, NULL, SC_MANAGER_ENUMERATE_SERVICE);
    if (sc == NULL) {
        PyErr_SetFromWindowsErr(0);
        return NULL;
    }

    hService = OpenService(sc, service_name, SERVICE_QUERY_CONFIG);
    if (hService == NULL) {
        PyErr_SetFromWindowsErr(0);
        goto error;
    }

    // This first call to QueryServiceConfig2() is necessary in order
    // to get the right size.
    bytesNeeded = 0;
    QueryServiceConfig2(hService, SERVICE_CONFIG_DESCRIPTION, NULL, 0,
                        &bytesNeeded);
    if (GetLastError() != ERROR_INSUFFICIENT_BUFFER) {
        PyErr_SetFromWindowsErr(0);
        goto error;
    }

    scd = (SERVICE_DESCRIPTION *)malloc(bytesNeeded);
    ok = QueryServiceConfig2(hService, SERVICE_CONFIG_DESCRIPTION,
                             (LPBYTE)scd, bytesNeeded, &bytesNeeded);
    if (ok == 0) {
        PyErr_SetFromWindowsErr(0);
        goto error;
    }

    // TODO: handle encoding errors.
    py_retstr = Py_BuildValue("s", scd->lpDescription);
    if (!py_retstr)
        goto error;

    CloseServiceHandle(sc);
    free(scd);
    return py_retstr;

error:
    if (hService != NULL)
        CloseServiceHandle(hService);
    if (sc != NULL)
        CloseServiceHandle(sc);
    if (lpService != NULL)
        free(lpService);
    return NULL;
}
