/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 */

#include <windows.h>
#include <Python.h>
#include <tchar.h>

#include "../../_psutil_common.h"
#include "process_utils.h"


#define THREAD_TIMEOUT 200  // ms

// Global object shared between the 2 threads.
PUNICODE_STRING globalFileName = NULL;


static int
psutil_get_filename(LPVOID lpvParam) {
    HANDLE hFile = *((HANDLE*)lpvParam);
    NTSTATUS status;
    ULONG bufferSize;
    ULONG attempts = 8;

    bufferSize = 0x200;
    globalFileName = MALLOC_ZERO(bufferSize);

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
    DWORD dwWait = 0;
    HANDLE hThread = NULL;
    DWORD threadRetValue;

    hThread = CreateThread(NULL, 0, psutil_get_filename, &hFile, 0, NULL);
    if (hThread == NULL) {
        PyErr_SetFromOSErrnoWithSyscall("CreateThread");
        return 1;
    }

    // Wait for the worker thread to finish
    dwWait = WaitForSingleObject(hThread, THREAD_TIMEOUT);

    // If the thread hangs, kill it and cleanup.
    if (dwWait == WAIT_TIMEOUT) {
        psutil_debug(
            "get file name thread timed out after %i ms", THREAD_TIMEOUT);
        SuspendThread(hThread);
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


// Taken from Process Hacker.
int
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
            psutil_debug("SystemExtendedHandleInformation: buffer too big");
            PyErr_NoMemory();
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
            FREE(globalFileName);
            globalFileName = NULL;
        }

        // cleanup section
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
