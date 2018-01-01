/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

extern int PSUTIL_TESTING;
extern int PSUTIL_DEBUG;

// a signaler for connections without an actual status
static const int PSUTIL_CONN_NONE = 128;

#if PY_MAJOR_VERSION < 3
PyObject* PyUnicode_DecodeFSDefault(char *s);
PyObject* PyUnicode_DecodeFSDefaultAndSize(char *s, Py_ssize_t size);
#endif

PyObject* AccessDenied(char *msg);
PyObject* NoSuchProcess(char *msg);

PyObject* psutil_set_testing(PyObject *self, PyObject *args);
void psutil_debug(const char* format, ...);
void psutil_setup(void);
