/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>

#include "../../arch/all/init.h"

// ====================================================================
// --- Backward compatibility with missing Python.h APIs
// ====================================================================

// PyPy on Windows. Missing APIs added in PyPy 7.3.14.
#if defined(PYPY_VERSION)
#if !defined(PyErr_SetFromWindowsErrWithFilename)
PyObject *
PyErr_SetFromWindowsErrWithFilename(int winerr, const char *filename) {
    PyObject *py_exc = NULL;
    PyObject *py_winerr = NULL;

    if (winerr == 0)
        winerr = GetLastError();
    if (filename == NULL) {
        py_exc = PyObject_CallFunction(PyExc_OSError, "(is)", winerr,
                                       strerror(winerr));
    }
    else {
        py_exc = PyObject_CallFunction(PyExc_OSError, "(iss)", winerr,
                                       strerror(winerr), filename);
    }
    if (py_exc == NULL)
        return NULL;

    py_winerr = Py_BuildValue("i", winerr);
    if (py_winerr == NULL)
        goto error;
    if (PyObject_SetAttrString(py_exc, "winerror", py_winerr) != 0)
        goto error;
    PyErr_SetObject(PyExc_OSError, py_exc);
    Py_XDECREF(py_exc);
    return NULL;

error:
    Py_XDECREF(py_exc);
    Py_XDECREF(py_winerr);
    return NULL;
}
#endif  // !defined(PyErr_SetFromWindowsErrWithFilename)


#if !defined(PyErr_SetExcFromWindowsErrWithFilenameObject)
PyObject *
PyErr_SetExcFromWindowsErrWithFilenameObject(
    PyObject *type, int ierr, PyObject *filename)
{
    // Original function is too complex. Just raise OSError without
    // filename.
    return PyErr_SetFromWindowsErrWithFilename(ierr, NULL);
}
#endif // !defined(PyErr_SetExcFromWindowsErrWithFilenameObject)
#endif  // defined(PYPY_VERSION)

// ====================================================================
// --- Backward compatibility with missing Python.h APIs
// ====================================================================

// A wrapper around GetModuleHandle and GetProcAddress.
PVOID
psutil_GetProcAddress(LPCSTR libname, LPCSTR apiname) {
    HMODULE mod;
    FARPROC addr;

    if ((mod = GetModuleHandleA(libname)) == NULL) {
        psutil_debug(
            "%s module not supported (needed for %s)", libname, apiname
        );
        PyErr_SetFromWindowsErrWithFilename(0, libname);
        return NULL;
    }
    if ((addr = GetProcAddress(mod, apiname)) == NULL) {
        psutil_debug("%s -> %s API not supported", libname, apiname);
        PyErr_SetFromWindowsErrWithFilename(0, apiname);
        return NULL;
    }
    return addr;
}


// Called on module import on all platforms.
int
psutil_setup_windows(void) {
    return 0;
}
