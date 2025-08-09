/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include "proc.h"
#if !defined(PSUTIL_OPENBSD) && !defined(PSUTIL_AIX)
    #include "users.h"
#endif

long psutil_getpagesize(void);
PyObject *psutil_getpagesize_pywrapper(PyObject *self, PyObject *args);
PyObject *psutil_users(PyObject *self, PyObject *args);
