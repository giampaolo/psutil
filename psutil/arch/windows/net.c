/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// Fixes clash between winsock2.h and windows.h
#define WIN32_LEAN_AND_MEAN

#include <Python.h>
#include <windows.h>
#include <wchar.h>
#include <ws2tcpip.h>

#include "../../_psutil_common.h"


static PIP_ADAPTER_ADDRESSES
psutil_get_nic_addresses(void) {
    ULONG bufferLength = 0;
    PIP_ADAPTER_ADDRESSES buffer;

    if (GetAdaptersAddresses(AF_UNSPEC, 0, NULL, NULL, &bufferLength)
            != ERROR_BUFFER_OVERFLOW)
    {
        PyErr_SetString(PyExc_RuntimeError,
                        "GetAdaptersAddresses() syscall failed.");
        return NULL;
    }

    buffer = malloc(bufferLength);
    if (buffer == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    memset(buffer, 0, bufferLength);

    if (GetAdaptersAddresses(AF_UNSPEC, 0, NULL, buffer, &bufferLength)
            != ERROR_SUCCESS)
    {
        free(buffer);
        PyErr_SetString(PyExc_RuntimeError,
                        "GetAdaptersAddresses() syscall failed.");
        return NULL;
    }

    return buffer;
}


/*
 * Return a Python list of named tuples with overall network I/O information
 */
PyObject *
psutil_net_io_counters(PyObject *self, PyObject *args) {
    DWORD dwRetVal = 0;
    MIB_IF_ROW2 *pIfRow = NULL;
    PIP_ADAPTER_ADDRESSES pAddresses = NULL;
    PIP_ADAPTER_ADDRESSES pCurrAddresses = NULL;
    PyObject *py_retdict = PyDict_New();
    PyObject *py_nic_info = NULL;
    PyObject *py_nic_name = NULL;

    if (py_retdict == NULL)
        return NULL;
    pAddresses = psutil_get_nic_addresses();
    if (pAddresses == NULL)
        goto error;
    pCurrAddresses = pAddresses;

    while (pCurrAddresses) {
        py_nic_name = NULL;
        py_nic_info = NULL;

        pIfRow = (MIB_IF_ROW2 *) malloc(sizeof(MIB_IF_ROW2));
        if (pIfRow == NULL) {
            PyErr_NoMemory();
            goto error;
        }

        SecureZeroMemory((PVOID)pIfRow, sizeof(MIB_IF_ROW2));
        pIfRow->InterfaceIndex = pCurrAddresses->IfIndex;
        dwRetVal = GetIfEntry2(pIfRow);
        if (dwRetVal != NO_ERROR) {
            PyErr_SetString(PyExc_RuntimeError,
                            "GetIfEntry() or GetIfEntry2() syscalls failed.");
            goto error;
        }

        py_nic_info = Py_BuildValue(
            "(KKKKKKKK)",
            pIfRow->OutOctets,
            pIfRow->InOctets,
            (pIfRow->OutUcastPkts + pIfRow->OutNUcastPkts),
            (pIfRow->InUcastPkts + pIfRow->InNUcastPkts),
            pIfRow->InErrors,
            pIfRow->OutErrors,
            pIfRow->InDiscards,
            pIfRow->OutDiscards);
        if (!py_nic_info)
            goto error;

        py_nic_name = PyUnicode_FromWideChar(
            pCurrAddresses->FriendlyName,
            wcslen(pCurrAddresses->FriendlyName));

        if (py_nic_name == NULL)
            goto error;
        if (PyDict_SetItem(py_retdict, py_nic_name, py_nic_info))
            goto error;
        Py_CLEAR(py_nic_name);
        Py_CLEAR(py_nic_info);

        free(pIfRow);
        pCurrAddresses = pCurrAddresses->Next;
    }

    free(pAddresses);
    return py_retdict;

error:
    Py_XDECREF(py_nic_name);
    Py_XDECREF(py_nic_info);
    Py_DECREF(py_retdict);
    if (pAddresses != NULL)
        free(pAddresses);
    if (pIfRow != NULL)
        free(pIfRow);
    return NULL;
}


/*
 * Return NICs addresses.
 */
PyObject *
psutil_net_if_addrs(PyObject *self, PyObject *args) {
    unsigned int i = 0;
    ULONG family;
    PCTSTR intRet;
    PCTSTR netmaskIntRet;
    char *ptr;
    char buff_addr[1024];
    char buff_macaddr[1024];
    char buff_netmask[1024];
    DWORD dwRetVal = 0;
    ULONG converted_netmask;
    UINT netmask_bits;
    struct in_addr in_netmask;
    PIP_ADAPTER_ADDRESSES pAddresses = NULL;
    PIP_ADAPTER_ADDRESSES pCurrAddresses = NULL;
    PIP_ADAPTER_UNICAST_ADDRESS pUnicast = NULL;

    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;
    PyObject *py_address = NULL;
    PyObject *py_mac_address = NULL;
    PyObject *py_nic_name = NULL;
    PyObject *py_netmask = NULL;

    if (py_retlist == NULL)
        return NULL;

    pAddresses = psutil_get_nic_addresses();
    if (pAddresses == NULL)
        goto error;
    pCurrAddresses = pAddresses;

    while (pCurrAddresses) {
        pUnicast = pCurrAddresses->FirstUnicastAddress;

        netmaskIntRet = NULL;
        py_nic_name = NULL;
        py_nic_name = PyUnicode_FromWideChar(
            pCurrAddresses->FriendlyName,
            wcslen(pCurrAddresses->FriendlyName));
        if (py_nic_name == NULL)
            goto error;

        // MAC address
        if (pCurrAddresses->PhysicalAddressLength != 0) {
            ptr = buff_macaddr;
            *ptr = '\0';
            for (i = 0; i < (int) pCurrAddresses->PhysicalAddressLength; i++) {
                if (i == (pCurrAddresses->PhysicalAddressLength - 1)) {
                    sprintf_s(ptr, _countof(buff_macaddr), "%.2X\n",
                              (int)pCurrAddresses->PhysicalAddress[i]);
                }
                else {
                    sprintf_s(ptr, _countof(buff_macaddr), "%.2X-",
                              (int)pCurrAddresses->PhysicalAddress[i]);
                }
                ptr += 3;
            }
            *--ptr = '\0';

            py_mac_address = Py_BuildValue("s", buff_macaddr);
            if (py_mac_address == NULL)
                goto error;

            Py_INCREF(Py_None);
            Py_INCREF(Py_None);
            Py_INCREF(Py_None);
            py_tuple = Py_BuildValue(
                "(OiOOOO)",
                py_nic_name,
                -1,  // this will be converted later to AF_LINK
                py_mac_address,
                Py_None,  // netmask (not supported)
                Py_None,  // broadcast (not supported)
                Py_None  // ptp (not supported on Windows)
            );
            if (! py_tuple)
                goto error;
            if (PyList_Append(py_retlist, py_tuple))
                goto error;
            Py_CLEAR(py_tuple);
            Py_CLEAR(py_mac_address);
        }

        // find out the IP address associated with the NIC
        if (pUnicast != NULL) {
            for (i = 0; pUnicast != NULL; i++) {
                family = pUnicast->Address.lpSockaddr->sa_family;
                if (family == AF_INET) {
                    struct sockaddr_in *sa_in = (struct sockaddr_in *)
                        pUnicast->Address.lpSockaddr;
                    intRet = inet_ntop(AF_INET, &(sa_in->sin_addr), buff_addr,
                                       sizeof(buff_addr));
                    if (!intRet)
                        goto error;
                    netmask_bits = pUnicast->OnLinkPrefixLength;
                    dwRetVal = ConvertLengthToIpv4Mask(
                        netmask_bits, &converted_netmask);
                    if (dwRetVal == NO_ERROR) {
                        in_netmask.s_addr = converted_netmask;
                        netmaskIntRet = inet_ntop(
                            AF_INET, &in_netmask, buff_netmask,
                            sizeof(buff_netmask));
                        if (!netmaskIntRet)
                            goto error;
                    }
                }
                else if (family == AF_INET6) {
                    struct sockaddr_in6 *sa_in6 = (struct sockaddr_in6 *)
                        pUnicast->Address.lpSockaddr;
                    intRet = inet_ntop(AF_INET6, &(sa_in6->sin6_addr),
                                       buff_addr, sizeof(buff_addr));
                    if (!intRet)
                        goto error;
                }
                else {
                    // we should never get here
                    pUnicast = pUnicast->Next;
                    continue;
                }

#if PY_MAJOR_VERSION >= 3
                py_address = PyUnicode_FromString(buff_addr);
#else
                py_address = PyString_FromString(buff_addr);
#endif
                if (py_address == NULL)
                    goto error;

                if (netmaskIntRet != NULL) {
#if PY_MAJOR_VERSION >= 3
                    py_netmask = PyUnicode_FromString(buff_netmask);
#else
                    py_netmask = PyString_FromString(buff_netmask);
#endif
                } else {
                    Py_INCREF(Py_None);
                    py_netmask = Py_None;
                }

                Py_INCREF(Py_None);
                Py_INCREF(Py_None);
                py_tuple = Py_BuildValue(
                    "(OiOOOO)",
                    py_nic_name,
                    family,
                    py_address,
                    py_netmask,
                    Py_None,  // broadcast (not supported)
                    Py_None  // ptp (not supported on Windows)
                );

                if (! py_tuple)
                    goto error;
                if (PyList_Append(py_retlist, py_tuple))
                    goto error;
                Py_CLEAR(py_tuple);
                Py_CLEAR(py_address);
                Py_CLEAR(py_netmask);

                pUnicast = pUnicast->Next;
            }
        }
        Py_CLEAR(py_nic_name);
        pCurrAddresses = pCurrAddresses->Next;
    }

    free(pAddresses);
    return py_retlist;

error:
    if (pAddresses)
        free(pAddresses);
    Py_DECREF(py_retlist);
    Py_XDECREF(py_tuple);
    Py_XDECREF(py_address);
    Py_XDECREF(py_nic_name);
    Py_XDECREF(py_netmask);
    return NULL;
}


/*
 * Provides stats about NIC interfaces installed on the system.
 * TODO: get 'duplex' (currently it's hard coded to '2', aka 'full duplex')
 */
PyObject *
psutil_net_if_stats(PyObject *self, PyObject *args) {
    int i;
    DWORD dwSize = 0;
    DWORD dwRetVal = 0;
    MIB_IFTABLE *pIfTable;
    MIB_IFROW *pIfRow;
    PIP_ADAPTER_ADDRESSES pAddresses = NULL;
    PIP_ADAPTER_ADDRESSES pCurrAddresses = NULL;
    char descr[MAX_PATH];
    int ifname_found;

    PyObject *py_nic_name = NULL;
    PyObject *py_retdict = PyDict_New();
    PyObject *py_ifc_info = NULL;
    PyObject *py_is_up = NULL;

    if (py_retdict == NULL)
        return NULL;

    pAddresses = psutil_get_nic_addresses();
    if (pAddresses == NULL)
        goto error;

    pIfTable = (MIB_IFTABLE *) malloc(sizeof (MIB_IFTABLE));
    if (pIfTable == NULL) {
        PyErr_NoMemory();
        goto error;
    }
    dwSize = sizeof(MIB_IFTABLE);
    if (GetIfTable(pIfTable, &dwSize, FALSE) == ERROR_INSUFFICIENT_BUFFER) {
        free(pIfTable);
        pIfTable = (MIB_IFTABLE *) malloc(dwSize);
        if (pIfTable == NULL) {
            PyErr_NoMemory();
            goto error;
        }
    }
    // Make a second call to GetIfTable to get the actual
    // data we want.
    if ((dwRetVal = GetIfTable(pIfTable, &dwSize, FALSE)) != NO_ERROR) {
        PyErr_SetString(PyExc_RuntimeError, "GetIfTable() syscall failed");
        goto error;
    }

    for (i = 0; i < (int) pIfTable->dwNumEntries; i++) {
        pIfRow = (MIB_IFROW *) & pIfTable->table[i];

        // GetIfTable is not able to give us NIC with "friendly names"
        // so we determine them via GetAdapterAddresses() which
        // provides friendly names *and* descriptions and find the
        // ones that match.
        ifname_found = 0;
        pCurrAddresses = pAddresses;
        while (pCurrAddresses) {
            sprintf_s(descr, MAX_PATH, "%wS", pCurrAddresses->Description);
            if (lstrcmp(descr, pIfRow->bDescr) == 0) {
                py_nic_name = PyUnicode_FromWideChar(
                    pCurrAddresses->FriendlyName,
                    wcslen(pCurrAddresses->FriendlyName));
                if (py_nic_name == NULL)
                    goto error;
                ifname_found = 1;
                break;
            }
            pCurrAddresses = pCurrAddresses->Next;
        }
        if (ifname_found == 0) {
            // Name not found means GetAdapterAddresses() doesn't list
            // this NIC, only GetIfTable, meaning it's not really a NIC
            // interface so we skip it.
            continue;
        }

        // is up?
        if ((pIfRow->dwOperStatus == MIB_IF_OPER_STATUS_CONNECTED ||
                pIfRow->dwOperStatus == MIB_IF_OPER_STATUS_OPERATIONAL) &&
                pIfRow->dwAdminStatus == 1 ) {
            py_is_up = Py_True;
        }
        else {
            py_is_up = Py_False;
        }
        Py_INCREF(py_is_up);

        py_ifc_info = Py_BuildValue(
            "(Oikk)",
            py_is_up,
            2,  // there's no way to know duplex so let's assume 'full'
            pIfRow->dwSpeed / 1000000,  // expressed in bytes, we want Mb
            pIfRow->dwMtu
        );
        if (!py_ifc_info)
            goto error;
        if (PyDict_SetItem(py_retdict, py_nic_name, py_ifc_info))
            goto error;
        Py_CLEAR(py_nic_name);
        Py_CLEAR(py_ifc_info);
    }

    free(pIfTable);
    free(pAddresses);
    return py_retdict;

error:
    Py_XDECREF(py_is_up);
    Py_XDECREF(py_ifc_info);
    Py_XDECREF(py_nic_name);
    Py_DECREF(py_retdict);
    if (pIfTable != NULL)
        free(pIfTable);
    if (pAddresses != NULL)
        free(pAddresses);
    return NULL;
}
