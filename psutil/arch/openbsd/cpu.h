/*
 * Copyright (c) 2009, Giampaolo Rodola', Landry Breuil.
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

PyObject *psutil_cpu_freq(PyObject* self, PyObject* args);
PyObject *psutil_cpu_stats(PyObject* self, PyObject* args);
PyObject *psutil_per_cpu_times(PyObject *self, PyObject *args);
