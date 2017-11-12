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
 * Return 1 if PSUTIL_TESTING env var is set or if testing mode was
 * enabled with psutil_set_testing.
 */
int
psutil_is_testing(void) {
    if (_psutil_testing == -1) {
        if (getenv("PSUTIL_TESTING") != NULL)
            _psutil_testing = 1;
        else
            _psutil_testing = 0;
    }
    return _psutil_testing;
}


/*
 * Enable testing mode. This has the same effect as setting PSUTIL_TESTING
 * env var. The dual method exists because updating os.environ on
 * Windows has no effect.
 */
PyObject *
psutil_set_testing(PyObject *self, PyObject *args) {
    _psutil_testing = 1;
    Py_INCREF(Py_None);
    return Py_None;
}
