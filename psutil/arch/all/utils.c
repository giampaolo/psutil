/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// Fixes clash between winsock2.h and windows.h
#if defined(PSUTIL_WINDOWS)
#define WIN32_LEAN_AND_MEAN
#endif

#include <Python.h>
#include <stdarg.h>
#include <math.h>
#if defined(PSUTIL_WINDOWS)
#include <winsock2.h>
#else
#include <sys/socket.h>
#endif

#include "init.h"


// Build a Python object from a format string, append it to a list,
// then decref it. Eliminates the need for a temporary variable, a NULL
// check, and a Py_DECREF / Py_XDECREF at the error label. Returns 1 on
// success, 0 on failure with a Python exception set.
int
pylist_append_fmt(PyObject *list, const char *fmt, ...) {
    int ret = 0;  // 0 = failure
    PyObject *obj = NULL;
    va_list ap;

    va_start(ap, fmt);
    obj = Py_VaBuildValue(fmt, ap);
    va_end(ap);

    if (!obj)
        return 0;
    if (PyList_Append(list, obj) < 0)
        goto done;
    ret = 1;  // success

done:
    Py_DECREF(obj);
    return ret;
}


// Append a pre-built Python object to a list, then decref it. Same as
// pylist_append_fmt() but takes an already-built object instead of a
// format string. Returns 1 on success, 0 on failure with a Python
// exception set.
int
pylist_append_obj(PyObject *list, PyObject *obj) {
    if (!obj)
        return 0;
    if (PyList_Append(list, obj) < 0) {
        Py_DECREF(obj);
        return 0;
    }
    Py_DECREF(obj);
    return 1;
}


// Build a Python object from a format string, set it as a key in a
// dict, then decref it. Same idea as pylist_append_fmt() but for
// dicts. Returns 1 on success, 0 on failure with a Python exception
// set.
int
pydict_add(PyObject *dict, const char *key, const char *fmt, ...) {
    int ret = 0;  // 0 = failure
    PyObject *obj = NULL;
    va_list ap;

    va_start(ap, fmt);
    obj = Py_VaBuildValue(fmt, ap);
    va_end(ap);

    if (!obj)
        return 0;
    if (PyDict_SetItemString(dict, key, obj) < 0)
        goto done;
    ret = 1;  // success

done:
    Py_DECREF(obj);
    return ret;
}


// Return 1 if `value` is in `py_seq`, 0 if it's not, -1 on error with
// a Python exception set.
static int
int_in_seq(int value, PyObject *py_seq) {
    int inseq;
    PyObject *py_value;

    py_value = PyLong_FromLong((long)value);
    if (py_value == NULL)
        return -1;
    inseq = PySequence_Contains(py_seq, py_value);  // return -1 on failure
    Py_DECREF(py_value);
    return inseq;
}


// Parse the (af_filter, type_filter) args that the Python layer passes
// to net_connections(). Return 0 on success, -1 on error with a Python
// exception set.
int
psutil_parse_conn_filters(
    PyObject *py_af_filter, PyObject *py_type_filter, psutil_conn_filters *out
) {
    if (!PySequence_Check(py_af_filter) || !PySequence_Check(py_type_filter)) {
        PyErr_SetString(PyExc_TypeError, "arg 2 or 3 is not a sequence");
        return -1;
    }
    if ((out->v4 = int_in_seq(AF_INET, py_af_filter)) == -1)
        return -1;
    if ((out->v6 = int_in_seq(AF_INET6, py_af_filter)) == -1)
        return -1;
    if ((out->unix_ = int_in_seq(AF_UNIX, py_af_filter)) == -1)
        return -1;
    if ((out->tcp = int_in_seq(SOCK_STREAM, py_type_filter)) == -1)
        return -1;
    if ((out->udp = int_in_seq(SOCK_DGRAM, py_type_filter)) == -1)
        return -1;
    return 0;
}


double
psutil_usage_percent(double used, double total, int round_) {
    double ret;

    if (total == 0.0)
        return 0.0;
    ret = (used / total) * 100.0;
    if (round_ >= 0)
        ret = round(ret * pow(10, round_)) / pow(10, round_);
    return ret;
}
