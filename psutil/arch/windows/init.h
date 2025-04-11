/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>

extern int PSUTIL_WINVER;

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
double psutil_FiletimeToUnixTime(FILETIME ft);
double psutil_LargeIntegerToUnixTime(LARGE_INTEGER li);
int psutil_setup_windows(void);
