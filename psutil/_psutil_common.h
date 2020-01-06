/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

// ====================================================================
// --- Global vars / constants
// ====================================================================

extern int PSUTIL_TESTING;
extern int PSUTIL_DEBUG;
// a signaler for connections without an actual status
static const int PSUTIL_CONN_NONE = 128;

// ====================================================================
// --- Python functions and backward compatibility
// ====================================================================

#if PY_MAJOR_VERSION < 3
PyObject* PyUnicode_DecodeFSDefault(char *s);
PyObject* PyUnicode_DecodeFSDefaultAndSize(char *s, Py_ssize_t size);
#endif
PyObject* PyErr_SetFromOSErrnoWithSyscall(const char *syscall);

// ====================================================================
// --- Custom exceptions
// ====================================================================

PyObject* AccessDenied(const char *msg);
PyObject* NoSuchProcess(const char *msg);

// ====================================================================
// --- Global utils
// ====================================================================

PyObject* psutil_set_testing(PyObject *self, PyObject *args);
void psutil_debug(const char* format, ...);
int psutil_setup(void);
