/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// This module retrieves handles opened by a process.
//
// We use NtQueryInformationProcess(ProcessHandleInformation) to
// enumerate them and NtQueryObject to obtain the corresponding file
// name.
//
// Directories are filtered out here too, via
// NtQueryInformationFile(FileStandardInformation), which answers from
// the handle we already have. The Python layer used to do it with
// os.stat(), which resolves the path from scratch and is a round trip
// per file on network filesystems.
//
// NtQueryObject / GetFileType block forever on pipes, console and
// other device handles with a pending blocking operation, so we call
// them in a worker thread with a timeout. The worker is created
// lazily, once per call, and reused for all the handles. On timeout
// we kill it with TerminateThread() and create a new one for the
// remaining handles. Killing it is safe because its body is strictly
// syscalls: it can't be holding the heap or loader lock, and it
// never exits on its own. The kernel wait it's stuck in is a
// UserMode wait, which termination breaks (SystemInformer has done
// the same for years). The old code deadlocked by killing a thread
// that used the heap and the Python C API, see #1967. If the killed
// thread doesn't die (never seen in practice) we abandon it and leak
// its resources.
//
// The whole design (per-process handle snapshot, object type
// pre-filter, reusable kill-on-timeout worker) mirrors what
// SystemInformer (ex Process Hacker) does when its kernel driver is
// not loaded:
// - handle enumeration: PhEnumProcessHandles in
//   https://github.com/winsiderss/systeminformer/blob/master/phlib/native.c
// - type table, name query and kill-on-timeout worker pool:
//   PhGetHandleInformationEx and PhpCallWithTimeout in
//   https://github.com/winsiderss/systeminformer/blob/master/phlib/hndlinfo.c
//
// Why the queries hang can be seen in the WRK kernel sources: they
// all wait on the FILE_OBJECT lock, which a blocking synchronous
// read holds for its whole duration. Even GetFileType, which is
// NtQueryVolumeInformationFile(FileFsDeviceInformation), acquires it
// before its no-IRP fast path:
// https://github.com/9176324/WRK/blob/master/base/ntos/io/iomgr/qsfs.c
//
// History:
// https://github.com/giampaolo/psutil/pull/597
// https://github.com/giampaolo/psutil/pull/2190
// https://github.com/giampaolo/psutil/pull/2894
//
// CREDITS: original implementation was written by Jeff Tang. It was
// then rewritten by Giampaolo Rodola many years later. Utility
// functions for getting the file handles and names were re-adapted
// from the excellent ProcessHacker / SystemInformer.

#include <windows.h>
#include <Python.h>

#include "../../arch/all/init.h"


#define THREAD_TIMEOUT 100  // ms
// How long to wait for a killed worker to actually die.
#define KILL_JOIN_TIMEOUT 1000  // ms

typedef struct {
    HANDLE hThread;
    HANDLE hStartEvent;  // auto-reset, main -> worker: work is ready
    HANDLE hDoneEvent;  // auto-reset, worker -> main: work is done
    HANDLE hFile;  // in: the handle to query
    PUNICODE_STRING fileName;  // in: caller-allocated result buffer
    ULONG bufferSize;  // in
    ULONG returnLength;  // out
    NTSTATUS status;  // out
    int quit;  // main thread asks the worker to exit
} Worker;


// ObjectTypesInformation buffer walking, adapted from SystemInformer's
// phnt headers. Entries are variable-size: each OBJECT_TYPE_INFORMATION2
// is followed by its type name buffer, padded to pointer alignment.
// clang-format off
#define ALIGN_UP_PTR(x) \
    (((ULONG_PTR)(x) + sizeof(ULONG_PTR) - 1) & ~(sizeof(ULONG_PTR) - 1))

#define FIRST_OBJECT_TYPE(types) \
    ((POBJECT_TYPE_INFORMATION2)ALIGN_UP_PTR( \
        (ULONG_PTR)(types) + sizeof(OBJECT_TYPES_INFORMATION)))

#define NEXT_OBJECT_TYPE(entry) \
    ((POBJECT_TYPE_INFORMATION2)((ULONG_PTR)(entry) \
        + sizeof(OBJECT_TYPE_INFORMATION2) \
        + ALIGN_UP_PTR((entry)->TypeName.MaximumLength)))
// clang-format on


// Find the kernel object type index for "File" handles, so that we
// can tell whether a handle refers to a file without touching it.
// The index is stable until reboot; resolve it once and cache it.
// Return 0 on success, -1 on error (Python exception set).
static int
psutil_get_file_type_index(ULONG *indexOut) {
    static ULONG cachedIndex = 0;
    NTSTATUS status;
    POBJECT_TYPES_INFORMATION typesInfo = NULL;
    POBJECT_TYPE_INFORMATION2 entry;
    ULONG bufferSize = 0x1000;
    ULONG returnLength = 0;
    ULONG i;
    int attempts = 8;

    if (cachedIndex != 0) {
        *indexOut = cachedIndex;
        return 0;
    }

    do {
        typesInfo = MALLOC_ZERO(bufferSize);
        if (typesInfo == NULL) {
            PyErr_NoMemory();
            return -1;
        }
        status = NtQueryObject(
            NULL, ObjectTypesInformation, typesInfo, bufferSize, &returnLength
        );
        if (status != STATUS_INFO_LENGTH_MISMATCH)
            break;
        FREE(typesInfo);
        typesInfo = NULL;
        bufferSize = returnLength + 0x1000;
    } while (--attempts);

    if (!NT_SUCCESS(status)) {
        psutil_SetFromNTStatusErr(status, "NtQueryObject");
        if (typesInfo != NULL)
            FREE(typesInfo);
        return -1;
    }

    entry = FIRST_OBJECT_TYPE(typesInfo);
    for (i = 0; i < typesInfo->NumberOfTypes; i++) {
        if (entry->TypeName.Length == 4 * sizeof(WCHAR)
            && memcmp(entry->TypeName.Buffer, L"File", 4 * sizeof(WCHAR)) == 0)
        {
            cachedIndex = entry->TypeIndex;
            *indexOut = cachedIndex;
            FREE(typesInfo);
            return 0;
        }
        entry = NEXT_OBJECT_TYPE(entry);
    }

    FREE(typesInfo);
    psutil_runtime_error("'File' object type not found");
    return -1;
}


static int
psutil_enum_process_handles(
    HANDLE hProcess, PPROCESS_HANDLE_SNAPSHOT_INFORMATION *snapshot
) {
    NTSTATUS status;
    PVOID buffer = NULL;
    ULONG bufferSize = 0x8000;
    DWORD returnLength = 0;
    int attempts = 8;

    do {
        // Zeroed buffer: some Windows versions return success for
        // minimal processes without writing anything, so make sure
        // NumberOfHandles reads as 0 in that case.
        buffer = MALLOC_ZERO(bufferSize);
        if (buffer == NULL) {
            PyErr_NoMemory();
            return -1;
        }
        status = NtQueryInformationProcess(
            hProcess,
            ProcessHandleInformation,
            buffer,
            bufferSize,
            &returnLength
        );
        if (status != STATUS_INFO_LENGTH_MISMATCH)
            break;
        FREE(buffer);
        buffer = NULL;
        // The handle table may grow between calls; leave some slack.
        bufferSize = returnLength + 0x1000;
    } while (--attempts);

    if (!NT_SUCCESS(status)) {
        psutil_SetFromNTStatusErr(status, "NtQueryInformationProcess");
        if (buffer != NULL)
            FREE(buffer);
        return -1;
    }

    *snapshot = (PPROCESS_HANDLE_SNAPSHOT_INFORMATION)buffer;
    return 0;
}


// Runs in a separate thread. The body is strictly syscalls: no
// Python, no heap, no CRT. The main thread may TerminateThread()
// this thread at any point between the two events, so anything that
// can hold a user-mode lock is off limits. Buffers are allocated and
// freed by the main thread, which also reports errors.
static DWORD WINAPI
psutil_worker_loop(LPVOID lpvParam) {
    Worker *w = (Worker *)lpvParam;
    FILE_STANDARD_INFORMATION info;
    IO_STATUS_BLOCK iosb;

    while (1) {
        WaitForSingleObject(w->hStartEvent, INFINITE);
        if (w->quit)
            return 0;
        w->status = 0;  // success
        // Note: also these are supposed to hang, hence why we do them
        // in here. When we skip the name query we leave the zeroed
        // buffer, meaning "no name", skipped by the caller. That's the
        // case for non-disk handles (pipes, sockets, ...), for
        // directories, for files being deleted (their path no longer
        // resolves) and for handles the query fails on (volumes, raw
        // devices).
        if (GetFileType(w->hFile) == FILE_TYPE_DISK
            && NT_SUCCESS(NtQueryInformationFile(
                w->hFile,
                &iosb,
                &info,
                sizeof(info),
                (FILE_INFORMATION_CLASS)FileStandardInformation
            ))
            && !info.Directory && !info.DeletePending)
        {
            w->status = NtQueryObject(
                w->hFile,
                ObjectNameInformation,
                w->fileName,
                w->bufferSize,
                &w->returnLength
            );
        }
        SetEvent(w->hDoneEvent);
    }
}


static Worker *
psutil_worker_create(void) {
    Worker *w;

    w = MALLOC_ZERO(sizeof(Worker));
    if (w == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    w->hStartEvent = CreateEvent(NULL, FALSE, FALSE, NULL);
    w->hDoneEvent = CreateEvent(NULL, FALSE, FALSE, NULL);
    if (w->hStartEvent == NULL || w->hDoneEvent == NULL) {
        psutil_oserror_wsyscall("CreateEvent");
        goto error;
    }
    // Small stack: the thread only issues syscalls. Keeps the cost
    // down if the worker gets stuck and leaks.
    w->hThread = CreateThread(
        NULL,
        0x10000,
        psutil_worker_loop,
        w,
        STACK_SIZE_PARAM_IS_A_RESERVATION,
        NULL
    );
    if (w->hThread == NULL) {
        psutil_oserror_wsyscall("CreateThread");
        goto error;
    }
    return w;

error:
    if (w->hStartEvent != NULL)
        CloseHandle(w->hStartEvent);
    if (w->hDoneEvent != NULL)
        CloseHandle(w->hDoneEvent);
    FREE(w);
    return NULL;
}


// Only for a live (not abandoned) worker: it's idle, so it exits
// right away and the wait is bounded.
static void
psutil_worker_destroy(Worker *w) {
    w->quit = 1;
    SetEvent(w->hStartEvent);
    WaitForSingleObject(w->hThread, INFINITE);
    CloseHandle(w->hThread);
    CloseHandle(w->hStartEvent);
    CloseHandle(w->hDoneEvent);
    FREE(w);
}


// Query the name of hFile on the worker thread, with a timeout.
// Return 0 on success (*nameOut set, may have Length 0), -1 on error
// (Python exception set), WAIT_TIMEOUT if the query got stuck. On
// WAIT_TIMEOUT the worker is killed and hFile is closed (or leaked
// if the kill fails); either way the caller must not touch hFile.
// *workerRef is reset to NULL; the next call creates a new worker.
static DWORD
psutil_worker_get_filename(
    Worker **workerRef, HANDLE hFile, PUNICODE_STRING *nameOut
) {
    Worker *w = NULL;
    DWORD dwWait;
    NTSTATUS status = 0;
    PUNICODE_STRING name = NULL;
    ULONG bufferSize = 0x200;
    ULONG attempts = 8;

    *nameOut = NULL;

    // A loop is needed because the I/O subsystem likes to give us the
    // wrong return lengths... Buffers are (re)allocated in here so
    // that the worker never touches the heap.
    do {
        name = MALLOC_ZERO(bufferSize);
        if (name == NULL) {
            PyErr_NoMemory();
            return -1;
        }

        w = *workerRef;
        if (w == NULL) {
            w = psutil_worker_create();
            if (w == NULL) {
                FREE(name);
                return -1;
            }
            *workerRef = w;
        }

        w->hFile = hFile;
        w->fileName = name;
        w->bufferSize = bufferSize;
        SetEvent(w->hStartEvent);

        dwWait = WaitForSingleObject(w->hDoneEvent, THREAD_TIMEOUT);
        if (dwWait != WAIT_OBJECT_0) {
            if (dwWait == WAIT_FAILED)
                psutil_debug("WaitForSingleObject -> WAIT_FAILED");
            psutil_debug(
                "get handle name thread timed out after %i ms; killing it",
                THREAD_TIMEOUT
            );
            // The worker is stuck in the kernel. Kill it: its body is
            // strictly syscalls, so there is no user-mode lock it can
            // orphan.
            if (!TerminateThread(w->hThread, 0))
                psutil_debug("TerminateThread -> FALSE");
            dwWait = WaitForSingleObject(w->hThread, KILL_JOIN_TIMEOUT);
            if (dwWait == WAIT_OBJECT_0) {
                // The worker is gone. It never acquired the file
                // object lock (it was stuck waiting for it), so
                // closing the handle here can't block.
                CloseHandle(w->hThread);
                CloseHandle(w->hStartEvent);
                CloseHandle(w->hDoneEvent);
                CloseHandle(w->hFile);
                FREE(w->fileName);
                FREE(w);
            }
            else {
                // Should not happen: the thread is stuck in an
                // unkillable kernel wait. Leak it, along with hFile,
                // the events and the name buffer, which the kernel
                // may still write to. The pending termination will
                // kill the thread before it ever runs user code
                // again.
                psutil_debug("killed worker did not exit; leaking it");
                CloseHandle(w->hThread);
            }
            *workerRef = NULL;
            return WAIT_TIMEOUT;
        }

        status = w->status;
        if (status == STATUS_BUFFER_OVERFLOW
            || status == STATUS_INFO_LENGTH_MISMATCH
            || status == STATUS_BUFFER_TOO_SMALL)
        {
            FREE(name);
            name = NULL;
            bufferSize = w->returnLength;
        }
        else {
            break;
        }
    } while (--attempts);

    if (!NT_SUCCESS(status)) {
        psutil_SetFromNTStatusErr(status, "NtQueryObject");
        if (name != NULL)
            FREE(name);
        return -1;
    }
    *nameOut = name;
    return 0;
}


PyObject *
psutil_get_open_files(HANDLE hProcess) {
    PPROCESS_HANDLE_SNAPSHOT_INFORMATION snapshot = NULL;
    PPROCESS_HANDLE_TABLE_ENTRY_INFO entry = NULL;
    Worker *worker = NULL;
    HANDLE hFile = NULL;
    PUNICODE_STRING fileName = NULL;
    ULONG_PTR i = 0;
    ULONG fileTypeIndex = 0;
    BOOLEAN errorOccurred = FALSE;
    DWORD dwRet;
    PyObject *py_retlist = PyList_New(0);

    if (!py_retlist)
        return NULL;

    if (psutil_get_file_type_index(&fileTypeIndex) != 0)
        goto error;
    if (psutil_enum_process_handles(hProcess, &snapshot) != 0)
        goto error;

    for (i = 0; i < snapshot->NumberOfHandles; i++) {
        entry = &snapshot->Handles[i];
        // Skip anything that is not a File object (events, keys,
        // threads, ...), which is usually most of the handles.
        if (entry->ObjectTypeIndex != fileTypeIndex)
            continue;
        if (!DuplicateHandle(
                hProcess,
                entry->HandleValue,
                GetCurrentProcess(),
                &hFile,
                0,
                TRUE,
                DUPLICATE_SAME_ACCESS
            ))
        {
            // The process may have closed it in the meantime.
            continue;
        }

        dwRet = psutil_worker_get_filename(&worker, hFile, &fileName);
        if (dwRet == WAIT_TIMEOUT) {
            // Already closed (or deliberately leaked) along with the
            // killed worker; skip this handle.
            hFile = NULL;
            continue;
        }
        if (dwRet != 0)
            goto error;

        if ((fileName != NULL) && (fileName->Length > 0)) {
            if (!pylist_append_obj(
                    py_retlist,
                    PyUnicode_FromWideChar(
                        fileName->Buffer, wcslen(fileName->Buffer)
                    )
                ))
                goto error;
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
    if (worker != NULL)
        psutil_worker_destroy(worker);
    if (hFile != NULL)
        CloseHandle(hFile);
    if (fileName != NULL)
        FREE(fileName);
    if (snapshot != NULL)
        FREE(snapshot);

    if (errorOccurred == TRUE)
        return NULL;
    return py_retlist;
}
