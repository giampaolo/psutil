/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

PyObject* AccessDenied(void);
PyObject* NoSuchProcess(void);
#if PY_MAJOR_VERSION < 3
PyObject* PyUnicode_DecodeFSDefault(char *s);
PyObject* PyUnicode_DecodeFSDefaultAndSize(char *s, Py_ssize_t size);
#endif