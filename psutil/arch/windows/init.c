/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>

#include "../../arch/all/init.h"

// Needed to make these globally visible.
int PSUTIL_WINVER;
SYSTEM_INFO          PSUTIL_SYSTEM_INFO;
CRITICAL_SECTION     PSUTIL_CRITICAL_SECTION;

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


// A wrapper around LoadLibrary and GetProcAddress.
PVOID
psutil_GetProcAddressFromLib(LPCSTR libname, LPCSTR apiname) {
    HMODULE mod;
    FARPROC addr;

    Py_BEGIN_ALLOW_THREADS
    mod = LoadLibraryA(libname);
    Py_END_ALLOW_THREADS
    if (mod  == NULL) {
        psutil_debug("%s lib not supported (needed for %s)", libname, apiname);
        PyErr_SetFromWindowsErrWithFilename(0, libname);
        return NULL;
    }
    if ((addr = GetProcAddress(mod, apiname)) == NULL) {
        psutil_debug("%s -> %s not supported", libname, apiname);
        PyErr_SetFromWindowsErrWithFilename(0, apiname);
        FreeLibrary(mod);
        return NULL;
    }
    // Causes crash.
    // FreeLibrary(mod);
    return addr;
}



/*
 * Convert the hi and lo parts of a FILETIME structure or a LARGE_INTEGER
 * to a UNIX time.
 * A FILETIME contains a 64-bit value representing the number of
 * 100-nanosecond intervals since January 1, 1601 (UTC).
 * A UNIX time is the number of seconds that have elapsed since the
 * UNIX epoch, that is the time 00:00:00 UTC on 1 January 1970.
 */
static double
_to_unix_time(ULONGLONG hiPart, ULONGLONG loPart) {
    ULONGLONG ret;

    // 100 nanosecond intervals since January 1, 1601.
    ret = hiPart << 32;
    ret += loPart;
    // Change starting time to the Epoch (00:00:00 UTC, January 1, 1970).
    ret -= 116444736000000000ull;
    // Convert nano secs to secs.
    return (double) ret / 10000000ull;
}


double
psutil_FiletimeToUnixTime(FILETIME ft) {
    return _to_unix_time((ULONGLONG)ft.dwHighDateTime,
                         (ULONGLONG)ft.dwLowDateTime);
}


double
psutil_LargeIntegerToUnixTime(LARGE_INTEGER li) {
    return _to_unix_time((ULONGLONG)li.HighPart,
                         (ULONGLONG)li.LowPart);
}

// Called on module import on all platforms.
int
psutil_setup_windows(void) {
    GetSystemInfo(&PSUTIL_SYSTEM_INFO);
    InitializeCriticalSection(&PSUTIL_CRITICAL_SECTION);
    return 0;
}
