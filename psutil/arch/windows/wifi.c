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


// TODO: avoid global var and instead use pContext in notification_callback().
int waitFlag = 1;

static char *
convert_status(PWLAN_INTERFACE_INFO pIfInfo) {
    switch (pIfInfo->isState) {
        case wlan_interface_state_not_ready:
            return "not_ready";
        case wlan_interface_state_connected:
            return "connected";
        case wlan_interface_state_ad_hoc_network_formed:
            return "ad_hoc_network_formed";
        case wlan_interface_state_disconnecting:
            return "disconnecting";
        case wlan_interface_state_disconnected:
            return "disconnected";
        case wlan_interface_state_associating:
            return "associating";
        case wlan_interface_state_discovering:
            return "discovering";
        case wlan_interface_state_authenticating:
            return "authenticating";
        default:
            return "unknown";
    }
}


static char *
convert_auth(int value) {
    switch (value) {
        case DOT11_AUTH_ALGO_80211_OPEN:
            return "802.11 Open";
        case DOT11_AUTH_ALGO_80211_SHARED_KEY:
            return "802.11 Shared";
        case DOT11_AUTH_ALGO_WPA:
            return "WPA";
        case DOT11_AUTH_ALGO_WPA_PSK:
            return "WPA-PSK";
        case DOT11_AUTH_ALGO_WPA_NONE:
            return "WPA-None";
        case DOT11_AUTH_ALGO_RSNA:
            return "RSNA";
        case DOT11_AUTH_ALGO_RSNA_PSK:
            return "RSNA-PSK";
        default:
            return "unknown";
    }
}


static char *
convert_cipher(int value) {
    switch (value) {
        case DOT11_CIPHER_ALGO_NONE:
            return "None";
        case DOT11_CIPHER_ALGO_WEP40:
            return "WEP-40";
        case DOT11_CIPHER_ALGO_TKIP:
            return "TKIP";
        case DOT11_CIPHER_ALGO_CCMP:
            return "CCMP";
        case DOT11_CIPHER_ALGO_WEP104:
            return "WEP-104 (0x%x)";
        case DOT11_CIPHER_ALGO_WEP:
            return "WEP";
        default:
            return "unknown";
    }
}


static char *
convert_macaddr(unsigned char *ptr) {
    static char buff[64];

    sprintf(buff, "%02X:%02X:%02X:%02X:%02X:%02X",
            (ptr[0] & 0xFF), (ptr[1] & 0xFF),
            (ptr[2] & 0xFF), (ptr[3] & 0xFF),
            (ptr[4] & 0xFF), (ptr[5] & 0xFF));
    return buff;
}


long
quality_perc_to_rssi(WLAN_SIGNAL_QUALITY value) {
    // RSSI (signal quality) expressed in dBm
    if (value == 0)
        return (long)-100;
    else if (value == 100)
        return (long)-50;
    else
        return -100 + ((long)value / 2);
}


// ---


PyObject *
psutil_wifi_ifaces(PyObject *self, PyObject *args) {
    HANDLE hClient = NULL;
    DWORD dwMaxClient = 2;
    DWORD dwCurVersion = 0;
    DWORD dwResult = 0;
    int iRet = 0;
    WCHAR GuidString[40] = {0};
    int i;
    PWLAN_INTERFACE_INFO_LIST pIfList = NULL;
    PWLAN_INTERFACE_INFO pIfInfo = NULL;

    // variables used for WlanQueryInterfaces for opcode = wlan_intf_opcode_current_connection
    PWLAN_CONNECTION_ATTRIBUTES pConnectInfo = NULL;
    DWORD connectInfoSize = sizeof(WLAN_CONNECTION_ATTRIBUTES);
    WLAN_OPCODE_VALUE_TYPE opCode = wlan_opcode_value_type_invalid;

    PyObject *py_dict = NULL;
    PyObject *py_guid = NULL;
    PyObject *py_essid = NULL;
    PyObject *py_bssid = NULL;
    PyObject *py_auth = NULL;
    PyObject *py_cipher = NULL;
    PyObject *py_description = NULL;
    PyObject *py_status = NULL;
    PyObject *py_qual_perc = NULL;
    PyObject *py_signal = NULL;
    PyObject *py_rxbitrate = NULL;
    PyObject *py_txbitrate = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;

    dwResult = WlanOpenHandle(dwMaxClient, NULL, &dwCurVersion, &hClient);
    if (dwResult != ERROR_SUCCESS) {
        PyErr_SetFromOSErrnoWithSyscall("WlanOpenHandle");
        return NULL;
    }

    dwResult = WlanEnumInterfaces(hClient, NULL, &pIfList);
    if (dwResult != ERROR_SUCCESS) {
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

        // --- build dict
        py_dict = PyDict_New();
        if (!py_dict)
            goto error;
        // status
        py_status = Py_BuildValue("s", convert_status(pIfInfo));
        if (! py_status)
            goto error;
        if (PyDict_SetItemString(py_dict, "status", py_status))
            goto error;
        // guid
        py_guid = PyUnicode_FromWideChar(GuidString, wcslen(GuidString));
        if (! py_guid)
            goto error;
        if (PyDict_SetItemString(py_dict, "guid", py_guid))
            goto error;
        // description
        py_description = PyUnicode_FromWideChar(
            pIfInfo->strInterfaceDescription,
            wcslen(pIfInfo->strInterfaceDescription));
        if (! py_description)
            goto error;
        if (PyDict_SetItemString(py_dict, "descr", py_description))
            goto error;

        // --- if the interface is connected retrieve more info

        if (pIfInfo->isState == wlan_interface_state_connected) {
            dwResult = WlanQueryInterface(
                hClient,
                &pIfInfo->InterfaceGuid,
                wlan_intf_opcode_current_connection,
                NULL,
                &connectInfoSize,
                (PVOID *) &pConnectInfo,
                &opCode);

            if (dwResult != ERROR_SUCCESS) {
                PyErr_SetFromOSErrnoWithSyscall("WlanEnumInterfaces");
                goto error;
            }

            // essid
            py_essid = Py_BuildValue("s",
                pConnectInfo->wlanAssociationAttributes.dot11Ssid.ucSSID);
            if (! py_essid)
                goto error;
            if (PyDict_SetItemString(py_dict, "essid", py_essid))
                goto error;
            // bssid
            py_bssid = Py_BuildValue("s",
                convert_macaddr(
                    pConnectInfo->wlanAssociationAttributes.dot11Bssid));
            if (! py_bssid)
                goto error;
            if (PyDict_SetItemString(py_dict, "bssid", py_bssid))
                goto error;
            // quality percent
            py_qual_perc = Py_BuildValue(
                "k", pConnectInfo->wlanAssociationAttributes.wlanSignalQuality);
            if (! py_qual_perc)
                goto error;
            if (PyDict_SetItemString(py_dict, "quality_percent", py_qual_perc))
                goto error;
            // signal
            py_signal = Py_BuildValue(
                "l", quality_perc_to_rssi(
                    pConnectInfo->wlanAssociationAttributes.wlanSignalQuality));
            if (! py_signal)
                goto error;
            if (PyDict_SetItemString(py_dict, "signal", py_signal))
                goto error;
            // auth
            py_auth = Py_BuildValue("s",
                convert_auth(
                    pConnectInfo->wlanSecurityAttributes.dot11AuthAlgorithm));
            if (! py_auth)
                goto error;
            if (PyDict_SetItemString(py_dict, "auth", py_auth))
                goto error;
            // cipher
            py_cipher = Py_BuildValue("s",
                convert_cipher(
                    pConnectInfo->wlanSecurityAttributes.dot11CipherAlgorithm));
            if (! py_cipher)
                goto error;
            if (PyDict_SetItemString(py_dict, "cipher", py_cipher))
                goto error;
            // RX rate (MB/sec)
            py_rxbitrate = Py_BuildValue("k",
                pConnectInfo->wlanAssociationAttributes.ulRxRate / 1000);
            if (! py_rxbitrate)
                goto error;
            if (PyDict_SetItemString(py_dict, "rxbitrate", py_rxbitrate))
                goto error;
            // TX rate (MB/sec)
            py_txbitrate = Py_BuildValue("k",
                pConnectInfo->wlanAssociationAttributes.ulTxRate / 1000);
            if (! py_txbitrate)
                goto error;
            if (PyDict_SetItemString(py_dict, "txbitrate", py_txbitrate))
                goto error;
        }

        // cleanup
        if (PyList_Append(py_retlist, py_dict))
            goto error;
        Py_CLEAR(py_auth);
        Py_CLEAR(py_bssid);
        Py_CLEAR(py_cipher);
        Py_CLEAR(py_description);
        Py_CLEAR(py_essid);
        Py_CLEAR(py_guid);
        Py_CLEAR(py_qual_perc);
        Py_CLEAR(py_rxbitrate);
        Py_CLEAR(py_signal);
        Py_CLEAR(py_status);
        Py_CLEAR(py_txbitrate);

        Py_CLEAR(py_dict);
    }

    WlanCloseHandle(hClient, NULL);
    if (pIfList != NULL)
        WlanFreeMemory(pIfList);
    return py_retlist;

error:
    if (pIfList != NULL)
        WlanFreeMemory(pIfList);
    Py_XDECREF(py_auth);
    Py_XDECREF(py_bssid);
    Py_XDECREF(py_cipher);
    Py_XDECREF(py_description);
    Py_XDECREF(py_essid);
    Py_XDECREF(py_guid);
    Py_XDECREF(py_qual_perc);
    Py_XDECREF(py_rxbitrate);
    Py_XDECREF(py_signal);
    Py_XDECREF(py_status);
    Py_XDECREF(py_txbitrate);

    Py_XDECREF(py_dict);
    Py_DECREF(py_retlist);
    WlanCloseHandle(hClient, NULL);
    return NULL;
}


static void
notification_callback(PWLAN_NOTIFICATION_DATA pNotifData, PVOID pContext) {
    if (pNotifData == NULL) {
        psutil_debug("pNotifData == NULL");
        return;
    }
    if (pNotifData->NotificationSource == WLAN_NOTIFICATION_SOURCE_ACM) {
        waitFlag = 0;
        if (pNotifData->NotificationCode == wlan_notification_acm_scan_complete) {
            psutil_debug("Wi-Fi scan completed");
        }
        else if (pNotifData->NotificationCode == wlan_notification_acm_scan_fail) {
            // TODO: provide better error message.
            psutil_debug("Wi-Fi scan error");
            PyErr_Format(PyExc_RuntimeError, "Wi-Fi scan error");
        }
        else {
            psutil_debug("Wi-Fi scan ignored notification code %i",
                         pNotifData->NotificationCode);
        }
        return;
    }
    psutil_debug("NotificationSource != WLAN_NOTIFICATION_SOURCE_ACM");
}


static int
refresh_scan(HANDLE hClient, GUID guid) {
    DWORD dwResult;
    DWORD dwPrevNotifType = 0;

    // Scan takes a while so we need to register a callback.
    dwResult = WlanRegisterNotification(
        hClient,
        WLAN_NOTIFICATION_SOURCE_ACM,
        FALSE,
        (WLAN_NOTIFICATION_CALLBACK)notification_callback,
        NULL,
        NULL,
        &dwPrevNotifType);

    if (dwResult != ERROR_SUCCESS) {
        PyErr_SetFromOSErrnoWithSyscall("WlanRegisterNotification");
        return 1;
    }

    // Scan.
    dwResult = WlanScan(hClient, &guid, NULL, NULL, NULL);
    if (dwResult != ERROR_SUCCESS) {
        PyErr_SetFromOSErrnoWithSyscall("WlanScan");
        return 1;
    }

    // Yawn...
    waitFlag = 1;
    while (waitFlag == 1)
        Sleep(100);

    // Unregister callback.
    dwResult = WlanRegisterNotification(
        hClient,
        WLAN_NOTIFICATION_SOURCE_NONE,
        FALSE,
        NULL,
        NULL,
        NULL,
        &dwPrevNotifType);

    if (dwResult != ERROR_SUCCESS) {
        PyErr_SetFromOSErrnoWithSyscall("WlanRegisterNotification (unregister)");
        return 1;
    }

    // Check if callback set an exception.
    if (PyErr_Occurred() != NULL)
        return 1;
    return 0;
}


/*
 * Scan Wi-Fi networks.
 */
PyObject *
psutil_wifi_scan(PyObject *self, PyObject *args) {
    LPWSTR guidstr;
    GUID guid;
    HRESULT hr;
    HANDLE hClient = NULL;
    DWORD dwMaxClient = 2;
    DWORD dwCurVersion = 0;
    DWORD dwResult;
    unsigned int j;
    long signal;
    char *auth;
    char *cipher;
    char macaddr[200];
    PWLAN_AVAILABLE_NETWORK_LIST pBssList = NULL;
    PWLAN_AVAILABLE_NETWORK pBssEntry = NULL;
    PWLAN_BSS_LIST WlanBssList = NULL;
    PyObject *py_dict = NULL;
    PyObject *py_ssid = NULL;
    PyObject *py_quality = NULL;
    PyObject *py_signal = NULL;
    PyObject *py_auth = NULL;
    PyObject *py_cipher = NULL;
    PyObject *py_macaddr = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;
    if (! PyArg_ParseTuple(args, "u", &guidstr))
        return NULL;

    // Get GUID.
    hr = CLSIDFromString(guidstr, (LPCLSID)&guid);
    if (hr != NOERROR) {
        PyErr_SetString(PyExc_RuntimeError, "CLSIDFromString syscall failed");
        return NULL;
    }

    // Open handle.
    dwResult = WlanOpenHandle(dwMaxClient, NULL, &dwCurVersion, &hClient);
    if (dwResult != ERROR_SUCCESS) {
        PyErr_SetFromOSErrnoWithSyscall("WlanOpenHandle");
        return NULL;
    }

    // Refresh scan results.
    if (refresh_scan(hClient, guid) == 1)
        goto error;

    // Get results.
    dwResult = WlanGetAvailableNetworkList(hClient, &guid, 0,  NULL, &pBssList);
    if (dwResult != ERROR_SUCCESS) {
        PyErr_SetFromOSErrnoWithSyscall("WlanGetAvailableNetworkList");
        return NULL;
    }

    // https://docs.microsoft.com/en-us/windows/win32/api/wlanapi/ns-wlanapi-wlan_available_network
    for (j = 0; j < pBssList->dwNumberOfItems; j++) {
        pBssEntry = (WLAN_AVAILABLE_NETWORK *) & pBssList->Network[j];
        if (! pBssEntry->bNetworkConnectable)
            continue;

        // RSSI expressed in dbm
        signal = quality_perc_to_rssi(pBssEntry->wlanSignalQuality);
        auth = convert_auth(pBssEntry->dot11DefaultAuthAlgorithm);
        cipher = convert_cipher(pBssEntry->dot11DefaultCipherAlgorithm);

        // Get MAC address.
        dwResult = WlanGetNetworkBssList(
            hClient,
            &guid,
            &pBssEntry->dot11Ssid,
            pBssEntry->dot11BssType,
            pBssEntry->bSecurityEnabled,
            NULL,
            &WlanBssList);
        if (dwResult != ERROR_SUCCESS) {
            PyErr_SetFromOSErrnoWithSyscall("WlanGetNetworkBssList");
            goto error;
        }
        if (WlanBssList->dwNumberOfItems < 1) {
            PyErr_SetString(PyExc_RuntimeError, "dwNumberOfItems = 0");
            goto error;
        }
        snprintf(
            macaddr,
            sizeof(macaddr),
            "%02x:%02x:%02x:%02x:%02x:%02x",
            WlanBssList->wlanBssEntries[0].dot11Bssid[0],
            WlanBssList->wlanBssEntries[0].dot11Bssid[1],
            WlanBssList->wlanBssEntries[0].dot11Bssid[2],
            WlanBssList->wlanBssEntries[0].dot11Bssid[3],
            WlanBssList->wlanBssEntries[0].dot11Bssid[4],
            WlanBssList->wlanBssEntries[0].dot11Bssid[5]);

        // --- build Python dict

        py_dict = PyDict_New();
        if (!py_dict)
            goto error;
        // SSID
        py_ssid = Py_BuildValue("s", pBssEntry->dot11Ssid.ucSSID);
        if (! py_ssid)
            goto error;
        if (PyDict_SetItemString(py_dict, "ssid", py_ssid))
            goto error;
        // quality
        py_quality = Py_BuildValue("i", pBssEntry->wlanSignalQuality);
        if (! py_quality)
            goto error;
        if (PyDict_SetItemString(py_dict, "quality", py_quality))
            goto error;
        // signal
        py_signal = Py_BuildValue("i", signal);
        if (! py_signal)
            goto error;
        if (PyDict_SetItemString(py_dict, "signal", py_signal))
            goto error;
        // auth
        py_auth = Py_BuildValue("s", auth);
        if (! py_auth)
            goto error;
        if (PyDict_SetItemString(py_dict, "auth", py_auth))
            goto error;
        // cipher
        py_cipher = Py_BuildValue("s", cipher);
        if (! py_cipher)
            goto error;
        if (PyDict_SetItemString(py_dict, "cipher", py_cipher))
            goto error;
        // MAC address
        py_macaddr = Py_BuildValue("s", macaddr);
        if (! py_macaddr)
            goto error;
        if (PyDict_SetItemString(py_dict, "macaddr", py_macaddr))
            goto error;

        // cleanup
        if (PyList_Append(py_retlist, py_dict))
            goto error;
        Py_CLEAR(py_dict);
        Py_CLEAR(py_ssid);
        Py_CLEAR(py_quality);
        Py_CLEAR(py_signal);
        Py_CLEAR(py_auth);
        Py_CLEAR(py_cipher);
        Py_CLEAR(py_macaddr);
        Py_CLEAR(py_dict);
    }

    WlanCloseHandle(hClient, NULL);
    WlanFreeMemory(pBssList);
    return py_retlist;

error:
    WlanCloseHandle(hClient, NULL);
    if (pBssList != NULL)
        WlanFreeMemory(pBssList);
    Py_XDECREF(py_dict);
    Py_XDECREF(py_ssid);
    Py_XDECREF(py_quality);
    Py_XDECREF(py_signal);
    Py_XDECREF(py_auth);
    Py_XDECREF(py_cipher);
    Py_XDECREF(py_macaddr);
    Py_XDECREF(py_dict);
    Py_DECREF(py_retlist);
    return NULL;
}
