/*
 * Copyright (c) 2009, itachee. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * OS X CPU temp reading using SMC.
 * Can be extended for more sensors in future
 */

#ifndef __OSX_SPECIFIC_H
#define __OSX_SPECIFIC_H
#include <Python.h>
PyObject* psutil_sensors_cpu_temperature(PyObject* self, PyObject* args);

#endif
