/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#if !defined(__PROCESS_INFO_H)
#define __PROCESS_INFO_H

#include <Python.h>
#include <windows.h>
#include "security.h"
#include "ntextapi.h"

#define HANDLE_TO_PYNUM(handle) PyLong_FromUnsignedLong((unsigned long) handle)
#define PYNUM_TO_HANDLE(obj) ((HANDLE)PyLong_AsUnsignedLong(obj))

#ifdef PSUTIL_CYGWIN
    /* Python on Cygwin does not have PyErr_SetFromWindowsError, or the
     * WindowsError exception class.  So instead we raise a normal OSError
     * with errno mapped from the Windows error using the cygwin_internal
     * API to provide the mapping. */
    #include <sys/cygwin.h>
    #include <sys/errno.h>
    #define PyErr_SetFromWindowsErr(ierr) ({ \
        errno = (int) cygwin_internal(CW_GET_ERRNO_FROM_WINERROR, \
                                      ((ierr) ? (ierr) : GetLastError())); \
        PyErr_SetFromErrno(PyExc_OSError); \
    })
#endif

DWORD* psutil_get_pids(DWORD *numberOfReturnedPIDs);
HANDLE psutil_handle_from_pid(DWORD pid);
HANDLE psutil_handle_from_pid_waccess(DWORD pid, DWORD dwDesiredAccess);
PyObject* psutil_win32_OpenProcess(PyObject *self, PyObject *args);
PyObject* psutil_win32_CloseHandle(PyObject *self, PyObject *args);

int psutil_handlep_is_running(HANDLE hProcess);
int psutil_pid_in_proclist(DWORD pid);
int psutil_pid_is_running(DWORD pid);
PyObject* psutil_get_cmdline(long pid);
PyObject* psutil_get_cwd(long pid);
PyObject* psutil_get_environ(long pid);
int psutil_get_proc_info(DWORD pid, PSYSTEM_PROCESS_INFORMATION *retProcess,
                         PVOID *retBuffer);

#endif
