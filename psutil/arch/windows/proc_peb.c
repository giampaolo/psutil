/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// Process cmdline(), cwd() and environ() implementations. All three
// live in the process PEB (Process Environment Block), which we read
// with ReadProcessMemory(). cmdline() can also avoid the PEB and use
// NtQueryInformationProcess() instead, see psutil_proc_cmdline().

#include <Python.h>
#include <windows.h>

#include "../../arch/all/init.h"


// Given a pointer into a process's memory, figure out how much data
// can be read from it.
static int
psutil_get_process_region_size(HANDLE hProcess, LPCVOID src, SIZE_T *psize) {
    MEMORY_BASIC_INFORMATION info;

    if (!VirtualQueryEx(hProcess, src, &info, sizeof(info))) {
        psutil_oserror_wsyscall("VirtualQueryEx");
        return -1;
    }

    *psize = info.RegionSize - ((char *)src - (char *)info.BaseAddress);
    return 0;
}


enum psutil_process_data_kind {
    KIND_CMDLINE,
    KIND_CWD,
    KIND_ENVIRON,
};


// Read a chunk of another process's memory. On error set a Python
// exception and return -1. May fail with ERROR_NOACCESS (turned into
// AccessDenied) or ERROR_PARTIAL_COPY, see:
// https://github.com/giampaolo/psutil/issues/875
static int
psutil_read_proc_mem(HANDLE hProcess, LPCVOID src, LPVOID dst, SIZE_T size) {
    if (!ReadProcessMemory(hProcess, src, dst, size, NULL)) {
        if (GetLastError() == ERROR_NOACCESS) {
            psutil_debug("ReadProcessMemory -> ERROR_NOACCESS");
            psutil_oserror_ad("ReadProcessMemory -> ERROR_NOACCESS");
        }
        else {
            psutil_oserror_wsyscall("ReadProcessMemory");
        }
        return -1;
    }
    return 0;
}


// Get data from the process with the given pid.  The data is returned
// in the pdata output member as a nul terminated string which must be
// freed on success. On success 0 is returned.  On error the output
// parameter is not touched, -1 is returned, and an appropriate Python
// exception is set.
static int
psutil_get_process_data(
    DWORD pid, enum psutil_process_data_kind kind, WCHAR **pdata, SIZE_T *psize
) {
    /* Several cases to consider:

       We (i.e. the python interpreter) and the target process are of
       the same bitness: the memory layout of the structures matches
       up and all is well.

       We are 64 bit and the target process is 32 bit (WoW64): we use
       custom 32 bit versions of the structures.

       We are 32 bit and the target process is 64 bit: we give up and
       raise AccessDenied (it would require the undocumented NtWow64*
       APIs).

       See: https://github.com/giampaolo/psutil/issues/2889

       Additional help came from:

         https://github.com/kohsuke/winp
         http://wj32.org/wp/2009/01/24/howto-get-the-command-line-of-processes/
     */
    SIZE_T size = 0;
    HANDLE hProcess = NULL;
    LPCVOID src;
    WCHAR *buffer = NULL;
#ifdef _WIN64
    LPVOID ppeb32 = NULL;
#else
    BOOL weAreWow64;
    BOOL theyAreWow64;
#endif
    DWORD access = PROCESS_QUERY_INFORMATION | PROCESS_VM_READ;
    NTSTATUS status;

    hProcess = psutil_handle_from_pid(pid, access);
    if (hProcess == NULL)
        return -1;

#ifdef _WIN64
    // 64 bit case.  Check if the target is a 32 bit process running in
    // WoW64 mode.
    status = NtQueryInformationProcess(
        hProcess, ProcessWow64Information, &ppeb32, sizeof(LPVOID), NULL
    );

    if (!NT_SUCCESS(status)) {
        psutil_SetFromNTStatusErr(
            status, "NtQueryInformationProcess(ProcessWow64Information)"
        );
        goto error;
    }

    if (ppeb32 != NULL) {
        // We are 64 bit.  Target process is 32 bit running in WoW64 mode.
        PEB32 peb32;
        RTL_USER_PROCESS_PARAMETERS32 procParameters32;

        // read PEB
        if (psutil_read_proc_mem(hProcess, ppeb32, &peb32, sizeof(peb32)) != 0)
            goto error;

        // read process parameters
        if (psutil_read_proc_mem(
                hProcess,
                UlongToPtr(peb32.ProcessParameters),
                &procParameters32,
                sizeof(procParameters32)
            )
            != 0)
        {
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
    }
    else
#else  // #ifdef _WIN64
    // We are 32 bit. If the target is 64 bit we give up: reading its
    // memory would require the undocumented NtWow64* APIs.
    if (!IsWow64Process(GetCurrentProcess(), &weAreWow64)
        || !IsWow64Process(hProcess, &theyAreWow64))
    {
        psutil_oserror_wsyscall("IsWow64Process");
        goto error;
    }

    if (weAreWow64 && !theyAreWow64) {
        psutil_oserror_ad("can't query 64-bit process from 32-bit psutil");
        goto error;
    }
#endif
    // Target process is of the same bitness as us.
    {
        PROCESS_BASIC_INFORMATION pbi;
        PEB_ peb;
        RTL_USER_PROCESS_PARAMETERS_ procParameters;

        status = NtQueryInformationProcess(
            hProcess, ProcessBasicInformation, &pbi, sizeof(pbi), NULL
        );

        if (!NT_SUCCESS(status)) {
            psutil_SetFromNTStatusErr(
                status, "NtQueryInformationProcess(ProcessBasicInformation)"
            );
            goto error;
        }


        // read peb
        if (psutil_read_proc_mem(
                hProcess, pbi.PebBaseAddress, &peb, sizeof(peb)
            )
            != 0)
        {
            goto error;
        }

        // read process parameters
        if (psutil_read_proc_mem(
                hProcess,
                peb.ProcessParameters,
                &procParameters,
                sizeof(procParameters)
            )
            != 0)
        {
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
        if (psutil_get_process_region_size(hProcess, src, &size) != 0)
            goto error;
    }

    buffer = calloc(size + 2, 1);
    if (buffer == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    if (psutil_read_proc_mem(hProcess, src, buffer, size) != 0)
        goto error;

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


// Get process cmdline by using NtQueryInformationProcess. This is a
// method alternative to PEB which is less likely to result in
// AccessDenied.
static int
psutil_cmdline_query_proc(DWORD pid, WCHAR **pdata, SIZE_T *psize) {
    HANDLE hProcess = NULL;
    ULONG bufLen = 0;
    NTSTATUS status;
    char *buffer = NULL;
    WCHAR *bufWchar = NULL;
    PUNICODE_STRING tmp = NULL;
    size_t size;

    hProcess = psutil_handle_from_pid(pid, PROCESS_QUERY_LIMITED_INFORMATION);
    if (hProcess == NULL)
        goto error;

    // get the right buf size
    status = NtQueryInformationProcess(
        hProcess, ProcessCommandLineInformation, NULL, 0, &bufLen
    );

    // https://github.com/giampaolo/psutil/issues/1501
    if (status == STATUS_NOT_FOUND) {
        psutil_oserror_ad(
            "NtQueryInformationProcess(ProcessCommandLineInformation) -> "
            "STATUS_NOT_FOUND"
        );
        goto error;
    }

    if (status != STATUS_BUFFER_OVERFLOW && status != STATUS_BUFFER_TOO_SMALL
        && status != STATUS_INFO_LENGTH_MISMATCH)
    {
        psutil_SetFromNTStatusErr(
            status, "NtQueryInformationProcess(ProcessCommandLineInformation)"
        );
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
        hProcess, ProcessCommandLineInformation, buffer, bufLen, &bufLen
    );
    if (!NT_SUCCESS(status)) {
        psutil_SetFromNTStatusErr(
            status, "NtQueryInformationProcess(ProcessCommandLineInformation)"
        );
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
    if (bufWchar != NULL)
        free(bufWchar);
    if (hProcess != NULL)
        CloseHandle(hProcess);
    return -1;
}


PyObject *
psutil_proc_cmdline(PyObject *self, PyObject *args, PyObject *kwdict) {
    WCHAR *data = NULL;
    LPWSTR *szArglist = NULL;
    SIZE_T size;
    int nArgs;
    int i;
    int func_ret;
    DWORD pid;
    int use_peb = 1;
    PyObject *py_retlist = NULL;
    PyObject *py_unicode = NULL;
    static char *keywords[] = {"pid", "use_peb", NULL};

    if (!PyArg_ParseTupleAndKeywords(
            args, kwdict, _Py_PARSE_PID "|p", keywords, &pid, &use_peb
        ))
    {
        return NULL;
    }
    if ((pid == 0) || (pid == 4))
        return Py_BuildValue("[]");

    if (psutil_check_pid_running(pid) != 0)
        return NULL;

    // Reading the PEB to get the cmdline seem to be the best method if
    // somebody has tampered with the parameters after creating the
    // process. For instance, create a process as suspended, patch the
    // command line in its PEB and unfreeze it. It requires more
    // privileges than NtQueryInformationProcess though (the fallback):
    // - https://github.com/giampaolo/psutil/pull/1398
    // - https://blog.xpnsec.com/how-to-argue-like-cobalt-strike/
    if (use_peb == 1)
        func_ret = psutil_get_process_data(pid, KIND_CMDLINE, &data, &size);
    else
        func_ret = psutil_cmdline_query_proc(pid, &data, &size);
    if (func_ret != 0)
        goto error;

    // attempt to parse the command line using Win32 API
    szArglist = CommandLineToArgvW(data, &nArgs);
    if (szArglist == NULL) {
        psutil_oserror_wsyscall("CommandLineToArgvW");
        goto error;
    }

    // arglist parsed as array of UNICODE_STRING, so convert each to
    // Python string object and add to arg list
    py_retlist = PyList_New(nArgs);
    if (py_retlist == NULL)
        goto error;
    for (i = 0; i < nArgs; i++) {
        py_unicode = PyUnicode_FromWideChar(
            szArglist[i], wcslen(szArglist[i])
        );
        if (py_unicode == NULL)
            goto error;
        PyList_SetItem(py_retlist, i, py_unicode);
        py_unicode = NULL;
    }

    LocalFree(szArglist);
    free(data);
    return py_retlist;

error:
    if (szArglist != NULL)
        LocalFree(szArglist);
    if (data != NULL)
        free(data);
    Py_XDECREF(py_unicode);
    Py_XDECREF(py_retlist);
    return NULL;
}


PyObject *
psutil_proc_cwd(PyObject *self, PyObject *args) {
    DWORD pid;
    PyObject *ret = NULL;
    WCHAR *data = NULL;
    SIZE_T size;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    if (psutil_check_pid_running(pid) != 0)
        return NULL;

    if (psutil_get_process_data(pid, KIND_CWD, &data, &size) != 0)
        goto out;

    // convert wchar array to a Python unicode string
    ret = PyUnicode_FromWideChar(data, wcslen(data));

out:
    if (data != NULL)
        free(data);

    return ret;
}


PyObject *
psutil_proc_environ(PyObject *self, PyObject *args) {
    DWORD pid;
    WCHAR *data = NULL;
    SIZE_T size;
    PyObject *ret = NULL;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if ((pid == 0) || (pid == 4))
        return PyUnicode_FromString("");

    if (psutil_check_pid_running(pid) != 0)
        return NULL;

    if (psutil_get_process_data(pid, KIND_ENVIRON, &data, &size) != 0)
        goto out;

    // convert wchar array to a Python unicode string
    ret = PyUnicode_FromWideChar(data, size / 2);

out:
    if (data != NULL)
        free(data);
    return ret;
}
