/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Windows platform-specific module methods for _psutil_mswindows
 */

// Fixes clash between winsock2.h and windows.h
#define WIN32_LEAN_AND_MEAN

#include <Python.h>
#include <windows.h>
#include <Psapi.h>
#include <time.h>
#include <lm.h>
#include <WinIoCtl.h>
#include <tchar.h>
#include <tlhelp32.h>
#include <winsock2.h>
#include <iphlpapi.h>
#include <wtsapi32.h>

// Link with Iphlpapi.lib
#pragma comment(lib, "IPHLPAPI.lib")

#include "_psutil_mswindows.h"
#include "_psutil_common.h"
#include "arch/mswindows/security.h"
#include "arch/mswindows/process_info.h"
#include "arch/mswindows/process_handles.h"
#include "arch/mswindows/ntextapi.h"


/*
 * Return a Python float representing the system uptime expressed in seconds
 * since the epoch.
 */
static PyObject*
get_system_boot_time(PyObject* self, PyObject* args)
{
    double uptime;
    time_t pt;
    FILETIME fileTime;
    long long ll;

    GetSystemTimeAsFileTime(&fileTime);

    /*
    HUGE thanks to:
    http://johnstewien.spaces.live.com/blog/cns!E6885DB5CEBABBC8!831.entry

    This function converts the FILETIME structure to the 32 bit
    Unix time structure.
    The time_t is a 32-bit value for the number of seconds since
    January 1, 1970. A FILETIME is a 64-bit for the number of
    100-nanosecond periods since January 1, 1601. Convert by
    subtracting the number of 100-nanosecond period betwee 01-01-1970
    and 01-01-1601, from time_t the divide by 1e+7 to get to the same
    base granularity.
    */
    ll = (((LONGLONG)(fileTime.dwHighDateTime)) << 32) + fileTime.dwLowDateTime;
    pt = (time_t)((ll - 116444736000000000ull) / 10000000ull);

    // XXX - By using GetTickCount() time will wrap around to zero if the
    // system is run continuously for 49.7 days.
    uptime = GetTickCount() / 1000.00f;
    return Py_BuildValue("d", (double)pt - uptime);
}


/*
 * Return 1 if PID exists in the current process list, else 0.
 */
static PyObject*
pid_exists(PyObject* self, PyObject* args)
{
    long pid;
    int status;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }

    status = psutil_pid_is_running(pid);
    if (-1 == status) {
        return NULL; // exception raised in psutil_pid_is_running()
    }
    return PyBool_FromLong(status);
}


/*
 * Return a Python list of all the PIDs running on the system.
 */
static PyObject*
get_pid_list(PyObject* self, PyObject* args)
{
    DWORD *proclist = NULL;
    DWORD numberOfReturnedPIDs;
    DWORD i;
    PyObject* pid = NULL;
    PyObject* retlist = PyList_New(0);

    if (retlist == NULL) {
        return NULL;
    }
    proclist = psutil_get_pids(&numberOfReturnedPIDs);
    if (NULL == proclist) {
        goto error;
    }

    for (i = 0; i < numberOfReturnedPIDs; i++) {
        pid = Py_BuildValue("I", proclist[i]);
        if (!pid)
            goto error;
        if (PyList_Append(retlist, pid))
            goto error;
        Py_DECREF(pid);
    }

    // free C array allocated for PIDs
    free(proclist);
    return retlist;

error:
    Py_XDECREF(pid);
    Py_DECREF(retlist);
    if (proclist != NULL)
        free(proclist);
    return NULL;
}


/*
 * Kill a process given its PID.
 */
static PyObject*
kill_process(PyObject* self, PyObject* args)
{
    HANDLE hProcess;
    long pid;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (pid == 0) {
        return AccessDenied();
    }

    hProcess = OpenProcess(PROCESS_TERMINATE, FALSE, pid);
    if (hProcess == NULL) {
        if (GetLastError() == ERROR_INVALID_PARAMETER) {
            // see http://code.google.com/p/psutil/issues/detail?id=24
            NoSuchProcess();
        }
        else {
            PyErr_SetFromWindowsErr(0);
        }
        return NULL;
    }

    // kill the process
    if (! TerminateProcess(hProcess, 0)) {
        PyErr_SetFromWindowsErr(0);
        CloseHandle(hProcess);
        return NULL;
    }

    CloseHandle(hProcess);
    Py_INCREF(Py_None);
    return Py_None;
}


/*
 * Wait for process to terminate and return its exit code.
 */
static PyObject*
process_wait(PyObject* self, PyObject* args)
{
    HANDLE hProcess;
    DWORD ExitCode;
    DWORD retVal;
    long pid;
    long timeout;

    if (! PyArg_ParseTuple(args, "ll", &pid, &timeout)) {
        return NULL;
    }
    if (pid == 0) {
        return AccessDenied();
    }

    hProcess = OpenProcess(SYNCHRONIZE | PROCESS_QUERY_INFORMATION, FALSE, pid);
    if (hProcess == NULL) {
        if (GetLastError() == ERROR_INVALID_PARAMETER) {
            // no such process; we do not want to raise NSP but
            // return None instead.
            Py_INCREF(Py_None);
            return Py_None;
        }
        else {
            PyErr_SetFromWindowsErr(0);
            return NULL;
        }
    }

    // wait until the process has terminated
    Py_BEGIN_ALLOW_THREADS
    retVal = WaitForSingleObject(hProcess, timeout);
    Py_END_ALLOW_THREADS

    if (retVal == WAIT_FAILED) {
        CloseHandle(hProcess);
        return PyErr_SetFromWindowsErr(GetLastError());
    }
    if (retVal == WAIT_TIMEOUT) {
        CloseHandle(hProcess);
        return Py_BuildValue("l", WAIT_TIMEOUT);
    }

    // get the exit code; note: subprocess module (erroneously?) uses
    // what returned by WaitForSingleObject
    if (GetExitCodeProcess(hProcess, &ExitCode) == 0) {
        CloseHandle(hProcess);
        return PyErr_SetFromWindowsErr(GetLastError());
    }
    CloseHandle(hProcess);
#if PY_MAJOR_VERSION >= 3
    return PyLong_FromLong((long) ExitCode);
#else
    return PyInt_FromLong((long) ExitCode);
#endif
}


/*
 * Return a Python tuple (user_time, kernel_time)
 */
static PyObject*
get_process_cpu_times(PyObject* self, PyObject* args)
{
    long        pid;
    HANDLE      hProcess;
    FILETIME    ftCreate, ftExit, ftKernel, ftUser;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }

    hProcess = psutil_handle_from_pid(pid);
    if (hProcess == NULL) {
        return NULL;
    }

    if (! GetProcessTimes(hProcess, &ftCreate, &ftExit, &ftKernel, &ftUser)) {
        CloseHandle(hProcess);
        if (GetLastError() == ERROR_ACCESS_DENIED) {
            // usually means the process has died so we throw a NoSuchProcess
            // here
            return NoSuchProcess();
        }
        else {
            PyErr_SetFromWindowsErr(0);
            return NULL;
        }
    }

    CloseHandle(hProcess);

    /*
    user and kernel times are represented as a FILETIME structure wich contains
    a 64-bit value representing the number of 100-nanosecond intervals since
    January 1, 1601 (UTC).
    http://msdn.microsoft.com/en-us/library/ms724284(VS.85).aspx

    To convert it into a float representing the seconds that the process has
    executed in user/kernel mode I borrowed the code below from Python's
    Modules/posixmodule.c
    */

    return Py_BuildValue(
        "(dd)",
        (double)(ftUser.dwHighDateTime*429.4967296 + \
                 ftUser.dwLowDateTime*1e-7),
        (double)(ftKernel.dwHighDateTime*429.4967296 + \
                 ftKernel.dwLowDateTime*1e-7)
        );
}


/*
 * Alternative implementation of the one above but bypasses ACCESS DENIED.
 */
static PyObject*
get_process_cpu_times_2(PyObject* self, PyObject* args)
{
    DWORD pid;
    PSYSTEM_PROCESS_INFORMATION process;
    PVOID buffer;
    double user, kernel;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (! get_process_info(pid, &process, &buffer)) {
        return NULL;
    }
    user = (double)process->UserTime.HighPart * 429.4967296 + \
           (double)process->UserTime.LowPart * 1e-7;
    kernel = (double)process->KernelTime.HighPart * 429.4967296 + \
             (double)process->KernelTime.LowPart * 1e-7;
    free(buffer);
    return Py_BuildValue("(dd)", user, kernel);
}


/*
 * Return a Python float indicating the process create time expressed in
 * seconds since the epoch.
 */
static PyObject*
get_process_create_time(PyObject* self, PyObject* args)
{
    long        pid;
    long long   unix_time;
    DWORD       exitCode;
    HANDLE      hProcess;
    BOOL        ret;
    FILETIME    ftCreate, ftExit, ftKernel, ftUser;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }

    // special case for PIDs 0 and 4, return BOOT_TIME
    if (0 == pid || 4 == pid) {
        return get_system_boot_time(NULL, NULL);
    }

    hProcess = psutil_handle_from_pid(pid);
    if (hProcess == NULL) {
        return NULL;
    }

    if (! GetProcessTimes(hProcess, &ftCreate, &ftExit, &ftKernel, &ftUser)) {
        CloseHandle(hProcess);
        if (GetLastError() == ERROR_ACCESS_DENIED) {
            // usually means the process has died so we throw a NoSuchProcess here
            return NoSuchProcess();
        }
        else {
            PyErr_SetFromWindowsErr(0);
            return NULL;
        }
    }

    // Make sure the process is not gone as OpenProcess alone seems to be
    // unreliable in doing so (it seems a previous call to p.wait() makes
    // it unreliable).
    // This check is important as creation time is used to make sure the
    // process is still running.
    ret = GetExitCodeProcess(hProcess, &exitCode);
    CloseHandle(hProcess);
    if (ret != 0) {
        if (exitCode != STILL_ACTIVE) {
            return NoSuchProcess();
        }
    }
    else {
        // Ignore access denied as it means the process is still alive.
        // For all other errors, we want an exception.
        if (GetLastError() != ERROR_ACCESS_DENIED) {
            PyErr_SetFromWindowsErr(0);
            return NULL;
        }
    }

    /*
    Convert the FILETIME structure to a Unix time.
    It's the best I could find by googling and borrowing code here and there.
    The time returned has a precision of 1 second.
    */
    unix_time = ((LONGLONG)ftCreate.dwHighDateTime) << 32;
    unix_time += ftCreate.dwLowDateTime - 116444736000000000LL;
    unix_time /= 10000000;
    return Py_BuildValue("d", (double)unix_time);
}


/*
 * Alternative implementation of the one above but bypasses ACCESS DENIED.
 */
static PyObject*
get_process_create_time_2(PyObject* self, PyObject* args)
{
    DWORD pid;
    PSYSTEM_PROCESS_INFORMATION process;
    PVOID buffer;
    long long   unix_time;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (! get_process_info(pid, &process, &buffer)) {
        return NULL;
    }
    // special case for PIDs 0 and 4, return BOOT_TIME
    if (0 == pid || 4 == pid) {
        return get_system_boot_time(NULL, NULL);
    }
    /*
    Convert the LARGE_INTEGER union to a Unix time.
    It's the best I could find by googling and borrowing code here and there.
    The time returned has a precision of 1 second.
    */
    unix_time = ((LONGLONG)process->CreateTime.HighPart) << 32;
    unix_time += process->CreateTime.LowPart - 116444736000000000LL;
    unix_time /= 10000000;
    free(buffer);
    return Py_BuildValue("d", (double)unix_time);
}


/*
 * Return a Python integer indicating the number of CPUs on the system.
 */
static PyObject*
get_num_cpus(PyObject* self, PyObject* args)
{
    SYSTEM_INFO system_info;
    system_info.dwNumberOfProcessors = 0;

    GetSystemInfo(&system_info);
    if (system_info.dwNumberOfProcessors == 0){
        // GetSystemInfo failed for some reason; return 1 as default
        return Py_BuildValue("I", 1);
    }
    return Py_BuildValue("I", system_info.dwNumberOfProcessors);
}

/*
 * Return process name as a Python string.
 */
static PyObject*
get_process_name(PyObject* self, PyObject* args) {
    long pid;
    int pid_return;
    PyObject* name;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }

    if (pid == 0) {
        return Py_BuildValue("s", "System Idle Process");
    }
    else if (pid == 4) {
        return Py_BuildValue("s", "System");
    }

    pid_return = psutil_pid_is_running(pid);
    if (pid_return == 0) {
        return NoSuchProcess();
    }
    if (pid_return == -1) {
        return NULL;
    }

    name = psutil_get_name(pid);
    if (name == NULL) {
        return NULL;  // exception set in psutil_get_name()
    }
    return name;
}


/*
 * Return process parent pid as a Python integer.
 */
static PyObject*
get_process_ppid(PyObject* self, PyObject* args) {
    long pid;
    int pid_return;
    PyObject* ppid;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if ((pid == 0) || (pid == 4)) {
        return Py_BuildValue("l", 0);
    }

    pid_return = psutil_pid_is_running(pid);
    if (pid_return == 0) {
        return NoSuchProcess();
    }
    if (pid_return == -1) {
        return NULL;
    }

    ppid = psutil_get_ppid(pid);
    if (ppid == NULL) {
        return NULL;  // exception set in psutil_get_ppid()
    }
    return ppid;
}

/*
 * Return process cmdline as a Python list of cmdline arguments.
 */
static PyObject*
get_process_cmdline(PyObject* self, PyObject* args) {
    long pid;
    int pid_return;
    PyObject* arglist;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if ((pid == 0) || (pid == 4)) {
        return Py_BuildValue("[]");
    }

    pid_return = psutil_pid_is_running(pid);
    if (pid_return == 0) {
        return NoSuchProcess();
    }
    if (pid_return == -1) {
        return NULL;
    }

    // XXX the assumptio below probably needs to go away

    // May fail any of several ReadProcessMemory calls etc. and not indicate
    // a real problem so we ignore any errors and just live without commandline
    arglist = psutil_get_arg_list(pid);
    if ( NULL == arglist ) {
        // carry on anyway, clear any exceptions too
        PyErr_Clear();
        return Py_BuildValue("[]");
    }

    return arglist;
}


/*
 * Return process executable path.
 */
static PyObject*
get_process_exe(PyObject* self, PyObject* args) {
    long pid;
    HANDLE hProcess;
    wchar_t exe[MAX_PATH];
    DWORD nSize = MAX_PATH;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }

    hProcess = psutil_handle_from_pid_waccess(pid, PROCESS_QUERY_INFORMATION);
    if (NULL == hProcess) {
        return NULL;
    }

    if (GetProcessImageFileName(hProcess, &exe, nSize) == 0) {
        CloseHandle(hProcess);
        return PyErr_SetFromWindowsErr(0);
    }

    CloseHandle(hProcess);
    return Py_BuildValue("s", exe);
}


/*
 * Return process memory information as a Python tuple.
 */
static PyObject*
get_process_memory_info(PyObject* self, PyObject* args)
{
    HANDLE hProcess;
    DWORD pid;
#if (_WIN32_WINNT >= 0x0501)  // Windows XP with SP2
    PROCESS_MEMORY_COUNTERS_EX cnt;
#else
    PROCESS_MEMORY_COUNTERS cnt;
#endif
    SIZE_T private = 0;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }

    hProcess = psutil_handle_from_pid(pid);
    if (NULL == hProcess) {
        return NULL;
    }

    if (! GetProcessMemoryInfo(hProcess, &cnt, sizeof(cnt)) ) {
        CloseHandle(hProcess);
        return PyErr_SetFromWindowsErr(0);
    }

#if (_WIN32_WINNT >= 0x0501)
    private = cnt.PrivateUsage;
#endif

    CloseHandle(hProcess);

// py 2.4
#if (PY_MAJOR_VERSION == 2) && (PY_MINOR_VERSION <= 4)
    return Py_BuildValue("(kIIIIIIIII)",
        cnt.PageFaultCount,
        (unsigned int)cnt.PeakWorkingSetSize,
        (unsigned int)cnt.WorkingSetSize,
        (unsigned int)cnt.QuotaPeakPagedPoolUsage,
        (unsigned int)cnt.QuotaPagedPoolUsage,
        (unsigned int)cnt.QuotaPeakNonPagedPoolUsage,
        (unsigned int)cnt.QuotaNonPagedPoolUsage,
        (unsigned int)cnt.PagefileUsage,
        (unsigned int)cnt.PeakPagefileUsage,
        (unsigned int)private);
#else
// py >= 2.5
    return Py_BuildValue("(knnnnnnnnn)",
        cnt.PageFaultCount,
        cnt.PeakWorkingSetSize,
        cnt.WorkingSetSize,
        cnt.QuotaPeakPagedPoolUsage,
        cnt.QuotaPagedPoolUsage,
        cnt.QuotaPeakNonPagedPoolUsage,
        cnt.QuotaNonPagedPoolUsage,
        cnt.PagefileUsage,
        cnt.PeakPagefileUsage,
        private);
#endif
}


/*
 * Alternative implementation of the one above but bypasses ACCESS DENIED.
 */
static PyObject*
get_process_memory_info_2(PyObject* self, PyObject* args)
{
    DWORD pid;
    PSYSTEM_PROCESS_INFORMATION process;
    PVOID buffer;
    ULONG m0;
    SIZE_T m1, m2, m3, m4, m5, m6, m7, m8, m9;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (! get_process_info(pid, &process, &buffer)) {
        return NULL;
    }
    m0 = process->PageFaultCount;
    m1 = process->PeakWorkingSetSize;
    m2 = process->WorkingSetSize;
    m3 = process->QuotaPeakPagedPoolUsage;
    m4 = process->QuotaPagedPoolUsage;
    m5 = process->QuotaPeakNonPagedPoolUsage;
    m6 = process->QuotaNonPagedPoolUsage;
    m7 = process->PagefileUsage;
    m8 = process->PeakPagefileUsage;
#if (_WIN32_WINNT >= 0x0501)
    m9 = process->PrivatePageCount;  // private me
#else
    m9 = 0;
#endif
    free(buffer);

// py 2.4
#if (PY_MAJOR_VERSION == 2) && (PY_MINOR_VERSION <= 4)
    return Py_BuildValue("(kIIIIIIIII)",
        (unsigned int)m0, (unsigned int)m1, (unsigned int)m2, (unsigned int)m3,
        (unsigned int)m4, (unsigned int)m5, (unsigned int)m6, (unsigned int)m7,
        (unsigned int)m8, (unsigned int)m9);
#else
    return Py_BuildValue("(knnnnnnnnn)",
        m0, m1, m2, m3, m4, m5, m6, m7, m8, m9);
#endif
}


/*
 * Return a Python integer indicating the total amount of physical memory
 * in bytes.
 */
static PyObject*
get_virtual_mem(PyObject* self, PyObject* args)
{
    MEMORYSTATUSEX memInfo;
    memInfo.dwLength = sizeof(MEMORYSTATUSEX);

    if (! GlobalMemoryStatusEx(&memInfo) ) {
        return PyErr_SetFromWindowsErr(0);
    }

    return Py_BuildValue("(LLLLLL)",
        memInfo.ullTotalPhys,      // total
        memInfo.ullAvailPhys,      // avail
        memInfo.ullTotalPageFile,  // total page file
        memInfo.ullAvailPageFile,  // avail page file
        memInfo.ullTotalVirtual,   // total virtual
        memInfo.ullAvailVirtual    // avail virtual
    );
}


#define LO_T ((float)1e-7)
#define HI_T (LO_T*4294967296.0)


/*
 * Return a Python list of tuples representing user, kernel and idle
 * CPU times for every CPU on the system.
 */
static PyObject*
get_system_cpu_times(PyObject* self, PyObject* args)
{
    float idle, kernel, user;
    typedef DWORD (_stdcall *NTQSI_PROC) (int, PVOID, ULONG, PULONG);
    NTQSI_PROC NtQuerySystemInformation;
    HINSTANCE hNtDll;
    SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION *sppi = NULL;
    SYSTEM_INFO si;
    UINT i;
    PyObject *arg = NULL;
    PyObject *retlist = PyList_New(0);

    if (retlist == NULL)
        return NULL;

    // dynamic linking is mandatory to use NtQuerySystemInformation
    hNtDll = LoadLibrary(TEXT("ntdll.dll"));
    if (hNtDll != NULL) {
        // gets NtQuerySystemInformation address
        NtQuerySystemInformation = (NTQSI_PROC)GetProcAddress(
                                    hNtDll, "NtQuerySystemInformation");

        if (NtQuerySystemInformation != NULL)
        {
            // retrives number of processors
            GetSystemInfo(&si);

            // allocates an array of SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION
            // structures, one per processor
            sppi = (SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION *) \
                    malloc(si.dwNumberOfProcessors * \
                         sizeof(SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION));
            if (sppi != NULL)
            {
                // gets cpu time informations
                if (0 == NtQuerySystemInformation(
                    SystemProcessorPerformanceInformation,
                    sppi,
                    si.dwNumberOfProcessors * sizeof
                                (SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION),
                    NULL)
                )
                {
                    // computes system global times summing each processor value
                    idle = user = kernel = 0;
                    for (i=0; i<si.dwNumberOfProcessors; i++) {
                        arg = NULL;
                        user = (float)((HI_T * sppi[i].UserTime.HighPart) + \
                                       (LO_T * sppi[i].UserTime.LowPart));
                        idle = (float)((HI_T * sppi[i].IdleTime.HighPart) + \
                                       (LO_T * sppi[i].IdleTime.LowPart));
                        kernel = (float)((HI_T * sppi[i].KernelTime.HighPart) + \
                                         (LO_T * sppi[i].KernelTime.LowPart));
                        // kernel time includes idle time on windows
                        // we return only busy kernel time subtracting
                        // idle time from kernel time
                        arg = Py_BuildValue("(ddd)", user,
                                                     kernel - idle,
                                                     idle);
                        if (!arg)
                            goto error;
                        if (PyList_Append(retlist, arg))
                            goto error;
                        Py_DECREF(arg);
                    }
                    free(sppi);
                    FreeLibrary(hNtDll);
                    return retlist;

                }  // END NtQuerySystemInformation
            }  // END malloc SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION
        }  // END GetProcAddress
    }  // END LoadLibrary
    goto error;

error:
    Py_XDECREF(arg);
    Py_DECREF(retlist);
    if (sppi) {
        free(sppi);
    }
    if (hNtDll) {
        FreeLibrary(hNtDll);
    }
    PyErr_SetFromWindowsErr(0);
    return NULL;
}


/*
 * Return process current working directory as a Python string.
 */

static PyObject*
get_process_cwd(PyObject* self, PyObject* args)
{
    long pid;
    HANDLE processHandle = NULL;
    PVOID pebAddress;
    PVOID rtlUserProcParamsAddress;
    UNICODE_STRING currentDirectory;
    WCHAR *currentDirectoryContent = NULL;
    PyObject *returnPyObj = NULL;
    PyObject *cwd_from_wchar = NULL;
    PyObject *cwd = NULL;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }

    processHandle = psutil_handle_from_pid(pid);
    if (processHandle == NULL) {
        return NULL;
    }

    pebAddress = psutil_get_peb_address(processHandle);

    // get the address of ProcessParameters
#ifdef _WIN64
    if (!ReadProcessMemory(processHandle, (PCHAR)pebAddress + 32,
        &rtlUserProcParamsAddress, sizeof(PVOID), NULL))
#else
    if (!ReadProcessMemory(processHandle, (PCHAR)pebAddress + 0x10,
        &rtlUserProcParamsAddress, sizeof(PVOID), NULL))
#endif
    {
        CloseHandle(processHandle);

        if (GetLastError() == ERROR_PARTIAL_COPY) {
            // this occurs quite often with system processes
            return AccessDenied();
        }
        else {
            return PyErr_SetFromWindowsErr(0);
        }
    }

    // Read the currentDirectory UNICODE_STRING structure.
    // 0x24 refers to "CurrentDirectoryPath" of RTL_USER_PROCESS_PARAMETERS
    // structure, see:
    // http://wj32.wordpress.com/2009/01/24/howto-get-the-command-line-of-processes/
#ifdef _WIN64
    if (!ReadProcessMemory(processHandle, (PCHAR)rtlUserProcParamsAddress + 56,
        &currentDirectory, sizeof(currentDirectory), NULL))
#else
    if (!ReadProcessMemory(processHandle, (PCHAR)rtlUserProcParamsAddress + 0x24,
        &currentDirectory, sizeof(currentDirectory), NULL))
#endif
    {
        CloseHandle(processHandle);
        if (GetLastError() == ERROR_PARTIAL_COPY) {
            // this occurs quite often with system processes
            return AccessDenied();
        }
        else {
            return PyErr_SetFromWindowsErr(0);
        }
    }

    // allocate memory to hold cwd
    currentDirectoryContent = (WCHAR *)malloc(currentDirectory.Length+1);
    if (currentDirectoryContent == NULL) {
        PyErr_NoMemory();
        goto error;
    }


    // read cwd
    if (!ReadProcessMemory(processHandle, currentDirectory.Buffer,
        currentDirectoryContent, currentDirectory.Length, NULL))
    {
        if (GetLastError() == ERROR_PARTIAL_COPY) {
            // this occurs quite often with system processes
            AccessDenied();
        }
        else {
            PyErr_SetFromWindowsErr(0);
        }
        goto error;
    }

    // null-terminate the string to prevent wcslen from returning
    // incorrect length the length specifier is in characters, but
    // currentDirectory.Length is in bytes
    currentDirectoryContent[(currentDirectory.Length/sizeof(WCHAR))] = '\0';

    // convert wchar array to a Python unicode string, and then to UTF8
    cwd_from_wchar = PyUnicode_FromWideChar(currentDirectoryContent,
                                            wcslen(currentDirectoryContent));
    if (cwd_from_wchar == NULL)
        goto error;

    #if PY_MAJOR_VERSION >= 3
        cwd = PyUnicode_FromObject(cwd_from_wchar);
    #else
        cwd = PyUnicode_AsUTF8String(cwd_from_wchar);
    #endif
    if (cwd == NULL)
        goto error;

    // decrement the reference count on our temp unicode str to avoid
    // mem leak
    returnPyObj = Py_BuildValue("N", cwd);
    if (!returnPyObj)
        goto error;

    Py_DECREF(cwd_from_wchar);

    CloseHandle(processHandle);
    free(currentDirectoryContent);
    return returnPyObj;

error:
    Py_XDECREF(cwd_from_wchar);
    Py_XDECREF(cwd);
    Py_XDECREF(returnPyObj);
    if (currentDirectoryContent != NULL)
        free(currentDirectoryContent);
    if (processHandle != NULL)
        CloseHandle(processHandle);
    return NULL;
}


/*
 * Resume or suspends a process
 */
int
suspend_resume_process(DWORD pid, int suspend)
{
    // a huge thanks to http://www.codeproject.com/KB/threads/pausep.aspx
    HANDLE hThreadSnap = NULL;
    THREADENTRY32  te32 = {0};

    if (pid == 0) {
        AccessDenied();
        return FALSE;
    }

    hThreadSnap = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    if (hThreadSnap == INVALID_HANDLE_VALUE) {
        PyErr_SetFromWindowsErr(0);
        return FALSE;
    }

    // Fill in the size of the structure before using it
    te32.dwSize = sizeof(THREADENTRY32);

    if (! Thread32First(hThreadSnap, &te32)) {
        PyErr_SetFromWindowsErr(0);
        CloseHandle(hThreadSnap);
        return FALSE;
    }

    // Walk the thread snapshot to find all threads of the process.
    // If the thread belongs to the process, add its information
    // to the display list.
    do
    {
        if (te32.th32OwnerProcessID == pid)
        {
            HANDLE hThread = OpenThread(THREAD_SUSPEND_RESUME, FALSE,
                                        te32.th32ThreadID);
            if (hThread == NULL) {
                PyErr_SetFromWindowsErr(0);
                CloseHandle(hThread);
                CloseHandle(hThreadSnap);
                return FALSE;
            }
            if (suspend == 1)
            {
                if (SuspendThread(hThread) == (DWORD)-1) {
                    PyErr_SetFromWindowsErr(0);
                    CloseHandle(hThread);
                    CloseHandle(hThreadSnap);
                    return FALSE;
                }
            }
            else
            {
                if (ResumeThread(hThread) == (DWORD)-1) {
                    PyErr_SetFromWindowsErr(0);
                    CloseHandle(hThread);
                    CloseHandle(hThreadSnap);
                    return FALSE;
                }
            }
            CloseHandle(hThread);
        }
    } while (Thread32Next(hThreadSnap, &te32));

    CloseHandle(hThreadSnap);
    return TRUE;
}


static PyObject*
suspend_process(PyObject* self, PyObject* args)
{
    long pid;
    int suspend = 1;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }

    if (! suspend_resume_process(pid, suspend)) {
        return NULL;
    }
    Py_INCREF(Py_None);
    return Py_None;
}


static PyObject*
resume_process(PyObject* self, PyObject* args)
{
    long pid;
    int suspend = 0;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }

    if (! suspend_resume_process(pid, suspend)) {
        return NULL;
    }
    Py_INCREF(Py_None);
    return Py_None;
}


static PyObject*
get_process_num_threads(PyObject* self, PyObject* args)
{
    DWORD pid;
    PSYSTEM_PROCESS_INFORMATION process;
    PVOID buffer;
    int num;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (! get_process_info(pid, &process, &buffer)) {
        return NULL;
    }
    num = (int)process->NumberOfThreads;
    free(buffer);
    return Py_BuildValue("i", num);
}


static PyObject*
get_process_threads(PyObject* self, PyObject* args)
{
    HANDLE hThread;
    THREADENTRY32 te32 = {0};
    long pid;
    int pid_return;
    int rc;
    FILETIME ftDummy, ftKernel, ftUser;
    PyObject* retList = PyList_New(0);
    PyObject* pyTuple = NULL;
    HANDLE hThreadSnap = NULL;

    if (retList == NULL) {
        return NULL;
    }
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        goto error;
    }
    if (pid == 0) {
        // raise AD instead of returning 0 as procexp is able to
        // retrieve useful information somehow
        AccessDenied();
        goto error;
    }

    pid_return = psutil_pid_is_running(pid);
    if (pid_return == 0) {
        NoSuchProcess();
        goto error;
    }
    if (pid_return == -1) {
        goto error;
    }

    hThreadSnap = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    if (hThreadSnap == INVALID_HANDLE_VALUE) {
        PyErr_SetFromWindowsErr(0);
        goto error;
    }

    // Fill in the size of the structure before using it
    te32.dwSize = sizeof(THREADENTRY32);

    if (! Thread32First(hThreadSnap, &te32)) {
        PyErr_SetFromWindowsErr(0);
        goto error;
    }

    // Walk the thread snapshot to find all threads of the process.
    // If the thread belongs to the process, increase the counter.
    do
    {
        if (te32.th32OwnerProcessID == pid)
        {
            pyTuple = NULL;
            hThread = NULL;
            hThread = OpenThread(THREAD_QUERY_INFORMATION,
                                  FALSE, te32.th32ThreadID);
            if (hThread == NULL) {
                // thread has disappeared on us
                continue;
            }

            rc = GetThreadTimes(hThread, &ftDummy, &ftDummy, &ftKernel, &ftUser);
            if (rc == 0) {
                PyErr_SetFromWindowsErr(0);
                goto error;
            }

            /*
            user and kernel times are represented as a FILETIME structure
            wich contains a 64-bit value representing the number of
            100-nanosecond intervals since January 1, 1601 (UTC).
            http://msdn.microsoft.com/en-us/library/ms724284(VS.85).aspx

            To convert it into a float representing the seconds that the
            process has executed in user/kernel mode I borrowed the code
            below from Python's Modules/posixmodule.c
            */
            pyTuple = Py_BuildValue("kdd",
                            te32.th32ThreadID,
                            (double)(ftUser.dwHighDateTime*429.4967296 + \
                                     ftUser.dwLowDateTime*1e-7),
                            (double)(ftKernel.dwHighDateTime*429.4967296 + \
                                     ftKernel.dwLowDateTime*1e-7));
            if (!pyTuple)
                goto error;
            if (PyList_Append(retList, pyTuple))
                goto error;
            Py_DECREF(pyTuple);

            CloseHandle(hThread);
        }
    } while (Thread32Next(hThreadSnap, &te32));

    CloseHandle(hThreadSnap);
    return retList;

error:
    Py_XDECREF(pyTuple);
    Py_DECREF(retList);
    if (hThread != NULL)
        CloseHandle(hThread);
    if (hThreadSnap != NULL) {
        CloseHandle(hThreadSnap);
    }
    return NULL;
}



static PyObject*
get_process_open_files(PyObject* self, PyObject* args)
{
    long       pid;
    HANDLE     processHandle;
    DWORD      access = PROCESS_DUP_HANDLE | PROCESS_QUERY_INFORMATION;
    PyObject*  filesList;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }

    processHandle = psutil_handle_from_pid_waccess(pid, access);
    if (processHandle == NULL) {
        return NULL;
    }

    filesList = psutil_get_open_files(pid, processHandle);
    CloseHandle(processHandle);
    if (filesList == NULL) {
        return PyErr_SetFromWindowsErr(0);
    }
    return filesList;
}


/*
 Accept a filename's drive in native  format like "\Device\HarddiskVolume1\"
 and return the corresponding drive letter (e.g. "C:\\").
 If no match is found return an empty string.
*/
static PyObject*
win32_QueryDosDevice(PyObject* self, PyObject* args)
{
    LPCTSTR   lpDevicePath;
    TCHAR d = TEXT('A');
    TCHAR     szBuff[5];

    if (!PyArg_ParseTuple(args, "s", &lpDevicePath)) {
        return NULL;
    }

    while(d <= TEXT('Z'))
    {
        TCHAR szDeviceName[3] = {d,TEXT(':'),TEXT('\0')};
        TCHAR szTarget[512] = {0};
        if (QueryDosDevice(szDeviceName, szTarget, 511) != 0){
            //_tprintf (TEXT("%c:\\   =>   %s\n"), d, szTarget);
            if(_tcscmp(lpDevicePath, szTarget) == 0) {
                _stprintf(szBuff, TEXT("%c:"), d);
                return Py_BuildValue("s", szBuff);
            }
        }
        d++;
    }
    return Py_BuildValue("s", "");
}

/*
 * Return process username as a "DOMAIN//USERNAME" string.
 */
static PyObject*
get_process_username(PyObject* self, PyObject* args)
{
    long pid;
    HANDLE processHandle;
    HANDLE tokenHandle;
    PTOKEN_USER user;
    ULONG bufferSize;
    PTSTR name;
    ULONG nameSize;
    PTSTR domainName;
    ULONG domainNameSize;
    SID_NAME_USE nameUse;
    PTSTR fullName;
    PyObject* returnObject;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }

    processHandle = psutil_handle_from_pid_waccess(pid, PROCESS_QUERY_INFORMATION);
    if (processHandle == NULL) {
        return NULL;
    }

    if (!OpenProcessToken(processHandle, TOKEN_QUERY, &tokenHandle)) {
        CloseHandle(processHandle);
        return PyErr_SetFromWindowsErr(0);
    }

    CloseHandle(processHandle);

    /* Get the user SID. */

    bufferSize = 0x100;
    user = malloc(bufferSize);
    if (user == NULL) {
        return PyErr_NoMemory();
    }

    if (!GetTokenInformation(tokenHandle,
                             TokenUser,
                             user,
                             bufferSize,
                             &bufferSize))
    {
        free(user);
        user = malloc(bufferSize);
        if (user == NULL) {
            CloseHandle(tokenHandle);
            return PyErr_NoMemory();
        }
        if (!GetTokenInformation(tokenHandle,
                                 TokenUser,
                                 user,
                                 bufferSize,
                                 &bufferSize))
        {
            free(user);
            CloseHandle(tokenHandle);
            return PyErr_SetFromWindowsErr(0);
        }
    }

    CloseHandle(tokenHandle);

    /* Resolve the SID to a name. */

    nameSize = 0x100;
    domainNameSize = 0x100;

    name = malloc(nameSize * sizeof(TCHAR));
    if (name == NULL)
        return PyErr_NoMemory();
    domainName = malloc(domainNameSize * sizeof(TCHAR));
    if (domainName == NULL)
        return PyErr_NoMemory();

    if (!LookupAccountSid(NULL, user->User.Sid, name, &nameSize, domainName,
                          &domainNameSize, &nameUse))
    {
        free(name);
        free(domainName);
        name = malloc(nameSize * sizeof(TCHAR));
        if (name == NULL)
            return PyErr_NoMemory();
        domainName = malloc(domainNameSize * sizeof(TCHAR));
        if (domainName == NULL)
            return PyErr_NoMemory();
        if (!LookupAccountSid(NULL, user->User.Sid, name, &nameSize, domainName,
                              &domainNameSize, &nameUse))
        {
            free(name);
            free(domainName);
            free(user);

            return PyErr_SetFromWindowsErr(0);
        }
    }

    nameSize = _tcslen(name);
    domainNameSize = _tcslen(domainName);

    /* Build the full username string. */
    fullName = malloc((domainNameSize + 1 + nameSize + 1) * sizeof(TCHAR));
    if (fullName == NULL) {
        free(name);
        free(domainName);
        free(user);
        return PyErr_NoMemory();
    }
    memcpy(fullName, domainName, domainNameSize);
    fullName[domainNameSize] = '\\';
    memcpy(&fullName[domainNameSize + 1], name, nameSize);
    fullName[domainNameSize + 1 + nameSize] = '\0';

    returnObject = Py_BuildValue("s", fullName);

    free(fullName);
    free(name);
    free(domainName);
    free(user);

    return returnObject;
}

#define BYTESWAP_USHORT(x) ((((USHORT)(x) << 8) | ((USHORT)(x) >> 8)) & 0xffff)

#ifndef AF_INET6
#define AF_INET6 23
#endif

static char *state_to_string(ULONG state)
{
    switch (state)
    {
    case MIB_TCP_STATE_CLOSED:
        return "CLOSE";
    case MIB_TCP_STATE_LISTEN:
        return "LISTEN";
    case MIB_TCP_STATE_SYN_SENT:
        return "SYN_SENT";
    case MIB_TCP_STATE_SYN_RCVD:
        return "SYN_RECV";
    case MIB_TCP_STATE_ESTAB:
        return "ESTABLISHED";
    case MIB_TCP_STATE_FIN_WAIT1:
        return "FIN_WAIT1";
    case MIB_TCP_STATE_FIN_WAIT2:
        return "FIN_WAIT2";
    case MIB_TCP_STATE_CLOSE_WAIT:
        return "CLOSE_WAIT";
    case MIB_TCP_STATE_CLOSING:
        return "CLOSING";
    case MIB_TCP_STATE_LAST_ACK:
        return "LAST_ACK";
    case MIB_TCP_STATE_TIME_WAIT:
        return "TIME_WAIT";
    case MIB_TCP_STATE_DELETE_TCB:
        return "DELETE_TCB";
    default:
        return "";
    }
}

/* mingw support */
#ifndef _IPRTRMIB_H
typedef struct _MIB_TCP6ROW_OWNER_PID
{
    UCHAR           ucLocalAddr[16];
    DWORD           dwLocalScopeId;
    DWORD           dwLocalPort;
    UCHAR           ucRemoteAddr[16];
    DWORD           dwRemoteScopeId;
    DWORD           dwRemotePort;
    DWORD           dwState;
    DWORD           dwOwningPid;
} MIB_TCP6ROW_OWNER_PID, *PMIB_TCP6ROW_OWNER_PID;

typedef struct _MIB_TCP6TABLE_OWNER_PID
{
    DWORD                   dwNumEntries;
    MIB_TCP6ROW_OWNER_PID   table[ANY_SIZE];
} MIB_TCP6TABLE_OWNER_PID, *PMIB_TCP6TABLE_OWNER_PID;
#endif

#ifndef __IPHLPAPI_H__
typedef struct in6_addr {
    union {
        UCHAR       Byte[16];
        USHORT      Word[8];
    } u;
} IN6_ADDR, *PIN6_ADDR, FAR *LPIN6_ADDR;


typedef enum _UDP_TABLE_CLASS {
    UDP_TABLE_BASIC,
    UDP_TABLE_OWNER_PID,
    UDP_TABLE_OWNER_MODULE
} UDP_TABLE_CLASS, *PUDP_TABLE_CLASS;


typedef struct _MIB_UDPROW_OWNER_PID {
    DWORD dwLocalAddr;
    DWORD dwLocalPort;
    DWORD dwOwningPid;
} MIB_UDPROW_OWNER_PID, *PMIB_UDPROW_OWNER_PID;

typedef struct _MIB_UDPTABLE_OWNER_PID
{
    DWORD                   dwNumEntries;
    MIB_UDPROW_OWNER_PID    table[ANY_SIZE];
} MIB_UDPTABLE_OWNER_PID, *PMIB_UDPTABLE_OWNER_PID;
#endif
/* end of mingw support */

typedef struct _MIB_UDP6ROW_OWNER_PID {
    UCHAR           ucLocalAddr[16];
    DWORD           dwLocalScopeId;
    DWORD           dwLocalPort;
    DWORD           dwOwningPid;
} MIB_UDP6ROW_OWNER_PID, *PMIB_UDP6ROW_OWNER_PID;

typedef struct _MIB_UDP6TABLE_OWNER_PID
{
    DWORD                   dwNumEntries;
    MIB_UDP6ROW_OWNER_PID   table[ANY_SIZE];
} MIB_UDP6TABLE_OWNER_PID, *PMIB_UDP6TABLE_OWNER_PID;


#define ConnDecrefPyObjs() Py_DECREF(_AF_INET); \
                           Py_DECREF(_AF_INET6);\
                           Py_DECREF(_SOCK_STREAM);\
                           Py_DECREF(_SOCK_DGRAM);

/*
 * Return a list of network connections opened by a process
 */
static PyObject*
get_process_connections(PyObject* self, PyObject* args)
{
    static long null_address[4] = { 0, 0, 0, 0 };

    unsigned long pid;
    PyObject* connectionsList;
    PyObject* connectionTuple = NULL;
    PyObject *af_filter = NULL;
    PyObject *type_filter = NULL;

    PyObject *_AF_INET = PyLong_FromLong((long)AF_INET);
    PyObject *_AF_INET6 = PyLong_FromLong((long)AF_INET6);
    PyObject *_SOCK_STREAM = PyLong_FromLong((long)SOCK_STREAM);
    PyObject *_SOCK_DGRAM = PyLong_FromLong((long)SOCK_DGRAM);

    typedef PSTR (NTAPI *_RtlIpv4AddressToStringA)(struct in_addr *,
                                                   PSTR /* __out_ecount(16) */);
    _RtlIpv4AddressToStringA rtlIpv4AddressToStringA;
    typedef PSTR (NTAPI *_RtlIpv6AddressToStringA)(struct in6_addr *,
                                                   PSTR /* __out_ecount(65) */);
    _RtlIpv6AddressToStringA rtlIpv6AddressToStringA;
    typedef DWORD (WINAPI *_GetExtendedTcpTable)(PVOID, PDWORD, BOOL, ULONG,
                                                 TCP_TABLE_CLASS, ULONG);
    _GetExtendedTcpTable getExtendedTcpTable;
    typedef DWORD (WINAPI *_GetExtendedUdpTable)(PVOID, PDWORD, BOOL, ULONG,
                                                 UDP_TABLE_CLASS, ULONG);
    _GetExtendedUdpTable getExtendedUdpTable;
    PVOID table = NULL;
    DWORD tableSize;
    PMIB_TCPTABLE_OWNER_PID tcp4Table;
    PMIB_UDPTABLE_OWNER_PID udp4Table;
    PMIB_TCP6TABLE_OWNER_PID tcp6Table;
    PMIB_UDP6TABLE_OWNER_PID udp6Table;
    ULONG i;
    CHAR addressBufferLocal[65];
    PyObject* addressTupleLocal = NULL;
    CHAR addressBufferRemote[65];
    PyObject* addressTupleRemote = NULL;

    if (! PyArg_ParseTuple(args, "lOO", &pid, &af_filter, &type_filter)) {
        ConnDecrefPyObjs();
        return NULL;
    }

    if (!PySequence_Check(af_filter) || !PySequence_Check(type_filter)) {
        ConnDecrefPyObjs();
        PyErr_SetString(PyExc_TypeError, "arg 2 or 3 is not a sequence");
        return NULL;
    }

    if (psutil_pid_is_running(pid) == 0) {
        ConnDecrefPyObjs();
        return NoSuchProcess();
    }

    /* Import some functions. */
    {
        HMODULE ntdll;
        HMODULE iphlpapi;

        ntdll = LoadLibrary(TEXT("ntdll.dll"));
        rtlIpv4AddressToStringA = (_RtlIpv4AddressToStringA)GetProcAddress(ntdll,
                                                     "RtlIpv4AddressToStringA");
        rtlIpv6AddressToStringA = (_RtlIpv6AddressToStringA)GetProcAddress(ntdll,
                                                     "RtlIpv6AddressToStringA");
        /* TODO: Check these two function pointers */

        iphlpapi = LoadLibrary(TEXT("iphlpapi.dll"));
        getExtendedTcpTable = (_GetExtendedTcpTable)GetProcAddress(iphlpapi,
                                                        "GetExtendedTcpTable");
        getExtendedUdpTable = (_GetExtendedUdpTable)GetProcAddress(iphlpapi,
                                                        "GetExtendedUdpTable");
        FreeLibrary(ntdll);
        FreeLibrary(iphlpapi);
    }

    if ((getExtendedTcpTable == NULL) || (getExtendedUdpTable == NULL)) {
        PyErr_SetString(PyExc_NotImplementedError,
                        "feature not supported on this Windows version");
        ConnDecrefPyObjs();
        return NULL;
    }

    connectionsList = PyList_New(0);
    if (connectionsList == NULL) {
        ConnDecrefPyObjs();
        return NULL;
    }

    /* TCP IPv4 */

    if ((PySequence_Contains(af_filter, _AF_INET) == 1) &&
        (PySequence_Contains(type_filter, _SOCK_STREAM) == 1))
    {
        table = NULL;
        connectionTuple = NULL;
        addressTupleLocal = NULL;
        addressTupleRemote = NULL;
        tableSize = 0;
        getExtendedTcpTable(NULL, &tableSize, FALSE, AF_INET,
                            TCP_TABLE_OWNER_PID_ALL, 0);

        table = malloc(tableSize);
        if (table == NULL) {
            PyErr_NoMemory();
            goto error;
        }

        if (getExtendedTcpTable(table, &tableSize, FALSE, AF_INET,
                                TCP_TABLE_OWNER_PID_ALL, 0) == 0)
        {
            tcp4Table = table;

            for (i = 0; i < tcp4Table->dwNumEntries; i++)
            {
                if (tcp4Table->table[i].dwOwningPid != pid) {
                    continue;
                }

                if (tcp4Table->table[i].dwLocalAddr != 0 ||
                    tcp4Table->table[i].dwLocalPort != 0)
                {
                    struct in_addr addr;

                    addr.S_un.S_addr = tcp4Table->table[i].dwLocalAddr;
                    rtlIpv4AddressToStringA(&addr, addressBufferLocal);
                    addressTupleLocal = Py_BuildValue("(si)", addressBufferLocal,
                               BYTESWAP_USHORT(tcp4Table->table[i].dwLocalPort));
                }
                else
                {
                    addressTupleLocal = PyTuple_New(0);
                }

                if (addressTupleLocal == NULL)
                    goto error;

                // On Windows <= XP, remote addr is filled even if socket
                // is in LISTEN mode in which case we just ignore it.
                if ((tcp4Table->table[i].dwRemoteAddr != 0 ||
                     tcp4Table->table[i].dwRemotePort != 0) &&
                    (tcp4Table->table[i].dwState != MIB_TCP_STATE_LISTEN))
                {
                    struct in_addr addr;

                    addr.S_un.S_addr = tcp4Table->table[i].dwRemoteAddr;
                    rtlIpv4AddressToStringA(&addr, addressBufferRemote);
                    addressTupleRemote = Py_BuildValue("(si)", addressBufferRemote,
                            BYTESWAP_USHORT(tcp4Table->table[i].dwRemotePort));
                }
                else
                {
                    addressTupleRemote = PyTuple_New(0);
                }

                if (addressTupleRemote == NULL)
                    goto error;

                connectionTuple = Py_BuildValue("(iiiNNs)",
                    -1,
                    AF_INET,
                    SOCK_STREAM,
                    addressTupleLocal,
                    addressTupleRemote,
                    state_to_string(tcp4Table->table[i].dwState)
                    );
                if (!connectionTuple)
                    goto error;
                if (PyList_Append(connectionsList, connectionTuple))
                    goto error;
                Py_DECREF(connectionTuple);
            }
        }

        free(table);
    }

    /* TCP IPv6 */

    if ((PySequence_Contains(af_filter, _AF_INET6) == 1) &&
        (PySequence_Contains(type_filter, _SOCK_STREAM) == 1))
    {
        table = NULL;
        connectionTuple = NULL;
        addressTupleLocal = NULL;
        addressTupleRemote = NULL;
        tableSize = 0;
        getExtendedTcpTable(NULL, &tableSize, FALSE, AF_INET6,
                            TCP_TABLE_OWNER_PID_ALL, 0);

        table = malloc(tableSize);
        if (table == NULL) {
            PyErr_NoMemory();
            goto error;
        }

        if (getExtendedTcpTable(table, &tableSize, FALSE, AF_INET6,
                                 TCP_TABLE_OWNER_PID_ALL, 0) == 0)
        {
            tcp6Table = table;

            for (i = 0; i < tcp6Table->dwNumEntries; i++)
            {
                if (tcp6Table->table[i].dwOwningPid != pid) {
                    continue;
                }

                if (memcmp(tcp6Table->table[i].ucLocalAddr, null_address, 16) != 0 ||
                tcp6Table->table[i].dwLocalPort != 0)
                {
                    struct in6_addr addr;

                    memcpy(&addr, tcp6Table->table[i].ucLocalAddr, 16);
                    rtlIpv6AddressToStringA(&addr, addressBufferLocal);
                    addressTupleLocal = Py_BuildValue("(si)", addressBufferLocal,
                             BYTESWAP_USHORT(tcp6Table->table[i].dwLocalPort));
                }
                else
                {
                    addressTupleLocal = PyTuple_New(0);
                }

                if (addressTupleLocal == NULL)
                    goto error;

                // On Windows <= XP, remote addr is filled even if socket
                // is in LISTEN mode in which case we just ignore it.
                if ((memcmp(tcp6Table->table[i].ucRemoteAddr, null_address, 16) != 0 ||
                    tcp6Table->table[i].dwRemotePort != 0) &&
                   (tcp6Table->table[i].dwState != MIB_TCP_STATE_LISTEN))
                {
                    struct in6_addr addr;

                    memcpy(&addr, tcp6Table->table[i].ucRemoteAddr, 16);
                    rtlIpv6AddressToStringA(&addr, addressBufferRemote);
                    addressTupleRemote = Py_BuildValue("(si)", addressBufferRemote,
                            BYTESWAP_USHORT(tcp6Table->table[i].dwRemotePort));
                }
                else
                {
                    addressTupleRemote = PyTuple_New(0);
                }

                if (addressTupleRemote == NULL)
                    goto error;

                connectionTuple = Py_BuildValue("(iiiNNs)",
                    -1,
                    AF_INET6,
                    SOCK_STREAM,
                    addressTupleLocal,
                    addressTupleRemote,
                    state_to_string(tcp6Table->table[i].dwState)
                    );
                if (!connectionTuple)
                    goto error;
                if (PyList_Append(connectionsList, connectionTuple))
                    goto error;
                Py_DECREF(connectionTuple);
            }
        }

        free(table);
    }

    /* UDP IPv4 */

    if ((PySequence_Contains(af_filter, _AF_INET) == 1) &&
        (PySequence_Contains(type_filter, _SOCK_DGRAM) == 1))
    {
        table = NULL;
        connectionTuple = NULL;
        addressTupleLocal = NULL;
        addressTupleRemote = NULL;
        tableSize = 0;
        getExtendedUdpTable(NULL, &tableSize, FALSE, AF_INET,
                            UDP_TABLE_OWNER_PID, 0);

        table = malloc(tableSize);
        if (table == NULL) {
            PyErr_NoMemory();
            goto error;
        }

        if (getExtendedUdpTable(table, &tableSize, FALSE, AF_INET,
                                 UDP_TABLE_OWNER_PID, 0) == 0)
        {
            udp4Table = table;

            for (i = 0; i < udp4Table->dwNumEntries; i++)
            {
                if (udp4Table->table[i].dwOwningPid != pid) {
                    continue;
                }

                if (udp4Table->table[i].dwLocalAddr != 0 ||
                    udp4Table->table[i].dwLocalPort != 0)
                {
                    struct in_addr addr;

                    addr.S_un.S_addr = udp4Table->table[i].dwLocalAddr;
                    rtlIpv4AddressToStringA(&addr, addressBufferLocal);
                    addressTupleLocal = Py_BuildValue("(si)", addressBufferLocal,
                                BYTESWAP_USHORT(udp4Table->table[i].dwLocalPort));
                }
                else
                {
                    addressTupleLocal = PyTuple_New(0);
                }

                if (addressTupleLocal == NULL)
                    goto error;

                connectionTuple = Py_BuildValue("(iiiNNs)",
                    -1,
                    AF_INET,
                    SOCK_DGRAM,
                    addressTupleLocal,
                    PyTuple_New(0),
                    ""
                    );
                if (!connectionTuple)
                    goto error;
                if (PyList_Append(connectionsList, connectionTuple))
                    goto error;
                Py_DECREF(connectionTuple);
            }
        }

        free(table);
    }

    /* UDP IPv6 */

    if ((PySequence_Contains(af_filter, _AF_INET6) == 1) &&
        (PySequence_Contains(type_filter, _SOCK_DGRAM) == 1))
    {
        table = NULL;
        connectionTuple = NULL;
        addressTupleLocal = NULL;
        addressTupleRemote = NULL;
        tableSize = 0;
        getExtendedUdpTable(NULL, &tableSize, FALSE,
                            AF_INET6, UDP_TABLE_OWNER_PID, 0);

        table = malloc(tableSize);
        if (table == NULL) {
            PyErr_NoMemory();
            goto error;
        }

        if (getExtendedUdpTable(table, &tableSize, FALSE, AF_INET6,
                                 UDP_TABLE_OWNER_PID, 0) == 0)
        {
            udp6Table = table;

            for (i = 0; i < udp6Table->dwNumEntries; i++)
            {
                if (udp6Table->table[i].dwOwningPid != pid) {
                    continue;
                }

                if (memcmp(udp6Table->table[i].ucLocalAddr, null_address, 16) != 0 ||
                    udp6Table->table[i].dwLocalPort != 0)
                {
                    struct in6_addr addr;

                    memcpy(&addr, udp6Table->table[i].ucLocalAddr, 16);
                    rtlIpv6AddressToStringA(&addr, addressBufferLocal);
                    addressTupleLocal = Py_BuildValue("(si)", addressBufferLocal,
                              BYTESWAP_USHORT(udp6Table->table[i].dwLocalPort));
                }
                else
                {
                    addressTupleLocal = PyTuple_New(0);
                }

                if (addressTupleLocal == NULL)
                    goto error;

                connectionTuple = Py_BuildValue("(iiiNNs)",
                    -1,
                    AF_INET6,
                    SOCK_DGRAM,
                    addressTupleLocal,
                    PyTuple_New(0),
                    ""
                    );
                if (!connectionTuple)
                    goto error;
                if (PyList_Append(connectionsList, connectionTuple))
                    goto error;
                Py_DECREF(connectionTuple);
            }
        }

        free(table);
    }

    ConnDecrefPyObjs();
    return connectionsList;

error:
    ConnDecrefPyObjs();
    Py_XDECREF(connectionTuple);
    Py_XDECREF(addressTupleLocal);
    Py_XDECREF(addressTupleRemote);
    Py_DECREF(connectionsList);
    if (table != NULL)
        free(table);
    return NULL;
}


/*
 * Get process priority as a Python integer.
 */
static PyObject*
get_process_priority(PyObject* self, PyObject* args)
{
    long pid;
    DWORD priority;
    HANDLE hProcess;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }

    hProcess = psutil_handle_from_pid(pid);
    if (hProcess == NULL) {
        return NULL;
    }

    priority = GetPriorityClass(hProcess);
    CloseHandle(hProcess);
    if (priority == 0) {
        PyErr_SetFromWindowsErr(0);
        return NULL;
    }
    return Py_BuildValue("i", priority);
}


/*
 * Set process priority.
 */
static PyObject*
set_process_priority(PyObject* self, PyObject* args)
{
    long pid;
    int priority;
    int retval;
    HANDLE hProcess;
    DWORD dwDesiredAccess = PROCESS_QUERY_INFORMATION | PROCESS_SET_INFORMATION;
    if (! PyArg_ParseTuple(args, "li", &pid, &priority)) {
        return NULL;
    }

    hProcess = psutil_handle_from_pid_waccess(pid, dwDesiredAccess);
    if (hProcess == NULL) {
        return NULL;
    }

    retval = SetPriorityClass(hProcess, priority);
    CloseHandle(hProcess);
    if (retval == 0) {
        PyErr_SetFromWindowsErr(0);
        return NULL;
    }
    Py_INCREF(Py_None);
    return Py_None;
}


#if (_WIN32_WINNT >= 0x0600)  // Windows Vista
/*
 * Get process IO priority as a Python integer.
 */
static PyObject*
get_process_io_priority(PyObject* self, PyObject* args)
{
    long pid;
    HANDLE hProcess;
    PULONG IoPriority;

    _NtQueryInformationProcess NtQueryInformationProcess =
        (_NtQueryInformationProcess)GetProcAddress(
        GetModuleHandleA("ntdll.dll"), "NtQueryInformationProcess");

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    hProcess = psutil_handle_from_pid(pid);
    if (hProcess == NULL) {
        return NULL;
    }

    NtQueryInformationProcess(
        hProcess,
        ProcessIoPriority,
        &IoPriority,
        sizeof(ULONG),
        NULL
    );
    CloseHandle(hProcess);
    return Py_BuildValue("i", IoPriority);
}


/*
 * Set process IO priority.
 */
static PyObject*
set_process_io_priority(PyObject* self, PyObject* args)
{
    long pid;
    int prio;
    HANDLE hProcess;

    _NtSetInformationProcess NtSetInformationProcess =
        (_NtSetInformationProcess)GetProcAddress(
        GetModuleHandleA("ntdll.dll"), "NtSetInformationProcess");

    if (NtSetInformationProcess == NULL) {
        PyErr_SetString(PyExc_RuntimeError,
                        "couldn't get NtSetInformationProcess");
        return NULL;
    }

    if (! PyArg_ParseTuple(args, "li", &pid, &prio)) {
        return NULL;
    }
    hProcess = psutil_handle_from_pid_waccess(pid, PROCESS_ALL_ACCESS);
    if (hProcess == NULL) {
        return NULL;
    }

    NtSetInformationProcess(
        hProcess,
        ProcessIoPriority,
        (PVOID)&prio,
        sizeof((PVOID)prio)
    );

    CloseHandle(hProcess);
    Py_INCREF(Py_None);
    return Py_None;
}
#endif


/*
 * Return a Python tuple referencing process I/O counters.
 */
static PyObject*
get_process_io_counters(PyObject* self, PyObject* args)
{
    DWORD pid;
    HANDLE hProcess;
    IO_COUNTERS IoCounters;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    hProcess = psutil_handle_from_pid(pid);
    if (NULL == hProcess) {
        return NULL;
    }
    if (! GetProcessIoCounters(hProcess, &IoCounters)) {
        CloseHandle(hProcess);
        return PyErr_SetFromWindowsErr(0);
    }
    CloseHandle(hProcess);
    return Py_BuildValue("(KKKK)", IoCounters.ReadOperationCount,
                                   IoCounters.WriteOperationCount,
                                   IoCounters.ReadTransferCount,
                                   IoCounters.WriteTransferCount);
}


/*
 * Alternative implementation of the one above but bypasses ACCESS DENIED.
 */
static PyObject*
get_process_io_counters_2(PyObject* self, PyObject* args)
{
    DWORD pid;
    PSYSTEM_PROCESS_INFORMATION process;
    PVOID buffer;
    LONGLONG rcount, wcount, rbytes, wbytes;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (! get_process_info(pid, &process, &buffer)) {
        return NULL;
    }
    rcount = process->ReadOperationCount.QuadPart;
    wcount = process->WriteOperationCount.QuadPart;
    rbytes = process->ReadTransferCount.QuadPart;
    wbytes = process->WriteTransferCount.QuadPart;
    free(buffer);
    return Py_BuildValue("KKKK", rcount, wcount, rbytes, wbytes);
}


/*
 * Return process CPU affinity as a bitmask
 */
static PyObject*
get_process_cpu_affinity(PyObject* self, PyObject* args)
{
    DWORD pid;
    HANDLE hProcess;
    PDWORD_PTR proc_mask;
    PDWORD_PTR system_mask;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    hProcess = psutil_handle_from_pid(pid);
    if (hProcess == NULL) {
        return NULL;
    }
    if (GetProcessAffinityMask(hProcess, &proc_mask, &system_mask) == 0) {
        CloseHandle(hProcess);
        return PyErr_SetFromWindowsErr(0);
    }

    CloseHandle(hProcess);
#ifdef _WIN64
    return Py_BuildValue("K", (unsigned long long)proc_mask);
#else
    return Py_BuildValue("k", (unsigned long)proc_mask);
#endif
}


/*
 * Set process CPU affinity
 */
static PyObject*
set_process_cpu_affinity(PyObject* self, PyObject* args)
{
    DWORD pid;
    HANDLE hProcess;
    DWORD dwDesiredAccess = PROCESS_QUERY_INFORMATION | PROCESS_SET_INFORMATION;
    DWORD_PTR mask;

#ifdef _WIN64
    if (! PyArg_ParseTuple(args, "lK", &pid, &mask))
#else
    if (! PyArg_ParseTuple(args, "lk", &pid, &mask))
#endif
    {
        return NULL;
    }
    hProcess = psutil_handle_from_pid_waccess(pid, dwDesiredAccess);
    if (hProcess == NULL) {
        return NULL;
    }

    if (SetProcessAffinityMask(hProcess, mask) == 0) {
        CloseHandle(hProcess);
        return PyErr_SetFromWindowsErr(0);
    }

    CloseHandle(hProcess);
    Py_INCREF(Py_None);
    return Py_None;
}


/*
 * Return True if one of the process threads is in a waiting or
 * suspended status.
 */
static PyObject*
is_process_suspended(PyObject* self, PyObject* args)
{
    DWORD pid;
    ULONG i;
    PSYSTEM_PROCESS_INFORMATION process;
    PVOID buffer;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (! get_process_info(pid, &process, &buffer)) {
        return NULL;
    }
    for (i = 0; i < process->NumberOfThreads; i++) {
        if (process->Threads[i].ThreadState != Waiting ||
            process->Threads[i].WaitReason != Suspended)
        {
            free(buffer);
            Py_RETURN_FALSE;
        }
    }
    free(buffer);
    Py_RETURN_TRUE;
}


/*
 * Return path's disk total and free as a Python tuple.
 */
static PyObject*
get_disk_usage(PyObject* self, PyObject* args)
{
    BOOL retval;
    ULARGE_INTEGER _, total, free;
    LPCTSTR path;

    if (! PyArg_ParseTuple(args, "s", &path)) {
        return NULL;
    }

    Py_BEGIN_ALLOW_THREADS
    retval = GetDiskFreeSpaceEx(path, &_, &total, &free);
    Py_END_ALLOW_THREADS
    if (retval == 0) {
        return PyErr_SetFromWindowsErr(0);
    }

    return Py_BuildValue("(LL)", total.QuadPart, free.QuadPart);
}


/*
 * Return a Python list of named tuples with overall network I/O information
 */
static PyObject*
get_network_io_counters(PyObject* self, PyObject* args)
{
    int attempts = 0;
    int outBufLen = 15000;
    DWORD dwRetVal = 0;
    MIB_IFROW *pIfRow = NULL;
    ULONG flags = 0;
    ULONG family = AF_UNSPEC;
    PIP_ADAPTER_ADDRESSES pAddresses = NULL;
    PIP_ADAPTER_ADDRESSES pCurrAddresses = NULL;

    PyObject* py_retdict = PyDict_New();
    PyObject* py_nic_info = NULL;
    PyObject* py_pre_nic_name = NULL;
    PyObject* py_nic_name = NULL;

    if (py_retdict == NULL) {
        return NULL;
    }
    do {
        pAddresses = (IP_ADAPTER_ADDRESSES *) malloc(outBufLen);
        if (pAddresses == NULL) {
            PyErr_NoMemory();
            goto error;
        }

        dwRetVal = GetAdaptersAddresses(family, flags, NULL, pAddresses,
                                        &outBufLen);
        if (dwRetVal == ERROR_BUFFER_OVERFLOW) {
            free(pAddresses);
            pAddresses = NULL;
        }
        else {
            break;
        }

        attempts++;
    } while ((dwRetVal == ERROR_BUFFER_OVERFLOW) && (attempts < 3));

    if (dwRetVal != NO_ERROR) {
        PyErr_SetString(PyExc_RuntimeError,  "GetAdaptersAddresses() failed.");
        goto error;
    }

    pCurrAddresses = pAddresses;
    while (pCurrAddresses) {
        py_pre_nic_name = NULL;
        py_nic_name = NULL;
        py_nic_info = NULL;
        pIfRow = (MIB_IFROW *) malloc(sizeof(MIB_IFROW));

        if (pIfRow == NULL) {
            PyErr_NoMemory();
            goto error;
        }

        pIfRow->dwIndex = pCurrAddresses->IfIndex;
        dwRetVal = GetIfEntry(pIfRow);
        if (dwRetVal != NO_ERROR) {
            PyErr_SetString(PyExc_RuntimeError, "GetIfEntry() failed.");
            goto error;
        }

        py_nic_info = Py_BuildValue("(IIIIIIII)",
                                    pIfRow->dwOutOctets,
                                    pIfRow->dwInOctets,
                                    pIfRow->dwOutUcastPkts,
                                    pIfRow->dwInUcastPkts,
                                    pIfRow->dwInErrors,
                                    pIfRow->dwOutErrors,
                                    pIfRow->dwInDiscards,
                                    pIfRow->dwOutDiscards);
        if (!py_nic_info)
            goto error;

        py_pre_nic_name = PyUnicode_FromWideChar(
                                pCurrAddresses->FriendlyName,
                                wcslen(pCurrAddresses->FriendlyName));
        if (py_pre_nic_name == NULL)
            goto error;
        py_nic_name = PyUnicode_FromObject(py_pre_nic_name);
        if (py_nic_name == NULL)
            goto error;
        if (PyDict_SetItem(py_retdict, py_nic_name, py_nic_info))
            goto error;
        Py_XDECREF(py_pre_nic_name);
        Py_XDECREF(py_nic_name);
        Py_XDECREF(py_nic_info);

        free(pIfRow);
        pCurrAddresses = pCurrAddresses->Next;
    }

    free(pAddresses);
    return py_retdict;

error:
    Py_XDECREF(py_pre_nic_name);
    Py_XDECREF(py_nic_name);
    Py_XDECREF(py_nic_info);
    Py_DECREF(py_retdict);
    if (pAddresses != NULL)
        free(pAddresses);
    if (pIfRow != NULL)
        free(pIfRow);
    return NULL;
}

// fix for mingw32, see
// https://code.google.com/p/psutil/issues/detail?id=351#c2
typedef struct _DISK_PERFORMANCE_WIN_2008 {
       LARGE_INTEGER BytesRead;
       LARGE_INTEGER BytesWritten;
       LARGE_INTEGER ReadTime;
       LARGE_INTEGER WriteTime;
       LARGE_INTEGER IdleTime;
       DWORD         ReadCount;
       DWORD         WriteCount;
       DWORD         QueueDepth;
       DWORD         SplitCount;
       LARGE_INTEGER QueryTime;
       DWORD         StorageDeviceNumber;
       WCHAR         StorageManagerName[8];
} DISK_PERFORMANCE_WIN_2008;

/*
 * Return a Python dict of tuples for disk I/O information
 */
static PyObject*
get_disk_io_counters(PyObject* self, PyObject* args)
{
    DISK_PERFORMANCE_WIN_2008 diskPerformance;
    DWORD dwSize;
    HANDLE hDevice = NULL;
    char szDevice[MAX_PATH];
    char szDeviceDisplay[MAX_PATH];
    int devNum;
    PyObject* py_retdict = PyDict_New();
    PyObject* py_disk_info = NULL;
    if (py_retdict == NULL) {
        return NULL;
    }

    // Apparently there's no way to figure out how many times we have
    // to iterate in order to find valid drives.
    // Let's assume 32, which is higher than 26, the number of letters
    // in the alphabet (from A:\ to Z:\).
    for (devNum=0; devNum <= 32; ++devNum) {
        py_disk_info = NULL;
        sprintf(szDevice, "\\\\.\\PhysicalDrive%d", devNum);
        hDevice = CreateFile(szDevice, 0, FILE_SHARE_READ | FILE_SHARE_WRITE,
                             NULL, OPEN_EXISTING, 0, NULL);

        if (hDevice == INVALID_HANDLE_VALUE) {
            continue;
        }
        if (DeviceIoControl(hDevice, IOCTL_DISK_PERFORMANCE, NULL, 0,
                            &diskPerformance, sizeof(diskPerformance),
                            &dwSize, NULL))
        {
            sprintf(szDeviceDisplay, "PhysicalDrive%d", devNum);
            py_disk_info = Py_BuildValue("(IILLLL)",
                                         diskPerformance.ReadCount,
                                         diskPerformance.WriteCount,
                                         diskPerformance.BytesRead,
                                         diskPerformance.BytesWritten,
                                         (diskPerformance.ReadTime.QuadPart
                                            * 10) / 1000,
                                         (diskPerformance.WriteTime.QuadPart
                                            * 10) / 1000);
            if (!py_disk_info)
                goto error;
            if (PyDict_SetItemString(py_retdict, szDeviceDisplay, py_disk_info))
                goto error;
            Py_XDECREF(py_disk_info);
        }
        else {
            // XXX we might get here with ERROR_INSUFFICIENT_BUFFER when
            // compiling with mingw32; not sure what to do.
            //return PyErr_SetFromWindowsErr(0);
            ;;
        }

        CloseHandle(hDevice);
    }

    return py_retdict;

error:
    Py_XDECREF(py_disk_info);
    Py_DECREF(py_retdict);
    if (hDevice != NULL)
        CloseHandle(hDevice);
    return NULL;
}


static char *get_drive_type(int type)
{
    switch (type) {
        case DRIVE_FIXED:
            return "fixed";
        case DRIVE_CDROM:
            return "cdrom";
        case DRIVE_REMOVABLE:
            return "removable";
        case DRIVE_UNKNOWN:
            return "unknown";
        case DRIVE_NO_ROOT_DIR:
            return "unmounted";
        case DRIVE_REMOTE:
            return "remote";
        case DRIVE_RAMDISK:
            return "ramdisk";
        default:
            return "?";
    }
}


#define _ARRAYSIZE(a) (sizeof(a)/sizeof(a[0]))

/*
 * Return disk partitions as a list of tuples such as
 * (drive_letter, drive_letter, type, "")
 */
static PyObject*
get_disk_partitions(PyObject* self, PyObject* args)
{
    DWORD num_bytes;
    char drive_strings[255];
    char* drive_letter = drive_strings;
    int all;
    int type;
    int ret;
    char opts[20];
    LPTSTR fs_type[MAX_PATH + 1] = { 0 };
    DWORD pflags = 0;
    PyObject* py_all;
    PyObject* py_retlist = PyList_New(0);
    PyObject* py_tuple = NULL;

    if (py_retlist == NULL) {
        return NULL;
    }

    // avoid to visualize a message box in case something goes wrong
    // see http://code.google.com/p/psutil/issues/detail?id=264
    SetErrorMode(SEM_FAILCRITICALERRORS);

    if (! PyArg_ParseTuple(args, "O", &py_all)) {
        goto error;
    }
    all = PyObject_IsTrue(py_all);

    Py_BEGIN_ALLOW_THREADS
    num_bytes = GetLogicalDriveStrings(254, drive_letter);
    Py_END_ALLOW_THREADS

    if (num_bytes == 0) {
        PyErr_SetFromWindowsErr(0);
        goto error;
    }

    while (*drive_letter != 0) {
        py_tuple = NULL;
        opts[0] = 0;
        fs_type[0] = 0;

        Py_BEGIN_ALLOW_THREADS
        type = GetDriveType(drive_letter);
        Py_END_ALLOW_THREADS

        // by default we only show hard drives and cd-roms
        if (all == 0) {
            if ((type == DRIVE_UNKNOWN) ||
                (type == DRIVE_NO_ROOT_DIR) ||
                (type == DRIVE_REMOTE) ||
                (type == DRIVE_RAMDISK)) {
                goto next;
            }
            // floppy disk: skip it by default as it introduces a
            // considerable slowdown.
            if ((type == DRIVE_REMOVABLE) && (strcmp(drive_letter, "A:\\") == 0)) {
                goto next;
            }
        }

        ret = GetVolumeInformation(drive_letter, NULL, _ARRAYSIZE(drive_letter),
                                   NULL, NULL, &pflags, fs_type,
                                   _ARRAYSIZE(fs_type));
        if (ret == 0) {
            // We might get here in case of a floppy hard drive, in
            // which case the error is (21, "device not ready").
            // Let's pretend it didn't happen as we already have
            // the drive name and type ('removable').
            strcat(opts, "");
            SetLastError(0);
        }
        else {
            if (pflags & FILE_READ_ONLY_VOLUME) {
                strcat(opts, "ro");
            }
            else {
                strcat(opts, "rw");
            }
            if (pflags & FILE_VOLUME_IS_COMPRESSED) {
                strcat(opts, ",compressed");
            }
        }

        if (strlen(opts) > 0) {
            strcat(opts, ",");
        }
        strcat(opts, get_drive_type(type));

        py_tuple = Py_BuildValue("(ssss)",
            drive_letter,
            drive_letter,
            fs_type,  // either FAT, FAT32, NTFS, HPFS, CDFS, UDF or NWFS
            opts);
        if (!py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_DECREF(py_tuple);
        goto next;

        next:
            drive_letter = strchr(drive_letter, 0) + 1;
    }

    SetErrorMode(0);
    return py_retlist;

error:
    SetErrorMode(0);
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    return NULL;
}


#ifdef UNICODE
#define WTSOpenServer WTSOpenServerW
#else
#define WTSOpenServer WTSOpenServerA
#endif


/*
 * Return a Python dict of tuples for disk I/O information
 */
static PyObject*
get_system_users(PyObject* self, PyObject* args)
{
    HANDLE hServer = NULL;
    LPTSTR buffer_user = NULL;
    LPTSTR buffer_addr = NULL;
    PWTS_SESSION_INFO sessions = NULL;
    DWORD count;
    DWORD i;
    DWORD sessionId;
    DWORD bytes;
    PWTS_CLIENT_ADDRESS address;
    char address_str[50];
    long long unix_time;

    PWINSTATIONQUERYINFORMATIONW WinStationQueryInformationW;
    WINSTATION_INFO station_info;
    HINSTANCE hInstWinSta = NULL;
    ULONG returnLen;

    PyObject* py_retlist = PyList_New(0);
    PyObject* py_tuple = NULL;
    PyObject* py_address = NULL;
    if (py_retlist == NULL) {
        return NULL;
    }

    hInstWinSta = LoadLibraryA("winsta.dll");
    WinStationQueryInformationW = (PWINSTATIONQUERYINFORMATIONW)
        GetProcAddress(hInstWinSta, "WinStationQueryInformationW");

    hServer = WTSOpenServer('\0');
    if (hServer == NULL) {
        PyErr_SetFromWindowsErr(0);
        goto error;
    }

    if (WTSEnumerateSessions(hServer, 0, 1, &sessions, &count) == 0) {
        PyErr_SetFromWindowsErr(0);
        goto error;
    }

    for (i=0; i<count; i++) {
        py_address = NULL;
        py_tuple = NULL;
        sessionId = sessions[i].SessionId;
        if (buffer_user != NULL) {
            WTSFreeMemory(buffer_user);
        }
        if (buffer_addr != NULL) {
            WTSFreeMemory(buffer_addr);
        }

        buffer_user = NULL;
        buffer_addr = NULL;

        // username
        bytes = 0;
        if (WTSQuerySessionInformation(hServer, sessionId, WTSUserName,
                                        &buffer_user, &bytes) == 0) {
            PyErr_SetFromWindowsErr(0);
            goto error;
        }
        if (bytes == 1) {
            continue;
        }

        // address
        bytes = 0;
        if (WTSQuerySessionInformation(hServer, sessionId, WTSClientAddress,
                                       &buffer_addr, &bytes) == 0) {
            PyErr_SetFromWindowsErr(0);
            goto error;
        }

        address = (PWTS_CLIENT_ADDRESS)buffer_addr;
        if (address->AddressFamily == 0) {  // AF_INET
            sprintf(address_str, "%u.%u.%u.%u", address->Address[0],
                                                address->Address[1],
                                                address->Address[2],
                                                address->Address[3]);
            py_address = Py_BuildValue("s", address_str);
            if (!py_address)
                goto error;
        }
        else {
            py_address = Py_None;
        }

        // login time
        if (!WinStationQueryInformationW(hServer,
                                         sessionId,
                                         WinStationInformation,
                                         &station_info,
                                         sizeof(station_info),
                                         &returnLen))
                                         {
            goto error;
        }

        unix_time = ((LONGLONG)station_info.ConnectTime.dwHighDateTime) << 32;
        unix_time += station_info.ConnectTime.dwLowDateTime - 116444736000000000LL;
        unix_time /= 10000000;

        py_tuple = Py_BuildValue("sOd", buffer_user,
                                        py_address,
                                        (double)unix_time);
        if (!py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_XDECREF(py_address);
        Py_XDECREF(py_tuple);
    }

    WTSCloseServer(hServer);
    WTSFreeMemory(sessions);
    WTSFreeMemory(buffer_user);
    WTSFreeMemory(buffer_addr);
    FreeLibrary(hInstWinSta);
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_XDECREF(py_address);
    Py_DECREF(py_retlist);

    if (hInstWinSta != NULL) {
        FreeLibrary(hInstWinSta);
    }
    if (hServer != NULL) {
        WTSCloseServer(hServer);
    }
    if (sessions != NULL) {
        WTSFreeMemory(sessions);
    }
    if (buffer_user != NULL) {
        WTSFreeMemory(buffer_user);
    }
    if (buffer_addr != NULL) {
        WTSFreeMemory(buffer_addr);
    }
    return NULL;
}


/*
 * Return the number of handles opened by process.
 */
static PyObject*
get_process_num_handles(PyObject* self, PyObject* args)
{
    DWORD pid;
    HANDLE hProcess;
    DWORD handleCount;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    hProcess = psutil_handle_from_pid(pid);
    if (NULL == hProcess) {
        return NULL;
    }
    if (! GetProcessHandleCount(hProcess, &handleCount)) {
        CloseHandle(hProcess);
        return PyErr_SetFromWindowsErr(0);
    }
    CloseHandle(hProcess);
    return Py_BuildValue("k", handleCount);
}


/*
 * Alternative implementation of the one above but bypasses ACCESS DENIED.
 */
static PyObject*
get_process_num_handles_2(PyObject* self, PyObject* args)
{
    DWORD pid;
    PSYSTEM_PROCESS_INFORMATION process;
    PVOID buffer;
    ULONG count;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (! get_process_info(pid, &process, &buffer)) {
        return NULL;
    }
    count = process->HandleCount;
    free(buffer);
    return Py_BuildValue("k", count);
}


/*
 * Return the number of context switches executed by process.
 */
static PyObject*
get_process_num_ctx_switches(PyObject* self, PyObject* args)
{
    DWORD pid;
    PSYSTEM_PROCESS_INFORMATION process;
    PVOID buffer;
    ULONG i;
    ULONG total = 0;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (! get_process_info(pid, &process, &buffer)) {
        return NULL;
    }
    for (i=0; i < process->NumberOfThreads; i++) {
        total += process->Threads[i].ContextSwitches;
    }
    free(buffer);
    return Py_BuildValue("ki", total, 0);
}


static char *get_region_protection_string(ULONG protection)
{
    switch (protection & 0xff) {
        case PAGE_NOACCESS:
            return "";
        case PAGE_READONLY:
            return "r";
        case PAGE_READWRITE:
            return "rw";
        case PAGE_WRITECOPY:
            return "wc";
        case PAGE_EXECUTE:
            return "x";
        case PAGE_EXECUTE_READ:
            return "xr";
        case PAGE_EXECUTE_READWRITE:
            return "xrw";
        case PAGE_EXECUTE_WRITECOPY:
            return "xwc";
        default:
            return "?";
    }
}

/*
 * Return a list of process's memory mappings.
 */
static PyObject*
get_process_memory_maps(PyObject* self, PyObject* args)
{
    DWORD pid;
    HANDLE hProcess = NULL;
    MEMORY_BASIC_INFORMATION basicInfo;
    PVOID baseAddress;
    PVOID previousAllocationBase;
    CHAR mappedFileName[MAX_PATH];
    SYSTEM_INFO system_info;
    LPVOID maxAddr;
    PyObject* py_list = PyList_New(0);
    PyObject* py_tuple = NULL;

    if (py_list == NULL) {
        return NULL;
    }
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        goto error;
    }
    hProcess = psutil_handle_from_pid(pid);
    if (NULL == hProcess) {
        goto error;
    }

    GetSystemInfo(&system_info);
    maxAddr = system_info.lpMaximumApplicationAddress;
    baseAddress = NULL;
    previousAllocationBase = NULL;

    while (VirtualQueryEx(hProcess, baseAddress, &basicInfo,
                          sizeof(MEMORY_BASIC_INFORMATION)))
    {
        py_tuple = NULL;
        if (baseAddress > maxAddr) {
            break;
        }
        if (GetMappedFileNameA(hProcess, baseAddress, mappedFileName,
                               sizeof(mappedFileName)))
        {
            py_tuple = Py_BuildValue("(kssI)",
                (unsigned long)baseAddress,
                get_region_protection_string(basicInfo.Protect),
                mappedFileName,
                basicInfo.RegionSize
            );
            if (!py_tuple)
                goto error;
            if (PyList_Append(py_list, py_tuple))
                goto error;
            Py_DECREF(py_tuple);
        }
        previousAllocationBase = basicInfo.AllocationBase;
        baseAddress = (PCHAR)baseAddress + basicInfo.RegionSize;
    }

    CloseHandle(hProcess);
    return py_list;

error:
    Py_XDECREF(py_tuple);
    Py_DECREF(py_list);
    if (hProcess != NULL)
        CloseHandle(hProcess);
    return NULL;
}

// ------------------------ Python init ---------------------------

static PyMethodDef
PsutilMethods[] =
{
    // --- per-process functions

    {"get_process_name", get_process_name, METH_VARARGS,
        "Return process name"},
    {"get_process_cmdline", get_process_cmdline, METH_VARARGS,
        "Return process cmdline as a list of cmdline arguments"},
    {"get_process_exe", get_process_exe, METH_VARARGS,
        "Return path of the process executable"},
    {"get_process_ppid", get_process_ppid, METH_VARARGS,
        "Return process ppid as an integer"},
    {"kill_process", kill_process, METH_VARARGS,
        "Kill the process identified by the given PID"},
    {"get_process_cpu_times", get_process_cpu_times, METH_VARARGS,
        "Return tuple of user/kern time for the given PID"},
    {"get_process_create_time", get_process_create_time, METH_VARARGS,
        "Return a float indicating the process create time expressed in "
        "seconds since the epoch"},
    {"get_process_memory_info", get_process_memory_info, METH_VARARGS,
        "Return a tuple of process memory information"},
    {"get_process_cwd", get_process_cwd, METH_VARARGS,
        "Return process current working directory"},
    {"suspend_process", suspend_process, METH_VARARGS,
        "Suspend a process"},
    {"resume_process", resume_process, METH_VARARGS,
        "Resume a process"},
    {"get_process_open_files", get_process_open_files, METH_VARARGS,
        "Return files opened by process"},
    {"get_process_username", get_process_username, METH_VARARGS,
        "Return the username of a process"},
    {"get_process_connections", get_process_connections, METH_VARARGS,
        "Return the network connections of a process"},
    {"get_process_num_threads", get_process_num_threads, METH_VARARGS,
        "Return the network connections of a process"},
    {"get_process_threads", get_process_threads, METH_VARARGS,
        "Return process threads information as a list of tuple"},
    {"process_wait", process_wait, METH_VARARGS,
        "Wait for process to terminate and return its exit code."},
    {"get_process_priority", get_process_priority, METH_VARARGS,
        "Return process priority."},
    {"set_process_priority", set_process_priority, METH_VARARGS,
        "Set process priority."},
#if (_WIN32_WINNT >= 0x0600)  // Windows Vista
    {"get_process_io_priority", get_process_io_priority, METH_VARARGS,
        "Return process IO priority."},
    {"set_process_io_priority", set_process_io_priority, METH_VARARGS,
        "Set process IO priority."},
#endif
    {"get_process_cpu_affinity", get_process_cpu_affinity, METH_VARARGS,
        "Return process CPU affinity as a bitmask."},
    {"set_process_cpu_affinity", set_process_cpu_affinity, METH_VARARGS,
        "Set process CPU affinity."},
    {"get_process_io_counters", get_process_io_counters, METH_VARARGS,
        "Get process I/O counters."},
    {"is_process_suspended", is_process_suspended, METH_VARARGS,
        "Return True if one of the process threads is in a suspended state"},
    {"get_process_num_handles", get_process_num_handles, METH_VARARGS,
        "Return the number of handles opened by process."},
    {"get_process_num_ctx_switches", get_process_num_ctx_switches, METH_VARARGS,
        "Return the number of context switches performed by process."},
    {"get_process_memory_maps", get_process_memory_maps, METH_VARARGS,
        "Return a list of process's memory mappings"},

    // --- alternative pinfo interface
    {"get_process_cpu_times_2", get_process_cpu_times_2, METH_VARARGS,
        "Alternative implementation"},
    {"get_process_create_time_2", get_process_create_time_2, METH_VARARGS,
        "Alternative implementation"},
    {"get_process_num_handles_2", get_process_num_handles_2, METH_VARARGS,
        "Alternative implementation"},
    {"get_process_io_counters_2", get_process_io_counters_2, METH_VARARGS,
        "Alternative implementation"},
    {"get_process_memory_info_2", get_process_memory_info_2, METH_VARARGS,
        "Alternative implementation"},

    // --- system-related functions

    {"get_pid_list", get_pid_list, METH_VARARGS,
        "Returns a list of PIDs currently running on the system"},
    {"pid_exists", pid_exists, METH_VARARGS,
        "Determine if the process exists in the current process list."},
    {"get_num_cpus", get_num_cpus, METH_VARARGS,
        "Returns the number of CPUs on the system"},
    {"get_system_boot_time", get_system_boot_time, METH_VARARGS,
        "Return the system boot time expressed in seconds since the epoch."},
    {"get_virtual_mem", get_virtual_mem, METH_VARARGS,
        "Return the total amount of physical memory, in bytes"},
    {"get_system_cpu_times", get_system_cpu_times, METH_VARARGS,
        "Return system per-cpu times as a list of tuples"},
    {"get_disk_usage", get_disk_usage, METH_VARARGS,
        "Return path's disk total and free as a Python tuple."},
    {"get_network_io_counters", get_network_io_counters, METH_VARARGS,
        "Return dict of tuples of networks I/O information."},
    {"get_disk_io_counters", get_disk_io_counters, METH_VARARGS,
         "Return dict of tuples of disks I/O information."},
    {"get_system_users", get_system_users, METH_VARARGS,
        "Return a list of currently connected users."},
    {"get_disk_partitions", get_disk_partitions, METH_VARARGS,
        "Return disk partitions."},


     // --- windows API bindings
    {"win32_QueryDosDevice", win32_QueryDosDevice, METH_VARARGS,
        "QueryDosDevice binding"},

    {NULL, NULL, 0, NULL}
};


struct module_state {
    PyObject *error;
};

#if PY_MAJOR_VERSION >= 3
    #define GETSTATE(m) ((struct module_state*)PyModule_GetState(m))
#else
    #define GETSTATE(m) (&_state)
    static struct module_state _state;
#endif

#if PY_MAJOR_VERSION >= 3

    static int psutil_mswindows_traverse(PyObject *m, visitproc visit, void *arg) {
        Py_VISIT(GETSTATE(m)->error);
        return 0;
    }

    static int psutil_mswindows_clear(PyObject *m) {
        Py_CLEAR(GETSTATE(m)->error);
        return 0;
    }

    static struct PyModuleDef moduledef = {
            PyModuleDef_HEAD_INIT,
            "psutil_mswindows",
            NULL,
            sizeof(struct module_state),
            PsutilMethods,
            NULL,
            psutil_mswindows_traverse,
            psutil_mswindows_clear,
            NULL
    };

#define INITERROR return NULL

    PyObject* PyInit__psutil_mswindows(void)

#else
    #define INITERROR return
    void init_psutil_mswindows(void)
#endif
{
    struct module_state *st = NULL;
#if PY_MAJOR_VERSION >= 3
    PyObject *module = PyModule_Create(&moduledef);
#else
    PyObject *module = Py_InitModule("_psutil_mswindows", PsutilMethods);
#endif

    if (module == NULL) {
        INITERROR;
    }

    st = GETSTATE(module);
    st->error = PyErr_NewException("_psutil_mswindow.Error", NULL, NULL);
    if (st->error == NULL) {
        Py_DECREF(module);
        INITERROR;
    }

    // Public constants
    // http://msdn.microsoft.com/en-us/library/ms683211(v=vs.85).aspx
    PyModule_AddIntConstant(module, "ABOVE_NORMAL_PRIORITY_CLASS",
                                     ABOVE_NORMAL_PRIORITY_CLASS);
    PyModule_AddIntConstant(module, "BELOW_NORMAL_PRIORITY_CLASS",
                                     BELOW_NORMAL_PRIORITY_CLASS);
    PyModule_AddIntConstant(module, "HIGH_PRIORITY_CLASS",
                                     HIGH_PRIORITY_CLASS);
    PyModule_AddIntConstant(module, "IDLE_PRIORITY_CLASS",
                                     IDLE_PRIORITY_CLASS);
    PyModule_AddIntConstant(module, "NORMAL_PRIORITY_CLASS",
                                     NORMAL_PRIORITY_CLASS);
    PyModule_AddIntConstant(module, "REALTIME_PRIORITY_CLASS",
                                     REALTIME_PRIORITY_CLASS);
    // private constants
    PyModule_AddIntConstant(module, "INFINITE", INFINITE);
    PyModule_AddIntConstant(module, "ERROR_ACCESS_DENIED", ERROR_ACCESS_DENIED);
    SetSeDebug();

#if PY_MAJOR_VERSION >= 3
    return module;
#endif
}
