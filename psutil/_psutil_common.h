/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#ifndef PSUTIL_PSUTIL_COMMON_H
#define PSUTIL_PSUTIL_COMMON_H

#include <Python.h>

extern int PSUTIL_TESTING;
extern int PSUTIL_DEBUG;

// a signaler for connections without an actual status
static const int PSUTIL_CONN_NONE = 128;

#if PY_MAJOR_VERSION < 3
PyObject* PyUnicode_DecodeFSDefault(char *s);
PyObject* PyUnicode_DecodeFSDefaultAndSize(char *s, Py_ssize_t size);
#endif

PyObject* AccessDenied(const char *msg);
PyObject* NoSuchProcess(const char *msg);
PyObject* PyErr_SetFromOSErrnoWithSyscall(const char *syscall);

PyObject* psutil_set_testing(PyObject *self, PyObject *args);
void psutil_debug(const char* format, ...);
int psutil_setup(void);

#endif // PSUTIL_PSUTIL_COMMON_H
