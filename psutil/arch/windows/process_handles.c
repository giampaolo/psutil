/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

/*
 * This module retrieves handles opened by a process.
 * We use NtQuerySystemInformation to enumerate them and NtQueryObject
 * to obtain the corresponding file name.
 * Since NtQueryObject hangs for certain handle types we call it in a
 * separate thread which gets killed if it doesn't complete within 100ms.
 * This is a limitation of the Windows API and ProcessHacker uses the
 * same trick: https://github.com/giampaolo/psutil/pull/597
 *
 * CREDITS: original implementation was written by Jeff Tang.
 * It was then rewritten by Giampaolo Rodola many years later.
 * Utility functions for getting the file handles and names were re-adapted
 * from the excellent ProcessHacker.
 */

#include <windows.h>
#include <Python.h>

#include "../../_psutil_common.h"
#include "process_utils.h"


#define THREAD_TIMEOUT 100  // ms
#define STATUS_UNSUCCESSFUL ((DWORD)0xC0000001L)

typedef struct
{
  NTSTATUS status;
  HANDLE hFile;
  PUNICODE_STRING FileName;
  ULONG Length;
} psutil_query_thread;


static int
psutil_enum_handles(PSYSTEM_HANDLE_INFORMATION_EX *handles) {
    static ULONG initialBufferSize = 0x10000;
    NTSTATUS status;
    PVOID buffer;
    ULONG bufferSize;

    bufferSize = initialBufferSize;
    buffer = MALLOC_ZERO(bufferSize);
    if (buffer == NULL) {
        PyErr_NoMemory();
        return 1;
    }

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
        if (buffer == NULL) {
            PyErr_NoMemory();
            return 1;
        }
    }

    if (! NT_SUCCESS(status)) {
        psutil_SetFromNTStatusErr(status, "NtQuerySystemInformation");
        FREE(buffer);
        return 1;
    }

    *handles = (PSYSTEM_HANDLE_INFORMATION_EX)buffer;
    return 0;
}

static DWORD
psutil_get_filename(LPVOID lpvParam) {
    psutil_query_thread* context = lpvParam;

    context->status = NtQueryObject(
        context->hFile,
        ObjectNameInformation,
        context->FileName,
        context->Length,
        &context->Length);
    return 0;
}


static PUNICODE_STRING
psutil_threaded_get_filename(HANDLE hFile) {
    DWORD dwWait;
    HANDLE hThread;
    DWORD result = 0;
    ULONG attempts = 8;
    psutil_query_thread threadContext;

    threadContext.status = STATUS_UNSUCCESSFUL;
    threadContext.hFile = hFile;
    threadContext.FileName = NULL;
    threadContext.Length = 0x200;
    threadContext.FileName = MALLOC_ZERO(threadContext.Length);
    if (threadContext.FileName == NULL) {
        PyErr_NoMemory();
        return NULL;
    }

    // A loop is needed because the I/O subsystem likes to give us the
    // wrong return lengths...
    do {
        hThread = CreateThread(
            NULL, 0, (LPTHREAD_START_ROUTINE)psutil_get_filename,
            &threadContext, 0, NULL);
        if (hThread == NULL) {
            PyErr_SetFromOSErrnoWithSyscall("CreateThread");
            FREE(threadContext.FileName);
            return NULL;
        }

        // Wait for the worker thread to finish.
        dwWait = WaitForSingleObject(hThread, THREAD_TIMEOUT);

        // If the thread hangs, kill it and cleanup.
        if (dwWait == WAIT_TIMEOUT) {
            psutil_debug(
                "get handle name thread timed out after %i ms", THREAD_TIMEOUT);
            if (TerminateThread(hThread, 0) == 0) {
                PyErr_SetFromOSErrnoWithSyscall("TerminateThread");
                result = 1;
            }
        } else if (dwWait == WAIT_FAILED) {
            psutil_debug("WaitForSingleObject -> WAIT_FAILED");
            result = 1;
            if (TerminateThread(hThread, 0) == 0) {
                PyErr_SetFromOSErrnoWithSyscall(
                    "WaitForSingleObject -> WAIT_FAILED -> TerminateThread");
            } else {
                PyErr_SetFromOSErrnoWithSyscall("WaitForSingleObject");
            }
        } else if (GetExitCodeThread(hThread, &result) == 0) {
            result = 1;
            PyErr_SetFromOSErrnoWithSyscall("GetExitCodeThread");
        } else if (threadContext.status == STATUS_BUFFER_OVERFLOW ||
                threadContext.status == STATUS_INFO_LENGTH_MISMATCH ||
                threadContext.status == STATUS_BUFFER_TOO_SMALL)
        {
            FREE(threadContext.FileName);
            threadContext.FileName = MALLOC_ZERO(threadContext.Length);
            if (threadContext.FileName == NULL) {
                PyErr_NoMemory();
                CloseHandle(hThread);
                return NULL;
            }
        } else {
            CloseHandle(hThread);
            break;
        }
        CloseHandle(hThread);

    } while (--attempts && !result);

    if (result) {
        FREE(threadContext.FileName);
        return NULL;
    }

    if (! NT_SUCCESS(threadContext.status)) {
        psutil_SetFromNTStatusErr(threadContext.status, "NtQuerySystemInformation");
        FREE(threadContext.FileName);
        return NULL;
    }

    return threadContext.FileName;
}


PyObject *
psutil_get_open_files(DWORD dwPid, HANDLE hProcess) {
    PSYSTEM_HANDLE_INFORMATION_EX       handlesList = NULL;
    PSYSTEM_HANDLE_TABLE_ENTRY_INFO_EX  hHandle = NULL;
    HANDLE                              hFile = NULL;
    ULONG                               i = 0;
    BOOLEAN                             errorOccurred = FALSE;
    PyObject*                           py_path = NULL;
    PyObject*                           py_retlist = PyList_New(0);
    PUNICODE_STRING                     fileName = NULL;

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

        if (GetFileType(hFile) != FILE_TYPE_DISK) {
            SetLastError(0);
            CloseHandle(hFile);
            hFile = NULL;
            continue;
        }

        fileName = psutil_threaded_get_filename(hFile);
        if (fileName == NULL)
            goto error;

        if ((fileName != NULL) && (fileName->Length > 0)) {
            py_path = PyUnicode_FromWideChar(fileName->Buffer,
                                             wcslen(fileName->Buffer));
            if (! py_path)
                goto error;
            if (PyList_Append(py_retlist, py_path))
                goto error;
            Py_CLEAR(py_path);  // also sets to NULL
        }

        // Loop cleanup section.
        if (fileName != NULL) {
            FREE(fileName);
            fileName = NULL;
        }
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
    if (fileName != NULL)
        FREE(fileName);
    if (py_path != NULL)
        Py_DECREF(py_path);
    if (handlesList != NULL)
        FREE(handlesList);

    if (errorOccurred == TRUE)
        return NULL;
    return py_retlist;
}
