/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// Fixes clash between winsock2.h and windows.h
#define WIN32_LEAN_AND_MEAN

#include <Python.h>
#include <windows.h>
#include <ws2tcpip.h>

#include "../../_psutil_common.h"
#include "process_utils.h"


#define BYTESWAP_USHORT(x) ((((USHORT)(x) << 8) | ((USHORT)(x) >> 8)) & 0xffff)
#define STATUS_UNSUCCESSFUL 0xC0000001

ULONG g_TcpTableSize = 0;
ULONG g_UdpTableSize = 0;


// Note about GetExtended[Tcp|Udp]Table syscalls: due to other processes
// being active on the machine, it's possible that the size of the table
// increases between the moment we query the size and the moment we query
// the data. Therefore we retry if that happens. See:
// https://github.com/giampaolo/psutil/pull/1335
// https://github.com/giampaolo/psutil/issues/1294
// A global and ever increasing size is used in order to avoid calling
// GetExtended[Tcp|Udp]Table twice per call (faster).


static PVOID __GetExtendedTcpTable(ULONG family) {
    DWORD err;
    PVOID table;
    ULONG size;
    TCP_TABLE_CLASS class = TCP_TABLE_OWNER_PID_ALL;

    size = g_TcpTableSize;
    if (size == 0) {
        GetExtendedTcpTable(NULL, &size, FALSE, family, class, 0);
        // reserve 25% more space
        size = size + (size / 2 / 2);
        g_TcpTableSize = size;
    }

    table = malloc(size);
    if (table == NULL) {
        PyErr_NoMemory();
        return NULL;
    }

    err = GetExtendedTcpTable(table, &size, FALSE, family, class, 0);
    if (err == NO_ERROR)
        return table;

    free(table);
    if (err == ERROR_INSUFFICIENT_BUFFER || err == STATUS_UNSUCCESSFUL) {
        psutil_debug("GetExtendedTcpTable: retry with different bufsize");
        g_TcpTableSize = 0;
        return __GetExtendedTcpTable(family);
    }

    PyErr_SetString(PyExc_RuntimeError, "GetExtendedTcpTable failed");
    return NULL;
}


static PVOID __GetExtendedUdpTable(ULONG family) {
    DWORD err;
    PVOID table;
    ULONG size;
    UDP_TABLE_CLASS class = UDP_TABLE_OWNER_PID;

    size = g_UdpTableSize;
    if (size == 0) {
        GetExtendedUdpTable(NULL, &size, FALSE, family, class, 0);
        // reserve 25% more space
        size = size + (size / 2 / 2);
        g_UdpTableSize = size;
    }

    table = malloc(size);
    if (table == NULL) {
        PyErr_NoMemory();
        return NULL;
    }

    err = GetExtendedUdpTable(table, &size, FALSE, family, class, 0);
    if (err == NO_ERROR)
        return table;

    free(table);
    if (err == ERROR_INSUFFICIENT_BUFFER || err == STATUS_UNSUCCESSFUL) {
        psutil_debug("GetExtendedUdpTable: retry with different bufsize");
        g_UdpTableSize = 0;
        return __GetExtendedUdpTable(family);
    }

    PyErr_SetString(PyExc_RuntimeError, "GetExtendedUdpTable failed");
    return NULL;
}


#define psutil_conn_decref_objs() \
    Py_DECREF(_AF_INET); \
    Py_DECREF(_AF_INET6);\
    Py_DECREF(_SOCK_STREAM);\
    Py_DECREF(_SOCK_DGRAM);


/*
 * Return a list of network connections opened by a process
 */
PyObject *
psutil_net_connections(PyObject *self, PyObject *args) {
    static long null_address[4] = { 0, 0, 0, 0 };
    DWORD pid;
    int pid_return;
    PVOID table = NULL;
    PMIB_TCPTABLE_OWNER_PID tcp4Table;
    PMIB_UDPTABLE_OWNER_PID udp4Table;
    PMIB_TCP6TABLE_OWNER_PID tcp6Table;
    PMIB_UDP6TABLE_OWNER_PID udp6Table;
    ULONG i;
    CHAR addressBufferLocal[65];
    CHAR addressBufferRemote[65];

    PyObject *py_retlist = NULL;
    PyObject *py_conn_tuple = NULL;
    PyObject *py_af_filter = NULL;
    PyObject *py_type_filter = NULL;
    PyObject *py_addr_tuple_local = NULL;
    PyObject *py_addr_tuple_remote = NULL;
    PyObject *_AF_INET = PyLong_FromLong((long)AF_INET);
    PyObject *_AF_INET6 = PyLong_FromLong((long)AF_INET6);
    PyObject *_SOCK_STREAM = PyLong_FromLong((long)SOCK_STREAM);
    PyObject *_SOCK_DGRAM = PyLong_FromLong((long)SOCK_DGRAM);

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID "OO", &pid, &py_af_filter,
                           &py_type_filter))
    {
        goto error;
    }

    if (!PySequence_Check(py_af_filter) || !PySequence_Check(py_type_filter)) {
        psutil_conn_decref_objs();
        PyErr_SetString(PyExc_TypeError, "arg 2 or 3 is not a sequence");
        return NULL;
    }

    if (pid != -1) {
        pid_return = psutil_pid_is_running(pid);
        if (pid_return == 0) {
            psutil_conn_decref_objs();
            return NoSuchProcess("psutil_pid_is_running");
        }
        else if (pid_return == -1) {
            psutil_conn_decref_objs();
            return NULL;
        }
    }

    py_retlist = PyList_New(0);
    if (py_retlist == NULL) {
        psutil_conn_decref_objs();
        return NULL;
    }

    // TCP IPv4

    if ((PySequence_Contains(py_af_filter, _AF_INET) == 1) &&
            (PySequence_Contains(py_type_filter, _SOCK_STREAM) == 1))
    {
        table = NULL;
        py_conn_tuple = NULL;
        py_addr_tuple_local = NULL;
        py_addr_tuple_remote = NULL;

        table = __GetExtendedTcpTable(AF_INET);
        if (table == NULL)
            goto error;
        tcp4Table = table;
        for (i = 0; i < tcp4Table->dwNumEntries; i++) {
            if (pid != -1) {
                if (tcp4Table->table[i].dwOwningPid != pid) {
                    continue;
                }
            }

            if (tcp4Table->table[i].dwLocalAddr != 0 ||
                    tcp4Table->table[i].dwLocalPort != 0)
            {
                struct in_addr addr;

                addr.S_un.S_addr = tcp4Table->table[i].dwLocalAddr;
                RtlIpv4AddressToStringA(&addr, addressBufferLocal);
                py_addr_tuple_local = Py_BuildValue(
                    "(si)",
                    addressBufferLocal,
                    BYTESWAP_USHORT(tcp4Table->table[i].dwLocalPort));
            }
            else {
                py_addr_tuple_local = PyTuple_New(0);
            }

            if (py_addr_tuple_local == NULL)
                goto error;

            // On Windows <= XP, remote addr is filled even if socket
            // is in LISTEN mode in which case we just ignore it.
            if ((tcp4Table->table[i].dwRemoteAddr != 0 ||
                    tcp4Table->table[i].dwRemotePort != 0) &&
                    (tcp4Table->table[i].dwState != MIB_TCP_STATE_LISTEN))
            {
                struct in_addr addr;

                addr.S_un.S_addr = tcp4Table->table[i].dwRemoteAddr;
                RtlIpv4AddressToStringA(&addr, addressBufferRemote);
                py_addr_tuple_remote = Py_BuildValue(
                    "(si)",
                    addressBufferRemote,
                    BYTESWAP_USHORT(tcp4Table->table[i].dwRemotePort));
            }
            else
            {
                py_addr_tuple_remote = PyTuple_New(0);
            }

            if (py_addr_tuple_remote == NULL)
                goto error;

            py_conn_tuple = Py_BuildValue(
                "(iiiNNiI)",
                -1,
                AF_INET,
                SOCK_STREAM,
                py_addr_tuple_local,
                py_addr_tuple_remote,
                tcp4Table->table[i].dwState,
                tcp4Table->table[i].dwOwningPid);
            if (!py_conn_tuple)
                goto error;
            if (PyList_Append(py_retlist, py_conn_tuple))
                goto error;
            Py_CLEAR(py_conn_tuple);
        }

        free(table);
        table = NULL;
    }

    // TCP IPv6
    if ((PySequence_Contains(py_af_filter, _AF_INET6) == 1) &&
            (PySequence_Contains(py_type_filter, _SOCK_STREAM) == 1) &&
            (RtlIpv6AddressToStringA != NULL))
    {
        table = NULL;
        py_conn_tuple = NULL;
        py_addr_tuple_local = NULL;
        py_addr_tuple_remote = NULL;

        table = __GetExtendedTcpTable(AF_INET6);
        if (table == NULL)
            goto error;
        tcp6Table = table;
        for (i = 0; i < tcp6Table->dwNumEntries; i++)
        {
            if (pid != -1) {
                if (tcp6Table->table[i].dwOwningPid != pid) {
                    continue;
                }
            }

            if (memcmp(tcp6Table->table[i].ucLocalAddr, null_address, 16)
                    != 0 || tcp6Table->table[i].dwLocalPort != 0)
            {
                struct in6_addr addr;

                memcpy(&addr, tcp6Table->table[i].ucLocalAddr, 16);
                RtlIpv6AddressToStringA(&addr, addressBufferLocal);
                py_addr_tuple_local = Py_BuildValue(
                    "(si)",
                    addressBufferLocal,
                    BYTESWAP_USHORT(tcp6Table->table[i].dwLocalPort));
            }
            else {
                py_addr_tuple_local = PyTuple_New(0);
            }

            if (py_addr_tuple_local == NULL)
                goto error;

            // On Windows <= XP, remote addr is filled even if socket
            // is in LISTEN mode in which case we just ignore it.
            if ((memcmp(tcp6Table->table[i].ucRemoteAddr, null_address, 16)
                    != 0 ||
                    tcp6Table->table[i].dwRemotePort != 0) &&
                    (tcp6Table->table[i].dwState != MIB_TCP_STATE_LISTEN))
            {
                struct in6_addr addr;

                memcpy(&addr, tcp6Table->table[i].ucRemoteAddr, 16);
                RtlIpv6AddressToStringA(&addr, addressBufferRemote);
                py_addr_tuple_remote = Py_BuildValue(
                    "(si)",
                    addressBufferRemote,
                    BYTESWAP_USHORT(tcp6Table->table[i].dwRemotePort));
            }
            else {
                py_addr_tuple_remote = PyTuple_New(0);
            }

            if (py_addr_tuple_remote == NULL)
                goto error;

            py_conn_tuple = Py_BuildValue(
                "(iiiNNiI)",
                -1,
                AF_INET6,
                SOCK_STREAM,
                py_addr_tuple_local,
                py_addr_tuple_remote,
                tcp6Table->table[i].dwState,
                tcp6Table->table[i].dwOwningPid);
            if (!py_conn_tuple)
                goto error;
            if (PyList_Append(py_retlist, py_conn_tuple))
                goto error;
            Py_CLEAR(py_conn_tuple);
        }

        free(table);
        table = NULL;
    }

    // UDP IPv4

    if ((PySequence_Contains(py_af_filter, _AF_INET) == 1) &&
            (PySequence_Contains(py_type_filter, _SOCK_DGRAM) == 1))
    {
        table = NULL;
        py_conn_tuple = NULL;
        py_addr_tuple_local = NULL;
        py_addr_tuple_remote = NULL;
        table = __GetExtendedUdpTable(AF_INET);
        if (table == NULL)
            goto error;
        udp4Table = table;
        for (i = 0; i < udp4Table->dwNumEntries; i++)
        {
            if (pid != -1) {
                if (udp4Table->table[i].dwOwningPid != pid) {
                    continue;
                }
            }

            if (udp4Table->table[i].dwLocalAddr != 0 ||
                udp4Table->table[i].dwLocalPort != 0)
            {
                struct in_addr addr;

                addr.S_un.S_addr = udp4Table->table[i].dwLocalAddr;
                RtlIpv4AddressToStringA(&addr, addressBufferLocal);
                py_addr_tuple_local = Py_BuildValue(
                    "(si)",
                    addressBufferLocal,
                    BYTESWAP_USHORT(udp4Table->table[i].dwLocalPort));
            }
            else {
                py_addr_tuple_local = PyTuple_New(0);
            }

            if (py_addr_tuple_local == NULL)
                goto error;

            py_conn_tuple = Py_BuildValue(
                "(iiiNNiI)",
                -1,
                AF_INET,
                SOCK_DGRAM,
                py_addr_tuple_local,
                PyTuple_New(0),
                PSUTIL_CONN_NONE,
                udp4Table->table[i].dwOwningPid);
            if (!py_conn_tuple)
                goto error;
            if (PyList_Append(py_retlist, py_conn_tuple))
                goto error;
            Py_CLEAR(py_conn_tuple);
        }

        free(table);
        table = NULL;
    }

    // UDP IPv6

    if ((PySequence_Contains(py_af_filter, _AF_INET6) == 1) &&
            (PySequence_Contains(py_type_filter, _SOCK_DGRAM) == 1) &&
            (RtlIpv6AddressToStringA != NULL))
    {
        table = NULL;
        py_conn_tuple = NULL;
        py_addr_tuple_local = NULL;
        py_addr_tuple_remote = NULL;
        table = __GetExtendedUdpTable(AF_INET6);
        if (table == NULL)
            goto error;
        udp6Table = table;
        for (i = 0; i < udp6Table->dwNumEntries; i++) {
            if (pid != -1) {
                if (udp6Table->table[i].dwOwningPid != pid) {
                    continue;
                }
            }

            if (memcmp(udp6Table->table[i].ucLocalAddr, null_address, 16)
                    != 0 || udp6Table->table[i].dwLocalPort != 0)
            {
                struct in6_addr addr;

                memcpy(&addr, udp6Table->table[i].ucLocalAddr, 16);
                RtlIpv6AddressToStringA(&addr, addressBufferLocal);
                py_addr_tuple_local = Py_BuildValue(
                    "(si)",
                    addressBufferLocal,
                    BYTESWAP_USHORT(udp6Table->table[i].dwLocalPort));
            }
            else {
                py_addr_tuple_local = PyTuple_New(0);
            }

            if (py_addr_tuple_local == NULL)
                goto error;

            py_conn_tuple = Py_BuildValue(
                "(iiiNNiI)",
                -1,
                AF_INET6,
                SOCK_DGRAM,
                py_addr_tuple_local,
                PyTuple_New(0),
                PSUTIL_CONN_NONE,
                udp6Table->table[i].dwOwningPid);
            if (!py_conn_tuple)
                goto error;
            if (PyList_Append(py_retlist, py_conn_tuple))
                goto error;
            Py_CLEAR(py_conn_tuple);
        }

        free(table);
        table = NULL;
    }

    psutil_conn_decref_objs();
    return py_retlist;

error:
    psutil_conn_decref_objs();
    Py_XDECREF(py_conn_tuple);
    Py_XDECREF(py_addr_tuple_local);
    Py_XDECREF(py_addr_tuple_remote);
    Py_DECREF(py_retlist);
    if (table != NULL)
        free(table);
    return NULL;
}
