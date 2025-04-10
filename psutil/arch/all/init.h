/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

// ====================================================================
// --- Global vars
// ====================================================================

extern int PSUTIL_DEBUG;

// ====================================================================
// --- Global utils
// ====================================================================

PyObject* psutil_set_debug(PyObject *self, PyObject *args);

// Print a debug message on stderr.
#define psutil_debug(...) do { \
    if (! PSUTIL_DEBUG) \
        break; \
    fprintf(stderr, "psutil-debug [%s:%d]> ", __FILE__, __LINE__); \
    fprintf(stderr, __VA_ARGS__); \
    fprintf(stderr, "\n");} while(0)
