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
// --- Global vars / constants
// ====================================================================


int PSUTIL_DEBUG = 0;
int PSUTIL_TESTING = 0;
// PSUTIL_CONN_NONE


// ====================================================================
// --- Python functions and backward compatibility
// ====================================================================

/*
 * Backport of unicode FS APIs from Python 3.
 * On Python 2 we just return a plain byte string
 * which is never supposed to raise decoding errors.
 * See: https://github.com/giampaolo/psutil/issues/1040
 */
#if PY_MAJOR_VERSION < 3
PyObject *
PyUnicode_DecodeFSDefault(char *s) {
    return PyString_FromString(s);
}


PyObject *
PyUnicode_DecodeFSDefaultAndSize(char *s, Py_ssize_t size) {
    return PyString_FromStringAndSize(s, size);
}
#endif

/*
 * Same as PyErr_SetFromErrno(0) but adds the syscall to the exception
 * message.
 */
PyObject *
PyErr_SetFromOSErrnoWithSyscall(const char *syscall) {
    char fullmsg[1024];

#ifdef _WIN32
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


// ====================================================================
// --- Custom exceptions
// ====================================================================

/*
 * Set OSError(errno=ESRCH, strerror="No such process") Python exception.
 * If msg != "" the exception message will change in accordance.
 */
PyObject *
NoSuchProcess(const char *msg) {
    PyObject *exc;
    exc = PyObject_CallFunction(
        PyExc_OSError, "(is)", ESRCH, strlen(msg) ? msg : strerror(ESRCH));
    PyErr_SetObject(PyExc_OSError, exc);
    Py_XDECREF(exc);
    return NULL;
}


/*
 * Set OSError(errno=EACCES, strerror="Permission denied") Python exception.
 * If msg != "" the exception message will change in accordance.
 */
PyObject *
AccessDenied(const char *msg) {
    PyObject *exc;
    exc = PyObject_CallFunction(
        PyExc_OSError, "(is)", EACCES, strlen(msg) ? msg : strerror(EACCES));
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


// ====================================================================
// --- Windows
// ====================================================================

#ifdef PSUTIL_WINDOWS
#include <windows.h>

// Needed to make these globally visible.
int PSUTIL_WINVER;
SYSTEM_INFO          PSUTIL_SYSTEM_INFO;
CRITICAL_SECTION     PSUTIL_CRITICAL_SECTION;

#define NT_FACILITY_MASK 0xfff
#define NT_FACILITY_SHIFT 16
#define NT_FACILITY(Status) \
    ((((ULONG)(Status)) >> NT_FACILITY_SHIFT) & NT_FACILITY_MASK)
#define NT_NTWIN32(status) (NT_FACILITY(Status) == FACILITY_WIN32)
#define WIN32_FROM_NTSTATUS(Status) (((ULONG)(Status)) & 0xffff)


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
    if (NtQuerySystemInformation == NULL)
        return 1;
    NtQueryInformationProcess = psutil_GetProcAddress(
        "ntdll.dll", "NtQueryInformationProcess");
    if (! NtQueryInformationProcess)
        return 1;
    NtSetInformationProcess = psutil_GetProcAddress(
        "ntdll.dll", "NtSetInformationProcess");
    if (! NtSetInformationProcess)
        return 1;
    WinStationQueryInformationW = psutil_GetProcAddressFromLib(
        "winsta.dll", "WinStationQueryInformationW");
    if (! WinStationQueryInformationW)
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

    // --- Optional
    // not available on Wine
    RtlIpv6AddressToStringA = psutil_GetProcAddressFromLib(
        "ntdll.dll", "RtlIpv6AddressToStringA");
    // minimum requirement: Win Vista
    GetTickCount64 = psutil_GetProcAddress(
        "kernel32", "GetTickCount64");
    // minimum requirement: Win 7
    GetActiveProcessorCount = psutil_GetProcAddress(
        "kernel32", "GetActiveProcessorCount");
    // minumum requirement: Win 7
    GetLogicalProcessorInformationEx = psutil_GetProcAddressFromLib(
        "kernel32", "GetLogicalProcessorInformationEx");

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
#endif  // PSUTIL_WINDOWS
