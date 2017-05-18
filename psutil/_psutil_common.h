/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

// a signaler for connections without an actual status
static const int PSUTIL_CONN_NONE = 128;

PyObject* AccessDenied(void);
PyObject* NoSuchProcess(void);
int psutil_testing(void);
PyObject* py_psutil_testing(PyObject *self, PyObject *args);
#if PY_MAJOR_VERSION < 3
PyObject* PyUnicode_DecodeFSDefault(char *s);
PyObject* PyUnicode_DecodeFSDefaultAndSize(char *s, Py_ssize_t size);
#endif
