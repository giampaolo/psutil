/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>

#if defined(PSUTIL_WINDOWS) && defined(PYPY_VERSION)
    #if !defined(PyErr_SetFromWindowsErrWithFilename)
        PyObject *PyErr_SetFromWindowsErrWithFilename(
            int ierr, const char *filename
        );
    #endif
    #if !defined(PyErr_SetExcFromWindowsErrWithFilenameObject)
        PyObject *PyErr_SetExcFromWindowsErrWithFilenameObject(
            PyObject *type, int ierr, PyObject *filename
        );
    #endif
#endif

PVOID psutil_GetProcAddress(LPCSTR libname, LPCSTR procname);
PVOID psutil_GetProcAddressFromLib(LPCSTR libname, LPCSTR procname);
int psutil_setup_windows(void);
