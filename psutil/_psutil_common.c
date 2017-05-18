/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Routines common to all platforms.
 */

#include <Python.h>
#include <stdio.h>

/*
 * Set OSError(errno=ESRCH, strerror="No such process") Python exception.
 */
PyObject *
NoSuchProcess(void) {
    PyObject *exc;
    char *msg = strerror(ESRCH);
    exc = PyObject_CallFunction(PyExc_OSError, "(is)", ESRCH, msg);
    PyErr_SetObject(PyExc_OSError, exc);
    Py_XDECREF(exc);
    return NULL;
}


/*
 * Set OSError(errno=EACCES, strerror="Permission denied") Python exception.
 */
PyObject *
AccessDenied(void) {
    PyObject *exc;
    char *msg = strerror(EACCES);
    exc = PyObject_CallFunction(PyExc_OSError, "(is)", EACCES, msg);
    PyErr_SetObject(PyExc_OSError, exc);
    Py_XDECREF(exc);
    return NULL;
}


static int _psutil_testing = -1;


/*
 * Return 1 if PSUTIL_TESTING env var is set else 0.
 */
int
psutil_testing(void) {
    if (_psutil_testing == -1) {
        if (getenv("PSUTIL_TESTING") != NULL)
            _psutil_testing = 1;
        else
            _psutil_testing = 0;
    }
    return _psutil_testing;
}


/*
 * Return True if PSUTIL_TESTING env var is set else False.
 */
PyObject *
py_psutil_testing(PyObject *self, PyObject *args) {
    PyObject *res;
    res = psutil_testing() ? Py_True : Py_False;
    Py_INCREF(res);
    return res;
}


/*
 * Backport of unicode FS APIs from Python 3.
 * On Python 2 we just return a plain byte string
 * which is never supposed to raise decoding errors.
 * See: https://github.com/giampaolo/psutil/issues/1040
 */
#if PY_MAJOR_VERSION < 3
PyObject *
PyUnicode_DecodeFSDefault(char *s) {
    return PyString_FromString(s);
}


PyObject *
PyUnicode_DecodeFSDefaultAndSize(char *s, Py_ssize_t size) {
    return PyString_FromStringAndSize(s, size);
}
#endif
