/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

#define PSUTIL_TV2DOUBLE(t) (((t).tv_nsec * 0.000000001) + (t).tv_sec)
int psutil_file_to_struct(char *path, void *fstruct, size_t size);

PyObject *psutil_proc_basic_info(PyObject *self, PyObject *args);
PyObject *psutil_proc_environ(PyObject *self, PyObject *args);
PyObject *psutil_proc_name_and_args(PyObject *self, PyObject *args);
