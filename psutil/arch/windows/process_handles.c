/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

/*
 * This module retrieves process open handles (regular files only).
 * We use NtQuerySystemInformation to enumerate handles and NtQueryObject
 * to get the file name.
 *
 * WARNING 1: NtQueryObject may hang for certain handle types.
 * In order to work around that we spawn a thread for each handle and
 * kill it if it didn't complete within 100ms. See:
 * https://github.com/giampaolo/psutil/pull/597
 *
 * WARNING 2: this will only list files living in the C:\\ drive, see
 * https://github.com/giampaolo/psutil/pull/1020
 *
 * Most of this code was re-adapted from the excellent ProcessHacker.
 */

#include <windows.h>
#include <Python.h>

#include "../../_psutil_common.h"
#include "process_utils.h"


#define THREAD_TIMEOUT 100  // ms

// Global object shared between the 2 threads.
// XXX: this is evil but not sure how to avoid it. Python GIL is supposed
// to save us though.
PUNICODE_STRING globalFileName = NULL;


// Return a file name string given a file handle by using NtQueryObject
// which may hang on certain file types.
static int
psutil_get_filename(LPVOID lpvParam) {
    HANDLE hFile = *((HANDLE*)lpvParam);
    NTSTATUS status;
    ULONG bufferSize;
    ULONG attempts = 8;

    bufferSize = 0x200;
    globalFileName = MALLOC_ZERO(bufferSize);

    // Note: also this is supposed to hang, hence why we do it in here.
    if (GetFileType(hFile) != FILE_TYPE_DISK) {
        globalFileName->Length = 0;
        return 0;
    }

    // A loop is needed because the I/O subsystem likes to give us the
    // wrong return lengths...
    do {
        status = NtQueryObject(
            hFile,
            ObjectNameInformation,
            globalFileName,
            bufferSize,
            &bufferSize
            );
        if (status == STATUS_BUFFER_OVERFLOW ||
                status == STATUS_INFO_LENGTH_MISMATCH ||
                status == STATUS_BUFFER_TOO_SMALL)
        {
            FREE(globalFileName);
            globalFileName = MALLOC_ZERO(bufferSize);
        }
        else {
            break;
        }
    } while (--attempts);

    if (! NT_SUCCESS(status)) {
        PyErr_SetFromOSErrnoWithSyscall("NtQuerySystemInformation");
        FREE(globalFileName);
        return 1;
    }

    return 0;
}


static DWORD
psutil_threaded_get_filename(HANDLE hFile) {
    DWORD dwWait;
    HANDLE hThread;
    DWORD threadRetValue;

    hThread = CreateThread(NULL, 0, psutil_get_filename, &hFile, 0, NULL);
    if (hThread == NULL) {
        PyErr_SetFromOSErrnoWithSyscall("CreateThread");
        return 1;
    }

    // Wait for the worker thread to finish.
    dwWait = WaitForSingleObject(hThread, THREAD_TIMEOUT);

    // If the thread hangs, kill it and cleanup.
    if (dwWait == WAIT_TIMEOUT) {
        psutil_debug(
            "get file name thread timed out after %i ms", THREAD_TIMEOUT);
        TerminateThread(hThread, 1);
        CloseHandle(hThread);
        return 0;
    }
    else {
        if (GetExitCodeThread(hThread, &threadRetValue) == 0) {
            CloseHandle(hThread);
            PyErr_SetFromOSErrnoWithSyscall("GetExitCodeThread");
            return 1;
        }
        CloseHandle(hThread);
        return threadRetValue;
    }
}


static int
psutil_enum_handles(PSYSTEM_HANDLE_INFORMATION_EX *handles) {
    static ULONG initialBufferSize = 0x10000;
    NTSTATUS status;
    PVOID buffer;
    ULONG bufferSize;

    bufferSize = initialBufferSize;
    buffer = MALLOC_ZERO(bufferSize);

    while ((status = NtQuerySystemInformation(
        SystemExtendedHandleInformation,
        buffer,
        bufferSize,
        NULL
        )) == STATUS_INFO_LENGTH_MISMATCH)
    {
        FREE(buffer);
        bufferSize *= 2;

        // Fail if we're resizing the buffer to something very large.
        if (bufferSize > 256 * 1024 * 1024) {
            PyErr_SetString(
                PyExc_RuntimeError,
                "SystemExtendedHandleInformation buffer too big");
            return 1;
        }

        buffer = MALLOC_ZERO(bufferSize);
    }

    if (! NT_SUCCESS(status)) {
        psutil_SetFromNTStatusErr(status, "NtQuerySystemInformation");
        FREE(buffer);
        return 1;
    }

    *handles = (PSYSTEM_HANDLE_INFORMATION_EX)buffer;
    return 0;
}


PyObject *
psutil_get_open_files(DWORD dwPid, HANDLE hProcess) {
    PSYSTEM_HANDLE_INFORMATION_EX       handlesList = NULL;
    PSYSTEM_HANDLE_TABLE_ENTRY_INFO_EX  hHandle = NULL;
    HANDLE                              hFile = NULL;
    ULONG                               i = 0;
    BOOLEAN                             errorOccurred = FALSE;
    PyObject*                           py_path = NULL;
    PyObject*                           py_retlist = PyList_New(0);;

    if (!py_retlist)
        return NULL;
    if (psutil_enum_handles(&handlesList) != 0)
        goto error;

    for (i = 0; i < handlesList->NumberOfHandles; i++) {
        hHandle = &handlesList->Handles[i];
        if ((ULONG_PTR)hHandle->UniqueProcessId != dwPid)
            continue;
        if (! DuplicateHandle(
                hProcess,
                hHandle->HandleValue,
                GetCurrentProcess(),
                &hFile,
                0,
                TRUE,
                DUPLICATE_SAME_ACCESS))
        {
            // Will fail if not a regular file; just skip it.
            continue;
        }

        // This will set *globalFileName* global variable.
        if (psutil_threaded_get_filename(hFile) != 0)
            goto error;

        if (globalFileName->Length > 0) {
            py_path = PyUnicode_FromWideChar(globalFileName->Buffer,
                                             wcslen(globalFileName->Buffer));
            if (! py_path)
                goto error;
            if (PyList_Append(py_retlist, py_path))
                goto error;
            Py_CLEAR(py_path);  // also sets to NULL
        }

        // Loop cleanup section.
        FREE(globalFileName);
        globalFileName = NULL;
        CloseHandle(hFile);
        hFile = NULL;
    }

    goto exit;

error:
    Py_XDECREF(py_retlist);
    errorOccurred = TRUE;
    goto exit;

exit:
    if (hFile != NULL)
        CloseHandle(hFile);
    if (globalFileName != NULL) {
        FREE(globalFileName);
        globalFileName = NULL;
    }
    if (py_path != NULL)
        Py_DECREF(py_path);
    if (handlesList != NULL)
        FREE(handlesList);
    if (errorOccurred == TRUE)
        return NULL;
    return py_retlist;
}
