/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Routines common to all platforms.
 */

#include <Python.h>
#include "_psutil_common.h"

// ====================================================================
// --- Global vars
// ====================================================================

int PSUTIL_DEBUG = 0;
int PSUTIL_TESTING = 0;
// PSUTIL_CONN_NONE


// ====================================================================
// --- Backward compatibility with missing Python.h APIs
// ====================================================================

// PyPy on Windows
#if defined(PSUTIL_WINDOWS) && defined(PYPY_VERSION)
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


// PyPy 2.7
#if !defined(PyErr_SetFromWindowsErr)
PyObject *
PyErr_SetFromWindowsErr(int winerr) {
    return PyErr_SetFromWindowsErrWithFilename(winerr, "");
}
#endif  // !defined(PyErr_SetFromWindowsErr)
#endif  // defined(PSUTIL_WINDOWS) && defined(PYPY_VERSION)


// ====================================================================
// --- Custom exceptions
// ====================================================================

/*
 * Same as PyErr_SetFromErrno(0) but adds the syscall to the exception
 * message.
 */
PyObject *
PyErr_SetFromOSErrnoWithSyscall(const char *syscall) {
    char fullmsg[1024];

#ifdef PSUTIL_WINDOWS
    sprintf(fullmsg, "(originated from %s)", syscall);
    PyErr_SetFromWindowsErrWithFilename(GetLastError(), fullmsg);
#else
    PyObject *exc;
    sprintf(fullmsg, "%s (originated from %s)", strerror(errno), syscall);
    exc = PyObject_CallFunction(PyExc_OSError, "(is)", errno, fullmsg);
    PyErr_SetObject(PyExc_OSError, exc);
    Py_XDECREF(exc);
#endif
    return NULL;
}


/*
 * Set OSError(errno=ESRCH, strerror="No such process (originated from")
 * Python exception.
 */
PyObject *
NoSuchProcess(const char *syscall) {
    PyObject *exc;
    char msg[1024];

    sprintf(msg, "No such process (originated from %s)", syscall);
    exc = PyObject_CallFunction(PyExc_OSError, "(is)", ESRCH, msg);
    PyErr_SetObject(PyExc_OSError, exc);
    Py_XDECREF(exc);
    return NULL;
}


/*
 * Set OSError(errno=EACCES, strerror="Permission denied" (originated from ...)
 * Python exception.
 */
PyObject *
AccessDenied(const char *syscall) {
    PyObject *exc;
    char msg[1024];

    sprintf(msg, "Access denied (originated from %s)", syscall);
    exc = PyObject_CallFunction(PyExc_OSError, "(is)", EACCES, msg);
    PyErr_SetObject(PyExc_OSError, exc);
    Py_XDECREF(exc);
    return NULL;
}


// ====================================================================
// --- Global utils
// ====================================================================

/*
 * Enable testing mode. This has the same effect as setting PSUTIL_TESTING
 * env var. This dual method exists because updating os.environ on
 * Windows has no effect. Called on unit tests setup.
 */
PyObject *
psutil_set_testing(PyObject *self, PyObject *args) {
    PSUTIL_TESTING = 1;
    PSUTIL_DEBUG = 1;
    Py_INCREF(Py_None);
    return Py_None;
}


/*
 * Print a debug message on stderr. No-op if PSUTIL_DEBUG env var is not set.
 */
void
psutil_debug(const char* format, ...) {
    va_list argptr;
    if (PSUTIL_DEBUG) {
        va_start(argptr, format);
        fprintf(stderr, "psutil-debug> ");
        vfprintf(stderr, format, argptr);
        fprintf(stderr, "\n");
        va_end(argptr);
    }
}


/*
 * Called on module import on all platforms.
 */
int
psutil_setup(void) {
    if (getenv("PSUTIL_DEBUG") != NULL)
        PSUTIL_DEBUG = 1;
    if (getenv("PSUTIL_TESTING") != NULL)
        PSUTIL_TESTING = 1;
    return 0;
}


// ============================================================================
// Utility functions (BSD)
// ============================================================================

#if defined(PSUTIL_FREEBSD) || defined(PSUTIL_OPENBSD) || defined(PSUTIL_NETBSD)
void
convert_kvm_err(const char *syscall, char *errbuf) {
    char fullmsg[8192];

    sprintf(fullmsg, "(originated from %s: %s)", syscall, errbuf);
    if (strstr(errbuf, "Permission denied") != NULL)
        AccessDenied(fullmsg);
    else if (strstr(errbuf, "Operation not permitted") != NULL)
        AccessDenied(fullmsg);
    else
        PyErr_Format(PyExc_RuntimeError, fullmsg);
}
#endif


// ====================================================================
// --- Windows
// ====================================================================

#ifdef PSUTIL_WINDOWS
#include <windows.h>

// Needed to make these globally visible.
int PSUTIL_WINVER;
SYSTEM_INFO          PSUTIL_SYSTEM_INFO;
CRITICAL_SECTION     PSUTIL_CRITICAL_SECTION;


// A wrapper around GetModuleHandle and GetProcAddress.
PVOID
psutil_GetProcAddress(LPCSTR libname, LPCSTR procname) {
    HMODULE mod;
    FARPROC addr;

    if ((mod = GetModuleHandleA(libname)) == NULL) {
        PyErr_SetFromWindowsErrWithFilename(0, libname);
        return NULL;
    }
    if ((addr = GetProcAddress(mod, procname)) == NULL) {
        PyErr_SetFromWindowsErrWithFilename(0, procname);
        return NULL;
    }
    return addr;
}


// A wrapper around LoadLibrary and GetProcAddress.
PVOID
psutil_GetProcAddressFromLib(LPCSTR libname, LPCSTR procname) {
    HMODULE mod;
    FARPROC addr;

    Py_BEGIN_ALLOW_THREADS
    mod = LoadLibraryA(libname);
    Py_END_ALLOW_THREADS
    if (mod  == NULL) {
        PyErr_SetFromWindowsErrWithFilename(0, libname);
        return NULL;
    }
    if ((addr = GetProcAddress(mod, procname)) == NULL) {
        PyErr_SetFromWindowsErrWithFilename(0, procname);
        FreeLibrary(mod);
        return NULL;
    }
    // Causes crash.
    // FreeLibrary(mod);
    return addr;
}


/*
 * Convert a NTSTATUS value to a Win32 error code and set the proper
 * Python exception.
 */
PVOID
psutil_SetFromNTStatusErr(NTSTATUS Status, const char *syscall) {
    ULONG err;
    char fullmsg[1024];

    if (NT_NTWIN32(Status))
        err = WIN32_FROM_NTSTATUS(Status);
    else
        err = RtlNtStatusToDosErrorNoTeb(Status);
    // if (GetLastError() != 0)
    //     err = GetLastError();
    sprintf(fullmsg, "(originated from %s)", syscall);
    return PyErr_SetFromWindowsErrWithFilename(err, fullmsg);
}


static int
psutil_loadlibs() {
    // --- Mandatory
    NtQuerySystemInformation = psutil_GetProcAddressFromLib(
        "ntdll.dll", "NtQuerySystemInformation");
    if (! NtQuerySystemInformation)
        return 1;
    NtQueryInformationProcess = psutil_GetProcAddress(
        "ntdll.dll", "NtQueryInformationProcess");
    if (! NtQueryInformationProcess)
        return 1;
    NtSetInformationProcess = psutil_GetProcAddress(
        "ntdll.dll", "NtSetInformationProcess");
    if (! NtSetInformationProcess)
        return 1;
    NtQueryObject = psutil_GetProcAddressFromLib(
        "ntdll.dll", "NtQueryObject");
    if (! NtQueryObject)
        return 1;
    RtlIpv4AddressToStringA = psutil_GetProcAddressFromLib(
        "ntdll.dll", "RtlIpv4AddressToStringA");
    if (! RtlIpv4AddressToStringA)
        return 1;
    GetExtendedTcpTable = psutil_GetProcAddressFromLib(
        "iphlpapi.dll", "GetExtendedTcpTable");
    if (! GetExtendedTcpTable)
        return 1;
    GetExtendedUdpTable = psutil_GetProcAddressFromLib(
        "iphlpapi.dll", "GetExtendedUdpTable");
    if (! GetExtendedUdpTable)
        return 1;
    RtlGetVersion = psutil_GetProcAddressFromLib(
        "ntdll.dll", "RtlGetVersion");
    if (! RtlGetVersion)
        return 1;
    NtSuspendProcess = psutil_GetProcAddressFromLib(
        "ntdll", "NtSuspendProcess");
    if (! NtSuspendProcess)
        return 1;
    NtResumeProcess = psutil_GetProcAddressFromLib(
        "ntdll", "NtResumeProcess");
    if (! NtResumeProcess)
        return 1;
    NtQueryVirtualMemory = psutil_GetProcAddressFromLib(
        "ntdll", "NtQueryVirtualMemory");
    if (! NtQueryVirtualMemory)
        return 1;
    RtlNtStatusToDosErrorNoTeb = psutil_GetProcAddressFromLib(
        "ntdll", "RtlNtStatusToDosErrorNoTeb");
    if (! RtlNtStatusToDosErrorNoTeb)
        return 1;
    GetTickCount64 = psutil_GetProcAddress(
        "kernel32", "GetTickCount64");
    if (! GetTickCount64)
        return 1;
    RtlIpv6AddressToStringA = psutil_GetProcAddressFromLib(
        "ntdll.dll", "RtlIpv6AddressToStringA");
    if (! RtlIpv6AddressToStringA)
        return 1;

    // --- Optional
    // minimum requirement: Win 7
    GetActiveProcessorCount = psutil_GetProcAddress(
        "kernel32", "GetActiveProcessorCount");
    // minumum requirement: Win 7
    GetLogicalProcessorInformationEx = psutil_GetProcAddressFromLib(
        "kernel32", "GetLogicalProcessorInformationEx");
    // minimum requirements: Windows Server Core
    WTSEnumerateSessionsW = psutil_GetProcAddressFromLib(
        "wtsapi32.dll", "WTSEnumerateSessionsW");
    WTSQuerySessionInformationW = psutil_GetProcAddressFromLib(
        "wtsapi32.dll", "WTSQuerySessionInformationW");
    WTSFreeMemory = psutil_GetProcAddressFromLib(
        "wtsapi32.dll", "WTSFreeMemory");

    PyErr_Clear();
    return 0;
}


static int
psutil_set_winver() {
    RTL_OSVERSIONINFOEXW versionInfo;
    ULONG maj;
    ULONG min;

    versionInfo.dwOSVersionInfoSize = sizeof(RTL_OSVERSIONINFOEXW);
    memset(&versionInfo, 0, sizeof(RTL_OSVERSIONINFOEXW));
    RtlGetVersion((PRTL_OSVERSIONINFOW)&versionInfo);
    maj = versionInfo.dwMajorVersion;
    min = versionInfo.dwMinorVersion;
    if (maj == 6 && min == 0)
        PSUTIL_WINVER = PSUTIL_WINDOWS_VISTA;  // or Server 2008
    else if (maj == 6 && min == 1)
        PSUTIL_WINVER = PSUTIL_WINDOWS_7;
    else if (maj == 6 && min == 2)
        PSUTIL_WINVER = PSUTIL_WINDOWS_8;
    else if (maj == 6 && min == 3)
        PSUTIL_WINVER = PSUTIL_WINDOWS_8_1;
    else if (maj == 10 && min == 0)
        PSUTIL_WINVER = PSUTIL_WINDOWS_10;
    else
        PSUTIL_WINVER = PSUTIL_WINDOWS_NEW;
    return 0;
}


int
psutil_load_globals() {
    if (psutil_loadlibs() != 0)
        return 1;
    if (psutil_set_winver() != 0)
        return 1;
    GetSystemInfo(&PSUTIL_SYSTEM_INFO);
    InitializeCriticalSection(&PSUTIL_CRITICAL_SECTION);
    return 0;
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
#endif  // PSUTIL_WINDOWS
