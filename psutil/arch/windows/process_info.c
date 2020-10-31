/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Helper functions related to fetching process information. Used by
 * _psutil_windows module methods.
 */

#include <Python.h>
#include <windows.h>

#include "../../_psutil_common.h"
#include "process_info.h"
#include "process_utils.h"


#ifndef _WIN64
typedef NTSTATUS (NTAPI *__NtQueryInformationProcess)(
    HANDLE ProcessHandle,
    DWORD ProcessInformationClass,
    PVOID ProcessInformation,
    DWORD ProcessInformationLength,
    PDWORD ReturnLength);
#endif


/*
 * Given a pointer into a process's memory, figure out how much
 * data can be read from it.
 */
static int
psutil_get_process_region_size(HANDLE hProcess, LPCVOID src, SIZE_T *psize) {
    MEMORY_BASIC_INFORMATION info;

    if (!VirtualQueryEx(hProcess, src, &info, sizeof(info))) {
        PyErr_SetFromOSErrnoWithSyscall("VirtualQueryEx");
        return -1;
    }

    *psize = info.RegionSize - ((char*)src - (char*)info.BaseAddress);
    return 0;
}


enum psutil_process_data_kind {
    KIND_CMDLINE,
    KIND_CWD,
    KIND_ENVIRON,
};


static void
psutil_convert_winerr(ULONG err, char* syscall) {
    char fullmsg[8192];

    if (err == ERROR_NOACCESS)  {
        sprintf(
            fullmsg,
            "(originated from %s -> ERROR_NOACCESS; converted to AccessDenied)",
            syscall);
        psutil_debug(fullmsg);
        AccessDenied(fullmsg);
    }
    else {
        PyErr_SetFromOSErrnoWithSyscall(syscall);
    }
}


static void
psutil_convert_ntstatus_err(NTSTATUS status, char* syscall) {
    ULONG err;

    if (NT_NTWIN32(status))
        err = WIN32_FROM_NTSTATUS(status);
    else
        err = RtlNtStatusToDosErrorNoTeb(status);
    psutil_convert_winerr(err, syscall);
}


/*
 * Get data from the process with the given pid.  The data is returned
 * in the pdata output member as a nul terminated string which must be
 * freed on success.
 * On success 0 is returned.  On error the output parameter is not touched,
 * -1 is returned, and an appropriate Python exception is set.
 */
static int
psutil_get_process_data(DWORD pid,
                        enum psutil_process_data_kind kind,
                        WCHAR **pdata,
                        SIZE_T *psize) {
    /* This function is quite complex because there are several cases to be
       considered:

       Two cases are really simple:  we (i.e. the python interpreter) and the
       target process are both 32 bit or both 64 bit.  In that case the memory
       layout of the structures matches up and all is well.

       When we are 64 bit and the target process is 32 bit we need to use
       custom 32 bit versions of the structures.

       When we are 32 bit and the target process is 64 bit we need to use
       custom 64 bit version of the structures.  Also we need to use separate
       Wow64 functions to get the information.

       A few helper structs are defined above so that the compiler can handle
       calculating the correct offsets.

       Additional help also came from the following sources:

         https://github.com/kohsuke/winp and
         http://wj32.org/wp/2009/01/24/howto-get-the-command-line-of-processes/
         http://stackoverflow.com/a/14012919
         http://www.drdobbs.com/embracing-64-bit-windows/184401966
     */
    SIZE_T size = 0;
    HANDLE hProcess = NULL;
    LPCVOID src;
    WCHAR *buffer = NULL;
#ifdef _WIN64
    LPVOID ppeb32 = NULL;
#else
    static __NtQueryInformationProcess NtWow64QueryInformationProcess64 = NULL;
    static _NtWow64ReadVirtualMemory64 NtWow64ReadVirtualMemory64 = NULL;
    PVOID64 src64;
    BOOL weAreWow64;
    BOOL theyAreWow64;
#endif
    DWORD access = PROCESS_QUERY_INFORMATION | PROCESS_VM_READ;
    NTSTATUS status;

    hProcess = psutil_handle_from_pid(pid, access);
    if (hProcess == NULL)
        return -1;

#ifdef _WIN64
    /* 64 bit case.  Check if the target is a 32 bit process running in WoW64
     * mode. */
    status = NtQueryInformationProcess(
        hProcess,
        ProcessWow64Information,
        &ppeb32,
        sizeof(LPVOID),
        NULL);

    if (!NT_SUCCESS(status)) {
        psutil_SetFromNTStatusErr(
            status, "NtQueryInformationProcess(ProcessWow64Information)");
        goto error;
    }

    if (ppeb32 != NULL) {
        /* We are 64 bit.  Target process is 32 bit running in WoW64 mode. */
        PEB32 peb32;
        RTL_USER_PROCESS_PARAMETERS32 procParameters32;

        // read PEB
        if (!ReadProcessMemory(hProcess, ppeb32, &peb32, sizeof(peb32), NULL)) {
            // May fail with ERROR_PARTIAL_COPY, see:
            // https://github.com/giampaolo/psutil/issues/875
            psutil_convert_winerr(GetLastError(), "ReadProcessMemory");
            goto error;
        }

        // read process parameters
        if (!ReadProcessMemory(hProcess,
                               UlongToPtr(peb32.ProcessParameters),
                               &procParameters32,
                               sizeof(procParameters32),
                               NULL))
        {
            // May fail with ERROR_PARTIAL_COPY, see:
            // https://github.com/giampaolo/psutil/issues/875
            psutil_convert_winerr(GetLastError(), "ReadProcessMemory");
            goto error;
        }

        switch (kind) {
            case KIND_CMDLINE:
                src = UlongToPtr(procParameters32.CommandLine.Buffer),
                size = procParameters32.CommandLine.Length;
                break;
            case KIND_CWD:
                src = UlongToPtr(procParameters32.CurrentDirectoryPath.Buffer);
                size = procParameters32.CurrentDirectoryPath.Length;
                break;
            case KIND_ENVIRON:
                src = UlongToPtr(procParameters32.env);
                break;
        }
    } else
#else  // #ifdef _WIN64
    /* 32 bit case.  Check if the target is also 32 bit. */
    if (!IsWow64Process(GetCurrentProcess(), &weAreWow64) ||
            !IsWow64Process(hProcess, &theyAreWow64)) {
        PyErr_SetFromOSErrnoWithSyscall("IsWow64Process");
        goto error;
    }

    if (weAreWow64 && !theyAreWow64) {
        /* We are 32 bit running in WoW64 mode.  Target process is 64 bit. */
        PROCESS_BASIC_INFORMATION64 pbi64;
        PEB64 peb64;
        RTL_USER_PROCESS_PARAMETERS64 procParameters64;

        if (NtWow64QueryInformationProcess64 == NULL) {
            NtWow64QueryInformationProcess64 = \
                psutil_GetProcAddressFromLib(
                    "ntdll.dll", "NtWow64QueryInformationProcess64");
            if (NtWow64QueryInformationProcess64 == NULL) {
                PyErr_Clear();
                AccessDenied("can't query 64-bit process in 32-bit-WoW mode");
                goto error;
            }
        }
        if (NtWow64ReadVirtualMemory64 == NULL) {
            NtWow64ReadVirtualMemory64 = \
                psutil_GetProcAddressFromLib(
                    "ntdll.dll", "NtWow64ReadVirtualMemory64");
            if (NtWow64ReadVirtualMemory64 == NULL) {
                PyErr_Clear();
                AccessDenied("can't query 64-bit process in 32-bit-WoW mode");
                goto error;
            }
        }

        status = NtWow64QueryInformationProcess64(
                hProcess,
                ProcessBasicInformation,
                &pbi64,
                sizeof(pbi64),
                NULL);
        if (!NT_SUCCESS(status)) {
            psutil_convert_ntstatus_err(
                status,
                "NtWow64QueryInformationProcess64(ProcessBasicInformation)");
            goto error;
        }

        // read peb
        status = NtWow64ReadVirtualMemory64(
                hProcess,
                pbi64.PebBaseAddress,
                &peb64,
                sizeof(peb64),
                NULL);
        if (!NT_SUCCESS(status)) {
            psutil_convert_ntstatus_err(
                status, "NtWow64ReadVirtualMemory64(pbi64.PebBaseAddress)");
            goto error;
        }

        // read process parameters
        status = NtWow64ReadVirtualMemory64(
                hProcess,
                peb64.ProcessParameters,
                &procParameters64,
                sizeof(procParameters64),
                NULL);
        if (!NT_SUCCESS(status)) {
            psutil_convert_ntstatus_err(
                status, "NtWow64ReadVirtualMemory64(peb64.ProcessParameters)");
            goto error;
        }

        switch (kind) {
            case KIND_CMDLINE:
                src64 = procParameters64.CommandLine.Buffer;
                size = procParameters64.CommandLine.Length;
                break;
            case KIND_CWD:
                src64 = procParameters64.CurrentDirectoryPath.Buffer,
                size = procParameters64.CurrentDirectoryPath.Length;
                break;
            case KIND_ENVIRON:
                src64 = procParameters64.env;
                break;
        }
    } else
#endif
    /* Target process is of the same bitness as us. */
    {
        PROCESS_BASIC_INFORMATION pbi;
        PEB_ peb;
        RTL_USER_PROCESS_PARAMETERS_ procParameters;

        status = NtQueryInformationProcess(
            hProcess,
            ProcessBasicInformation,
            &pbi,
            sizeof(pbi),
            NULL);

        if (!NT_SUCCESS(status)) {
            psutil_SetFromNTStatusErr(
                status, "NtQueryInformationProcess(ProcessBasicInformation)");
            goto error;
        }


        // read peb
        if (!ReadProcessMemory(hProcess,
                               pbi.PebBaseAddress,
                               &peb,
                               sizeof(peb),
                               NULL))
        {
            // May fail with ERROR_PARTIAL_COPY, see:
            // https://github.com/giampaolo/psutil/issues/875
            psutil_convert_winerr(GetLastError(), "ReadProcessMemory");
            goto error;
        }

        // read process parameters
        if (!ReadProcessMemory(hProcess,
                               peb.ProcessParameters,
                               &procParameters,
                               sizeof(procParameters),
                               NULL))
        {
            // May fail with ERROR_PARTIAL_COPY, see:
            // https://github.com/giampaolo/psutil/issues/875
            psutil_convert_winerr(GetLastError(), "ReadProcessMemory");
            goto error;
        }

        switch (kind) {
            case KIND_CMDLINE:
                src = procParameters.CommandLine.Buffer;
                size = procParameters.CommandLine.Length;
                break;
            case KIND_CWD:
                src = procParameters.CurrentDirectoryPath.Buffer;
                size = procParameters.CurrentDirectoryPath.Length;
                break;
            case KIND_ENVIRON:
                src = procParameters.env;
                break;
        }
    }

    if (kind == KIND_ENVIRON) {
#ifndef _WIN64
        if (weAreWow64 && !theyAreWow64) {
            AccessDenied("can't query 64-bit process in 32-bit-WoW mode");
            goto error;
        }
        else
#endif
        if (psutil_get_process_region_size(hProcess, src, &size) != 0)
            goto error;
    }

    buffer = calloc(size + 2, 1);
    if (buffer == NULL) {
        PyErr_NoMemory();
        goto error;
    }

#ifndef _WIN64
    if (weAreWow64 && !theyAreWow64) {
        status = NtWow64ReadVirtualMemory64(
                hProcess,
                src64,
                buffer,
                size,
                NULL);
        if (!NT_SUCCESS(status)) {
            psutil_convert_ntstatus_err(status, "NtWow64ReadVirtualMemory64");
            goto error;
        }
    } else
#endif
    if (!ReadProcessMemory(hProcess, src, buffer, size, NULL)) {
        // May fail with ERROR_PARTIAL_COPY, see:
        // https://github.com/giampaolo/psutil/issues/875
        psutil_convert_winerr(GetLastError(), "ReadProcessMemory");
        goto error;
    }

    CloseHandle(hProcess);

    *pdata = buffer;
    *psize = size;

    return 0;

error:
    if (hProcess != NULL)
        CloseHandle(hProcess);
    if (buffer != NULL)
        free(buffer);
    return -1;
}


/*
 * Get process cmdline by using NtQueryInformationProcess. This is a
 * method alternative to PEB which is less likely to result in
 * AccessDenied. Requires Windows 8.1+.
 */
static int
psutil_cmdline_query_proc(DWORD pid, WCHAR **pdata, SIZE_T *psize) {
    HANDLE hProcess = NULL;
    ULONG bufLen = 0;
    NTSTATUS status;
    char * buffer = NULL;
    WCHAR * bufWchar = NULL;
    PUNICODE_STRING tmp = NULL;
    size_t size;
    int ProcessCommandLineInformation = 60;

    if (PSUTIL_WINVER < PSUTIL_WINDOWS_8_1) {
        PyErr_SetString(
            PyExc_RuntimeError, "requires Windows 8.1+");
        goto error;
    }

    hProcess = psutil_handle_from_pid(pid, PROCESS_QUERY_LIMITED_INFORMATION);
    if (hProcess == NULL)
        goto error;

    // get the right buf size
    status = NtQueryInformationProcess(
        hProcess,
        ProcessCommandLineInformation,
        NULL,
        0,
        &bufLen);

    // https://github.com/giampaolo/psutil/issues/1501
    if (status == STATUS_NOT_FOUND) {
        AccessDenied("NtQueryInformationProcess(ProcessBasicInformation) -> "
                     "STATUS_NOT_FOUND translated into PermissionError");
        goto error;
    }

    if (status != STATUS_BUFFER_OVERFLOW && \
            status != STATUS_BUFFER_TOO_SMALL && \
            status != STATUS_INFO_LENGTH_MISMATCH) {
        psutil_SetFromNTStatusErr(
            status, "NtQueryInformationProcess(ProcessBasicInformation)");
        goto error;
    }

    // allocate memory
    buffer = calloc(bufLen, 1);
    if (buffer == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    // get the cmdline
    status = NtQueryInformationProcess(
        hProcess,
        ProcessCommandLineInformation,
        buffer,
        bufLen,
        &bufLen
    );
    if (!NT_SUCCESS(status)) {
        psutil_SetFromNTStatusErr(
            status, "NtQueryInformationProcess(ProcessCommandLineInformation)");
        goto error;
    }

    // build the string
    tmp = (PUNICODE_STRING)buffer;
    size = wcslen(tmp->Buffer) + 1;
    bufWchar = (WCHAR *)calloc(size, sizeof(WCHAR));
    if (bufWchar == NULL) {
        PyErr_NoMemory();
        goto error;
    }
    wcscpy_s(bufWchar, size, tmp->Buffer);
    *pdata = bufWchar;
    *psize = size * sizeof(WCHAR);
    free(buffer);
    CloseHandle(hProcess);
    return 0;

error:
    if (buffer != NULL)
        free(buffer);
    if (hProcess != NULL)
        CloseHandle(hProcess);
    return -1;
}


/*
 * Return a Python list representing the arguments for the process
 * with given pid or NULL on error.
 */
PyObject *
psutil_get_cmdline(DWORD pid, int use_peb) {
    PyObject *ret = NULL;
    WCHAR *data = NULL;
    SIZE_T size;
    PyObject *py_retlist = NULL;
    PyObject *py_unicode = NULL;
    LPWSTR *szArglist = NULL;
    int nArgs, i;
    int func_ret;

    /*
    Reading the PEB to get the cmdline seem to be the best method if
    somebody has tampered with the parameters after creating the process.
    For instance, create a process as suspended, patch the command line
    in its PEB and unfreeze it. It requires more privileges than
    NtQueryInformationProcess though (the fallback):
    - https://github.com/giampaolo/psutil/pull/1398
    - https://blog.xpnsec.com/how-to-argue-like-cobalt-strike/
    */
    if (use_peb == 1)
        func_ret = psutil_get_process_data(pid, KIND_CMDLINE, &data, &size);
    else
        func_ret = psutil_cmdline_query_proc(pid, &data, &size);
    if (func_ret != 0)
        goto out;

    // attempt to parse the command line using Win32 API
    szArglist = CommandLineToArgvW(data, &nArgs);
    if (szArglist == NULL) {
        PyErr_SetFromOSErrnoWithSyscall("CommandLineToArgvW");
        goto out;
    }

    // arglist parsed as array of UNICODE_STRING, so convert each to
    // Python string object and add to arg list
    py_retlist = PyList_New(nArgs);
    if (py_retlist == NULL)
        goto out;
    for (i = 0; i < nArgs; i++) {
        py_unicode = PyUnicode_FromWideChar(szArglist[i],
            wcslen(szArglist[i]));
        if (py_unicode == NULL)
            goto out;
        PyList_SET_ITEM(py_retlist, i, py_unicode);
        py_unicode = NULL;
    }
    ret = py_retlist;
    py_retlist = NULL;

out:
    if (szArglist != NULL)
        LocalFree(szArglist);
    if (data != NULL)
        free(data);
    Py_XDECREF(py_unicode);
    Py_XDECREF(py_retlist);
    return ret;
}


PyObject *
psutil_get_cwd(DWORD pid) {
    PyObject *ret = NULL;
    WCHAR *data = NULL;
    SIZE_T size;

    if (psutil_get_process_data(pid, KIND_CWD, &data, &size) != 0)
        goto out;

    // convert wchar array to a Python unicode string
    ret = PyUnicode_FromWideChar(data, wcslen(data));

out:
    if (data != NULL)
        free(data);

    return ret;
}


/*
 * returns a Python string containing the environment variable data for the
 * process with given pid or NULL on error.
 */
PyObject *
psutil_get_environ(DWORD pid) {
    PyObject *ret = NULL;
    WCHAR *data = NULL;
    SIZE_T size;

    if (psutil_get_process_data(pid, KIND_ENVIRON, &data, &size) != 0)
        goto out;

    // convert wchar array to a Python unicode string
    ret = PyUnicode_FromWideChar(data, size / 2);

out:
    if (data != NULL)
        free(data);
    return ret;
}


/*
 * Given a process PID and a PSYSTEM_PROCESS_INFORMATION structure
 * fills the structure with various process information in one shot
 * by using NtQuerySystemInformation.
 * We use this as a fallback when faster functions fail with access
 * denied. This is slower because it iterates over all processes
 * but it doesn't require any privilege (also work for PID 0).
 * On success return 1, else 0 with Python exception already set.
 */
int
psutil_get_proc_info(DWORD pid, PSYSTEM_PROCESS_INFORMATION *retProcess,
                     PVOID *retBuffer) {
    static ULONG initialBufferSize = 0x4000;
    NTSTATUS status;
    PVOID buffer;
    ULONG bufferSize;
    PSYSTEM_PROCESS_INFORMATION process;

    bufferSize = initialBufferSize;
    buffer = malloc(bufferSize);
    if (buffer == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    while (TRUE) {
        status = NtQuerySystemInformation(
            SystemProcessInformation,
            buffer,
            bufferSize,
            &bufferSize);
        if (status == STATUS_BUFFER_TOO_SMALL ||
                status == STATUS_INFO_LENGTH_MISMATCH)
        {
            free(buffer);
            buffer = malloc(bufferSize);
            if (buffer == NULL) {
                PyErr_NoMemory();
                goto error;
            }
        }
        else {
            break;
        }
    }

    if (! NT_SUCCESS(status)) {
        psutil_SetFromNTStatusErr(
            status, "NtQuerySystemInformation(SystemProcessInformation)");
        goto error;
    }

    if (bufferSize <= 0x20000)
        initialBufferSize = bufferSize;

    process = PSUTIL_FIRST_PROCESS(buffer);
    do {
        if ((ULONG_PTR)process->UniqueProcessId == pid) {
            *retProcess = process;
            *retBuffer = buffer;
            return 1;
        }
    } while ((process = PSUTIL_NEXT_PROCESS(process)));

    NoSuchProcess("NtQuerySystemInformation (no PID found)");
    goto error;

error:
    if (buffer != NULL)
        free(buffer);
    return 0;
}


/*
 * Get various process information by using NtQuerySystemInformation.
 * We use this as a fallback when faster functions fail with access
 * denied. This is slower because it iterates over all processes.
 * Returned tuple includes the following process info:
 *
 * - num_threads()
 * - ctx_switches()
 * - num_handles() (fallback)
 * - cpu_times() (fallback)
 * - create_time() (fallback)
 * - io_counters() (fallback)
 * - memory_info() (fallback)
 */
PyObject *
psutil_proc_info(PyObject *self, PyObject *args) {
    DWORD pid;
    PSYSTEM_PROCESS_INFORMATION process;
    PVOID buffer;
    ULONG i;
    ULONG ctx_switches = 0;
    double user_time;
    double kernel_time;
    double create_time;
    PyObject *py_retlist;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (! psutil_get_proc_info(pid, &process, &buffer))
        return NULL;

    for (i = 0; i < process->NumberOfThreads; i++)
        ctx_switches += process->Threads[i].ContextSwitches;
    user_time = (double)process->UserTime.HighPart * HI_T + \
                (double)process->UserTime.LowPart * LO_T;
    kernel_time = (double)process->KernelTime.HighPart * HI_T + \
                    (double)process->KernelTime.LowPart * LO_T;

    // Convert the LARGE_INTEGER union to a Unix time.
    // It's the best I could find by googling and borrowing code here
    // and there. The time returned has a precision of 1 second.
    if (0 == pid || 4 == pid) {
        // the python module will translate this into BOOT_TIME later
        create_time = 0;
    }
    else {
        create_time = psutil_LargeIntegerToUnixTime(process->CreateTime);
    }

    py_retlist = Py_BuildValue(
#if defined(_WIN64)
        "kkdddkKKKKKK" "kKKKKKKKKK",
#else
        "kkdddkKKKKKK" "kIIIIIIIII",
#endif
        process->HandleCount,                   // num handles
        ctx_switches,                           // num ctx switches
        user_time,                              // cpu user time
        kernel_time,                            // cpu kernel time
        create_time,                            // create time
        process->NumberOfThreads,               // num threads
        // IO counters
        process->ReadOperationCount.QuadPart,   // io rcount
        process->WriteOperationCount.QuadPart,  // io wcount
        process->ReadTransferCount.QuadPart,    // io rbytes
        process->WriteTransferCount.QuadPart,   // io wbytes
        process->OtherOperationCount.QuadPart,  // io others count
        process->OtherTransferCount.QuadPart,   // io others bytes
        // memory
        process->PageFaultCount,                // num page faults
        process->PeakWorkingSetSize,            // peak wset
        process->WorkingSetSize,                // wset
        process->QuotaPeakPagedPoolUsage,       // peak paged pool
        process->QuotaPagedPoolUsage,           // paged pool
        process->QuotaPeakNonPagedPoolUsage,    // peak non paged pool
        process->QuotaNonPagedPoolUsage,        // non paged pool
        process->PagefileUsage,                 // pagefile
        process->PeakPagefileUsage,             // peak pagefile
        process->PrivatePageCount               // private
    );

    free(buffer);
    return py_retlist;
}
