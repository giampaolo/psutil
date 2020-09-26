/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>
#include <wlanapi.h>
#include <objbase.h>
#include <wtypes.h>

#include "../../_psutil_common.h"


/*
 * Return a Python list of named tuples with overall network I/O information
 */
PyObject *
psutil_wifi_cards(PyObject *self, PyObject *args) {
    HANDLE hClient = NULL;
    DWORD dwMaxClient = 2;   //
    DWORD dwCurVersion = 0;
    DWORD dwResult = 0;
    int iRet = 0;
    WCHAR GuidString[40] = {0};
    int i;
    char *status;
    PWLAN_INTERFACE_INFO_LIST pIfList = NULL;
    PWLAN_INTERFACE_INFO pIfInfo = NULL;

    PyObject *py_tuple = NULL;
    PyObject *py_guid = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;

    dwResult = WlanOpenHandle(dwMaxClient, NULL, &dwCurVersion, &hClient);
    if (dwResult != ERROR_SUCCESS)  {
        PyErr_SetFromOSErrnoWithSyscall("WlanOpenHandle");
        return NULL;
    }

    dwResult = WlanEnumInterfaces(hClient, NULL, &pIfList);
    if (dwResult != ERROR_SUCCESS)  {
        PyErr_SetFromOSErrnoWithSyscall("WlanEnumInterfaces");
        goto error;
    }

    for (i = 0; i < (int) pIfList->dwNumberOfItems; i++) {
        pIfInfo = (WLAN_INTERFACE_INFO *) &pIfList->InterfaceInfo[i];
        iRet = StringFromGUID2(
            &pIfInfo->InterfaceGuid, (LPOLESTR) &GuidString, 39);
        if (iRet == 0) {
            PyErr_Format(PyExc_RuntimeError, "StringFromGUID2 syscall failed");
            goto error;
        }

        switch (pIfInfo->isState) {
            case wlan_interface_state_not_ready:
                status = "not_ready";
                break;
            case wlan_interface_state_connected:
                status = "connected";
                break;
            case wlan_interface_state_ad_hoc_network_formed:
                status = "ad_hoc_network_formed";
                break;
            case wlan_interface_state_disconnecting:
                status = "disconnecting";
                break;
            case wlan_interface_state_disconnected:
                status = "disconnected";
                break;
            case wlan_interface_state_associating:
                status = "associating";
                break;
            case wlan_interface_state_discovering:
                status = "discovering";
                break;
            case wlan_interface_state_authenticating:
                status = "authenticating";
                break;
            default:
                status = "unknown";
                break;
        }

        py_guid = PyUnicode_FromWideChar(GuidString, wcslen(GuidString));
        if (! py_guid)
            goto error;
        py_tuple = Py_BuildValue("(Os)", py_guid, status);
        if (!py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_CLEAR(py_guid);
        Py_CLEAR(py_tuple);
    }

    if (pIfList != NULL)
        WlanFreeMemory(pIfList);
    return py_retlist;

error:
    if (pIfList != NULL)
        WlanFreeMemory(pIfList);
    Py_XDECREF(py_tuple);
    Py_XDECREF(py_guid);
    Py_DECREF(py_retlist);
    WlanCloseHandle(hClient, NULL);
    return NULL;
}
