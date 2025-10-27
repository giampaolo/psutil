/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>
#include <Winsvc.h>

#include "../../arch/all/init.h"


// ==================================================================
// utils
// ==================================================================


SC_HANDLE
psutil_get_service_handler(
    const wchar_t *service_name, DWORD scm_access, DWORD access
) {
    SC_HANDLE sc = NULL;
    SC_HANDLE hService = NULL;

    sc = OpenSCManagerW(NULL, NULL, scm_access);
    if (sc == NULL) {
        psutil_oserror_wsyscall("OpenSCManagerW");
        return NULL;
    }

    hService = OpenServiceW(sc, service_name, access);
    if (hService == NULL) {
        psutil_oserror_wsyscall("OpenServiceW");
        CloseServiceHandle(sc);
        return NULL;
    }

    CloseServiceHandle(sc);
    return hService;
}


// helper: parse args, convert to wchar, and open service
// returns NULL on error. On success, fills *service_name_out.
static SC_HANDLE
psutil_get_service_from_args(
    PyObject *args, DWORD scm_access, DWORD access, wchar_t **service_name_out
) {
    PyObject *py_service_name = NULL;
    wchar_t *service_name = NULL;
    Py_ssize_t wlen;
    SC_HANDLE hService = NULL;

    if (!PyArg_ParseTuple(args, "U", &py_service_name)) {
        return NULL;
    }

    service_name = PyUnicode_AsWideCharString(py_service_name, &wlen);
    if (service_name == NULL) {
        return NULL;
    }

    hService = psutil_get_service_handler(service_name, scm_access, access);
    if (hService == NULL) {
        PyMem_Free(service_name);
        return NULL;
    }

    *service_name_out = service_name;
    return hService;
}


// XXX - expose these as constants?
static const char *
get_startup_string(DWORD startup) {
    switch (startup) {
        case SERVICE_AUTO_START:
            return "automatic";
        case SERVICE_DEMAND_START:
            return "manual";
        case SERVICE_DISABLED:
            return "disabled";
        // drivers only (since we use EnumServicesStatusEx() with
        // SERVICE_WIN32)
        // case SERVICE_BOOT_START:
        //     return "boot-start";
        // case SERVICE_SYSTEM_START:
        //     return "system-start";
        default:
            return "unknown";
    }
}


// XXX - expose these as constants?
static const char *
get_state_string(DWORD state) {
    switch (state) {
        case SERVICE_RUNNING:
            return "running";
        case SERVICE_PAUSED:
            return "paused";
        case SERVICE_START_PENDING:
            return "start_pending";
        case SERVICE_PAUSE_PENDING:
            return "pause_pending";
        case SERVICE_CONTINUE_PENDING:
            return "continue_pending";
        case SERVICE_STOP_PENDING:
            return "stop_pending";
        case SERVICE_STOPPED:
            return "stopped";
        default:
            return "unknown";
    }
}


// ==================================================================
// APIs
// ==================================================================

/*
 * Enumerate all services.
 */
PyObject *
psutil_winservice_enumerate(PyObject *self, PyObject *args) {
    ENUM_SERVICE_STATUS_PROCESSW *lpService = NULL;
    BOOL ok;
    SC_HANDLE sc = NULL;
    DWORD bytesNeeded = 0;
    DWORD srvCount;
    DWORD resumeHandle = 0;
    DWORD dwBytes = 0;
    DWORD i;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;
    PyObject *py_name = NULL;
    PyObject *py_display_name = NULL;

    if (py_retlist == NULL)
        return NULL;

    sc = OpenSCManager(NULL, NULL, SC_MANAGER_ENUMERATE_SERVICE);
    if (sc == NULL) {
        psutil_oserror_wsyscall("OpenSCManager");
        return NULL;
    }

    for (;;) {
        ok = EnumServicesStatusExW(
            sc,
            SC_ENUM_PROCESS_INFO,
            SERVICE_WIN32,  // XXX - extend this to include drivers etc.?
            SERVICE_STATE_ALL,
            (LPBYTE)lpService,
            dwBytes,
            &bytesNeeded,
            &srvCount,
            &resumeHandle,
            NULL
        );
        if (ok || (GetLastError() != ERROR_MORE_DATA))
            break;
        if (lpService)
            free(lpService);
        dwBytes = bytesNeeded;
        lpService = (ENUM_SERVICE_STATUS_PROCESSW *)malloc(dwBytes);
    }

    for (i = 0; i < srvCount; i++) {
        // Get unicode name / display name.
        py_name = NULL;
        py_name = PyUnicode_FromWideChar(
            lpService[i].lpServiceName, wcslen(lpService[i].lpServiceName)
        );
        if (py_name == NULL)
            goto error;

        py_display_name = NULL;
        py_display_name = PyUnicode_FromWideChar(
            lpService[i].lpDisplayName, wcslen(lpService[i].lpDisplayName)
        );
        if (py_display_name == NULL)
            goto error;

        // Construct the result.
        py_tuple = Py_BuildValue("(OO)", py_name, py_display_name);
        if (py_tuple == NULL)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_DECREF(py_display_name);
        Py_DECREF(py_name);
        Py_DECREF(py_tuple);
    }

    // Free resources.
    CloseServiceHandle(sc);
    free(lpService);
    return py_retlist;

error:
    Py_DECREF(py_name);
    Py_XDECREF(py_display_name);
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    if (sc != NULL)
        CloseServiceHandle(sc);
    if (lpService != NULL)
        free(lpService);
    return NULL;
}


/*
 * Get service config information. Returns:
 * - display_name
 * - binpath
 * - username
 * - startup_type
 */
PyObject *
psutil_winservice_query_config(PyObject *self, PyObject *args) {
    wchar_t *service_name = NULL;
    SC_HANDLE hService = NULL;
    BOOL ok;
    DWORD bytesNeeded = 0;
    QUERY_SERVICE_CONFIGW *qsc = NULL;
    PyObject *py_tuple = NULL;
    PyObject *py_unicode_display_name = NULL;
    PyObject *py_unicode_binpath = NULL;
    PyObject *py_unicode_username = NULL;

    hService = psutil_get_service_from_args(
        args, SC_MANAGER_ENUMERATE_SERVICE, SERVICE_QUERY_CONFIG, &service_name
    );
    if (hService == NULL)
        return NULL;

    // First call to QueryServiceConfigW() is necessary to get the
    // right size.
    bytesNeeded = 0;
    QueryServiceConfigW(hService, NULL, 0, &bytesNeeded);
    if (GetLastError() != ERROR_INSUFFICIENT_BUFFER) {
        psutil_oserror_wsyscall("QueryServiceConfigW");
        goto error;
    }

    qsc = (QUERY_SERVICE_CONFIGW *)malloc(bytesNeeded);
    if (qsc == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    ok = QueryServiceConfigW(hService, qsc, bytesNeeded, &bytesNeeded);
    if (!ok) {
        psutil_oserror_wsyscall("QueryServiceConfigW");
        goto error;
    }

    // Get unicode display name.
    py_unicode_display_name = PyUnicode_FromWideChar(
        qsc->lpDisplayName, wcslen(qsc->lpDisplayName)
    );
    if (py_unicode_display_name == NULL)
        goto error;

    // Get unicode bin path.
    py_unicode_binpath = PyUnicode_FromWideChar(
        qsc->lpBinaryPathName, wcslen(qsc->lpBinaryPathName)
    );
    if (py_unicode_binpath == NULL)
        goto error;

    // Get unicode username.
    py_unicode_username = PyUnicode_FromWideChar(
        qsc->lpServiceStartName, wcslen(qsc->lpServiceStartName)
    );
    if (py_unicode_username == NULL)
        goto error;

    // Construct result tuple.
    py_tuple = Py_BuildValue(
        "(OOOs)",
        py_unicode_display_name,
        py_unicode_binpath,
        py_unicode_username,
        get_startup_string(qsc->dwStartType)  // startup
    );
    if (py_tuple == NULL)
        goto error;

    // Free resources.
    Py_DECREF(py_unicode_display_name);
    Py_DECREF(py_unicode_binpath);
    Py_DECREF(py_unicode_username);
    free(qsc);
    CloseServiceHandle(hService);
    PyMem_Free(service_name);
    return py_tuple;

error:
    Py_XDECREF(py_unicode_display_name);
    Py_XDECREF(py_unicode_binpath);
    Py_XDECREF(py_unicode_username);
    Py_XDECREF(py_tuple);
    if (hService)
        CloseServiceHandle(hService);
    if (qsc)
        free(qsc);
    if (service_name)
        PyMem_Free(service_name);
    return NULL;
}


/*
 * Get service status information. Returns:
 * - status
 * - pid
 */
PyObject *
psutil_winservice_query_status(PyObject *self, PyObject *args) {
    wchar_t *service_name = NULL;
    SC_HANDLE hService = NULL;
    BOOL ok;
    DWORD bytesNeeded = 0;
    SERVICE_STATUS_PROCESS *ssp = NULL;
    PyObject *py_tuple = NULL;

    hService = psutil_get_service_from_args(
        args, SC_MANAGER_ENUMERATE_SERVICE, SERVICE_QUERY_STATUS, &service_name
    );
    if (hService == NULL)
        return NULL;

    // First call to QueryServiceStatusEx() is necessary to get the
    // right size.
    QueryServiceStatusEx(
        hService, SC_STATUS_PROCESS_INFO, NULL, 0, &bytesNeeded
    );
    if (GetLastError() == ERROR_MUI_FILE_NOT_FOUND) {
        // Also services.msc fails in the same manner, so we return an
        // empty string.
        CloseServiceHandle(hService);
        PyMem_Free(service_name);
        return Py_BuildValue("s", "");
    }
    if (GetLastError() != ERROR_INSUFFICIENT_BUFFER) {
        psutil_oserror_wsyscall("QueryServiceStatusEx");
        goto error;
    }

    ssp = (SERVICE_STATUS_PROCESS *)HeapAlloc(
        GetProcessHeap(), 0, bytesNeeded
    );
    if (ssp == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    // Actual call.
    ok = QueryServiceStatusEx(
        hService,
        SC_STATUS_PROCESS_INFO,
        (LPBYTE)ssp,
        bytesNeeded,
        &bytesNeeded
    );
    if (!ok) {
        psutil_oserror_wsyscall("QueryServiceStatusEx");
        goto error;
    }

    py_tuple = Py_BuildValue(
        "(sk)", get_state_string(ssp->dwCurrentState), ssp->dwProcessId
    );
    if (py_tuple == NULL)
        goto error;

    CloseServiceHandle(hService);
    HeapFree(GetProcessHeap(), 0, ssp);
    PyMem_Free(service_name);
    return py_tuple;

error:
    Py_XDECREF(py_tuple);
    if (hService)
        CloseServiceHandle(hService);
    if (ssp)
        HeapFree(GetProcessHeap(), 0, ssp);
    if (service_name)
        PyMem_Free(service_name);
    return NULL;
}

PyObject *
psutil_winservice_query_descr(PyObject *self, PyObject *args) {
    BOOL ok;
    DWORD bytesNeeded = 0;
    SC_HANDLE hService = NULL;
    SERVICE_DESCRIPTIONW *scd = NULL;
    wchar_t *service_name = NULL;
    PyObject *py_retstr = NULL;

    hService = psutil_get_service_from_args(
        args, SC_MANAGER_ENUMERATE_SERVICE, SERVICE_QUERY_CONFIG, &service_name
    );
    if (hService == NULL)
        return NULL;

    QueryServiceConfig2W(
        hService, SERVICE_CONFIG_DESCRIPTION, NULL, 0, &bytesNeeded
    );

    if ((GetLastError() == ERROR_NOT_FOUND)
        || (GetLastError() == ERROR_MUI_FILE_NOT_FOUND))
    {
        // E.g. services.msc fails in this manner, so we return an
        // empty string.
        psutil_debug("set empty string for NOT_FOUND service description");
        CloseServiceHandle(hService);
        PyMem_Free(service_name);
        return Py_BuildValue("s", "");
    }

    if (GetLastError() != ERROR_INSUFFICIENT_BUFFER) {
        psutil_oserror_wsyscall("QueryServiceConfig2W");
        goto error;
    }

    scd = (SERVICE_DESCRIPTIONW *)malloc(bytesNeeded);
    if (scd == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    ok = QueryServiceConfig2W(
        hService,
        SERVICE_CONFIG_DESCRIPTION,
        (LPBYTE)scd,
        bytesNeeded,
        &bytesNeeded
    );
    if (!ok) {
        psutil_oserror_wsyscall("QueryServiceConfig2W");
        goto error;
    }

    if (scd->lpDescription == NULL) {
        py_retstr = Py_BuildValue("s", "");
    }
    else {
        py_retstr = PyUnicode_FromWideChar(
            scd->lpDescription, wcslen(scd->lpDescription)
        );
    }

    if (!py_retstr)
        goto error;

    free(scd);
    CloseServiceHandle(hService);
    PyMem_Free(service_name);
    return py_retstr;

error:
    if (hService)
        CloseServiceHandle(hService);
    if (scd)
        free(scd);
    if (service_name)
        PyMem_Free(service_name);
    return NULL;
}


/*
 * Start service.
 * XXX - note: this is exposed but not used.
 */
PyObject *
psutil_winservice_start(PyObject *self, PyObject *args) {
    BOOL ok;
    SC_HANDLE hService = NULL;
    wchar_t *service_name = NULL;

    hService = psutil_get_service_from_args(
        args, SC_MANAGER_ALL_ACCESS, SERVICE_START, &service_name
    );
    if (hService == NULL)
        return NULL;

    ok = StartService(hService, 0, NULL);
    if (!ok) {
        psutil_oserror_wsyscall("StartService");
        goto error;
    }

    CloseServiceHandle(hService);
    PyMem_Free(service_name);
    Py_RETURN_NONE;

error:
    if (hService)
        CloseServiceHandle(hService);
    if (service_name)
        PyMem_Free(service_name);
    return NULL;
}


/*
 * Stop service.
 * XXX - note: this is exposed but not used.
 */
PyObject *
psutil_winservice_stop(PyObject *self, PyObject *args) {
    wchar_t *service_name = NULL;
    BOOL ok;
    SC_HANDLE hService = NULL;
    SERVICE_STATUS ssp;

    hService = psutil_get_service_from_args(
        args, SC_MANAGER_ALL_ACCESS, SERVICE_STOP, &service_name
    );
    if (hService == NULL)
        return NULL;

    // Note: this can hang for 30 secs.
    Py_BEGIN_ALLOW_THREADS
    ok = ControlService(hService, SERVICE_CONTROL_STOP, &ssp);
    Py_END_ALLOW_THREADS
    if (!ok) {
        psutil_oserror_wsyscall("ControlService");
        goto error;
    }

    CloseServiceHandle(hService);
    PyMem_Free(service_name);
    Py_RETURN_NONE;

error:
    if (hService)
        CloseServiceHandle(hService);
    if (service_name)
        PyMem_Free(service_name);
    return NULL;
}
