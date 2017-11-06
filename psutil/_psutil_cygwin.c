#define WIN32_LEAN_AND_MEAN

#include <windows.h>
#include <Psapi.h>
#include <winsock2.h>
#include <WinIoCtl.h>
#include <tlhelp32.h>

/* On Cygwin, mprapi.h is missing a necessary include of wincrypt.h
 * which is needed to define some types, so we include it here since
 * iphlpapi.h includes iprtrmib.h which in turn includes mprapi.h
 */
#include <wincrypt.h>

/* TODO: There are some structs defined in netioapi.h that are only defined in
 * ws2ipdef.h has been included; however, for reasons unknown to me currently,
 * the headers included with Cygwin deliberately do not include ws2ipdef.h
 * when compiling for Cygwin.  For now I include it manually which seems to work
 * but it would be good to track down why this was in the first place.
 */
#include <ws2ipdef.h>
#include <iphlpapi.h>

#include <sys/cygwin.h>

#include <Python.h>

#include <mntent.h>
#include <utmpx.h>

#include "arch/windows/process_info.h"
#include "arch/windows/utils.h"
#include "_psutil_common.h"


/*
 * ============================================================================
 * Utilities
 * ============================================================================
 */

 // a flag for connections without an actual status
static int PSUTIL_CONN_NONE = 128;
#define BYTESWAP_USHORT(x) ((((USHORT)(x) << 8) | ((USHORT)(x) >> 8)) & 0xffff)
#define _psutil_conn_decref_objs() \
    Py_DECREF(_AF_INET); \
    Py_DECREF(_AF_INET6);\
    Py_DECREF(_SOCK_STREAM);\
    Py_DECREF(_SOCK_DGRAM);


// fix for mingw32, see
// https://github.com/giampaolo/psutil/issues/351#c2
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

/* Python wrappers for Cygwin's cygwin_conv_path API--accepts and returns
 * Python unicode strings.  Always returns absolute paths.
 */
static PyObject *
psutil_cygwin_conv_path(PyObject *self, PyObject *args,
                        cygwin_conv_path_t what) {
    char *from;
    char *to;
    ssize_t size;

    if (!PyArg_ParseTuple(args, "s", &from)) {
        return NULL;
    }

    size = cygwin_conv_path(what, from, NULL, 0);

    if (size < 0) {
        /* TODO: Better error handling */
        return size;
    }

    to = malloc(size);
    if (to == NULL) {
        return NULL;
    }

    if (cygwin_conv_path(what, from, to, size)) {
        return NULL;
    }

    /* size includes the terminal null byte */
#if PY_MAJOR_VERSION >= 3
    return PyUnicode_FromStringAndSize(to, size - 1);
#else
    return PyString_FromStringAndSize(to, size - 1);
#endif
}


static PyObject *
psutil_cygpath_to_winpath(PyObject *self, PyObject *args) {
    return psutil_cygwin_conv_path(self, args, CCP_POSIX_TO_WIN_A);
}


static PyObject *
psutil_winpath_to_cygpath(PyObject *self, PyObject *args) {
    return psutil_cygwin_conv_path(self, args, CCP_WIN_A_TO_POSIX);
}


static PyObject*
psutil_cygpid_to_winpid(PyObject *self, PyObject *args) {
    pid_t pid;
    DWORD winpid;

    if (! PyArg_ParseTuple(args, "l", (long*) &pid))
        return NULL;

    if (!(winpid = (DWORD)cygwin_internal(CW_CYGWIN_PID_TO_WINPID, pid)))
        return NoSuchProcess();

#if PY_MAJOR_VERSION >= 3
    return PyLong_FromLong((long) winpid);
#else
    return PyInt_FromLong((long) winpid);
#endif
}


static PyObject*
psutil_winpid_to_cygpid(PyObject *self, PyObject *args) {
    pid_t pid;
    int winpid;

    if (! PyArg_ParseTuple(args, "i", &winpid))
        return NULL;

    /* For some reason (perhaps historical) Cygwin provides a function
     * specifically for this purpose, rather than using cygwin_internal
     * as in the opposite case. */
    if ((pid = cygwin_winpid_to_pid(winpid)) < 0)
        return NoSuchProcess();

#if PY_MAJOR_VERSION >= 3
    return PyLong_FromLong((long) pid);
#else
    return PyInt_FromLong((long) pid);
#endif
}


static ULONGLONG (*psutil_GetTickCount64)(void) = NULL;

/*
 * Return a Python float representing the system uptime expressed in seconds
 * since the epoch.
 */
static PyObject *
psutil_boot_time(PyObject *self, PyObject *args) {
    double uptime;
    double pt;
    FILETIME fileTime;
    long long ll;
    HINSTANCE hKernel32;
    psutil_GetTickCount64 = NULL;

    GetSystemTimeAsFileTime(&fileTime);

    /*
    HUGE thanks to:
    http://johnstewien.spaces.live.com/blog/cns!E6885DB5CEBABBC8!831.entry

    This function converts the FILETIME structure to a 32-bit Unix time.
    The Unix time is a 32-bit value for the number of seconds since
    January 1, 1970. A FILETIME is a 64-bit for the number of
    100-nanosecond periods since January 1, 1601. Convert by
    subtracting the number of 100-nanosecond period betwee 01-01-1970
    and 01-01-1601, from time_t the divide by 1e+7 to get to the same
    base granularity.
    */
    ll = (((LONGLONG)(fileTime.dwHighDateTime)) << 32) \
        + fileTime.dwLowDateTime;
    pt = (double)(ll - 116444736000000000ull) / 1e7;

    // GetTickCount64() is Windows Vista+ only. Dinamically load
    // GetTickCount64() at runtime. We may have used
    // "#if (_WIN32_WINNT >= 0x0600)" pre-processor but that way
    // the produced exe/wheels cannot be used on Windows XP, see:
    // https://github.com/giampaolo/psutil/issues/811#issuecomment-230639178
    hKernel32 = GetModuleHandleW(L"KERNEL32");
    psutil_GetTickCount64 = (void*)GetProcAddress(hKernel32, "GetTickCount64");
    if (psutil_GetTickCount64 != NULL) {
        // Windows >= Vista
        uptime = (double)psutil_GetTickCount64() / 1000.00;
    }
    else {
        // Windows XP.
        // GetTickCount() time will wrap around to zero if the
        // system is run continuously for 49.7 days.
        uptime = (double)GetTickCount() / 1000.00;
    }

    return Py_BuildValue("d", floor(pt - uptime));
}


/* TODO: Copied verbatim from the Linux module; refactor */
/*
 * Return disk mounted partitions as a list of tuples including device,
 * mount point and filesystem type
 */
static PyObject *
psutil_disk_partitions(PyObject *self, PyObject *args) {
    FILE *file = NULL;
    struct mntent *entry;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;

    if (py_retlist == NULL)
        return NULL;

    // MOUNTED constant comes from mntent.h and it's == '/etc/mtab'
    Py_BEGIN_ALLOW_THREADS
    file = setmntent(MOUNTED, "r");
    Py_END_ALLOW_THREADS
    if ((file == 0) || (file == NULL)) {
        PyErr_SetFromErrnoWithFilename(PyExc_OSError, MOUNTED);
        goto error;
    }

    while ((entry = getmntent(file))) {
        if (entry == NULL) {
            PyErr_Format(PyExc_RuntimeError, "getmntent() failed");
            goto error;
        }
        py_tuple = Py_BuildValue("(ssss)",
                                 entry->mnt_fsname,  // device
                                 entry->mnt_dir,     // mount point
                                 entry->mnt_type,    // fs type
                                 entry->mnt_opts);   // options
        if (! py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_DECREF(py_tuple);
    }
    endmntent(file);
    return py_retlist;

error:
    if (file != NULL)
        endmntent(file);
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    return NULL;
}


/* Copied verbatim from the Windows module
   TODO: Refactor this later
 */
/*
 * Return process CPU affinity as a bitmask
 */
static PyObject *
psutil_proc_cpu_affinity_get(PyObject *self, PyObject *args) {
    DWORD pid;
    HANDLE hProcess;
    DWORD_PTR proc_mask;
    DWORD_PTR system_mask;

    if (! PyArg_ParseTuple(args, "l", &pid))
        return NULL;
    hProcess = psutil_handle_from_pid(pid);
    if (hProcess == NULL)
        return NULL;

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
 * Return process memory information as a Python tuple.
 */
static PyObject *
psutil_proc_memory_info(PyObject *self, PyObject *args) {
    HANDLE hProcess;
    DWORD pid;
#if (_WIN32_WINNT >= 0x0501)  // Windows XP with SP2
    PROCESS_MEMORY_COUNTERS_EX cnt;
#else
    PROCESS_MEMORY_COUNTERS cnt;
#endif
    SIZE_T private = 0;

    if (! PyArg_ParseTuple(args, "l", &pid))
        return NULL;

    hProcess = psutil_handle_from_pid(pid);
    if (NULL == hProcess)
        return NULL;

    if (! GetProcessMemoryInfo(hProcess, (PPROCESS_MEMORY_COUNTERS)&cnt,
                               sizeof(cnt))) {
        CloseHandle(hProcess);
        return PyErr_SetFromWindowsErr(0);
    }

#if (_WIN32_WINNT >= 0x0501)  // Windows XP with SP2
    private = cnt.PrivateUsage;
#endif

    CloseHandle(hProcess);

    // PROCESS_MEMORY_COUNTERS values are defined as SIZE_T which on 64bits
    // is an (unsigned long long) and on 32bits is an (unsigned int).
    // "_WIN64" is defined if we're running a 64bit Python interpreter not
    // exclusively if the *system* is 64bit.
#if defined(_WIN64)
    return Py_BuildValue(
        "(kKKKKKKKKK)",
        cnt.PageFaultCount,  // unsigned long
        (unsigned long long)cnt.PeakWorkingSetSize,
        (unsigned long long)cnt.WorkingSetSize,
        (unsigned long long)cnt.QuotaPeakPagedPoolUsage,
        (unsigned long long)cnt.QuotaPagedPoolUsage,
        (unsigned long long)cnt.QuotaPeakNonPagedPoolUsage,
        (unsigned long long)cnt.QuotaNonPagedPoolUsage,
        (unsigned long long)cnt.PagefileUsage,
        (unsigned long long)cnt.PeakPagefileUsage,
        (unsigned long long)private);
#else
    return Py_BuildValue(
        "(kIIIIIIIII)",
        cnt.PageFaultCount,    // unsigned long
        (unsigned int)cnt.PeakWorkingSetSize,
        (unsigned int)cnt.WorkingSetSize,
        (unsigned int)cnt.QuotaPeakPagedPoolUsage,
        (unsigned int)cnt.QuotaPagedPoolUsage,
        (unsigned int)cnt.QuotaPeakNonPagedPoolUsage,
        (unsigned int)cnt.QuotaNonPagedPoolUsage,
        (unsigned int)cnt.PagefileUsage,
        (unsigned int)cnt.PeakPagefileUsage,
        (unsigned int)private);
#endif
}


/*
 * Alternative implementation of the one above but bypasses ACCESS DENIED.
 */
static PyObject *
psutil_proc_memory_info_2(PyObject *self, PyObject *args) {
    DWORD pid;
    PSYSTEM_PROCESS_INFORMATION process;
    PVOID buffer;
    SIZE_T private;
    unsigned long pfault_count;

#if defined(_WIN64)
    unsigned long long m1, m2, m3, m4, m5, m6, m7, m8;
#else
    unsigned int m1, m2, m3, m4, m5, m6, m7, m8;
#endif

    if (! PyArg_ParseTuple(args, "l", &pid))
        return NULL;
    if (! psutil_get_proc_info(pid, &process, &buffer))
        return NULL;

#if (_WIN32_WINNT >= 0x0501)  // Windows XP with SP2
    private = process->PrivatePageCount;
#else
    private = 0;
#endif
    pfault_count = process->PageFaultCount;

    m1 = process->PeakWorkingSetSize;
    m2 = process->WorkingSetSize;
    m3 = process->QuotaPeakPagedPoolUsage;
    m4 = process->QuotaPagedPoolUsage;
    m5 = process->QuotaPeakNonPagedPoolUsage;
    m6 = process->QuotaNonPagedPoolUsage;
    m7 = process->PagefileUsage;
    m8 = process->PeakPagefileUsage;

    free(buffer);

    // SYSTEM_PROCESS_INFORMATION values are defined as SIZE_T which on 64
    // bits is an (unsigned long long) and on 32bits is an (unsigned int).
    // "_WIN64" is defined if we're running a 64bit Python interpreter not
    // exclusively if the *system* is 64bit.
#if defined(_WIN64)
    return Py_BuildValue("(kKKKKKKKKK)",
#else
    return Py_BuildValue("(kIIIIIIIII)",
#endif
        pfault_count, m1, m2, m3, m4, m5, m6, m7, m8, private);
}


/**
 * Returns the USS of the process.
 * Reference:
 * https://dxr.mozilla.org/mozilla-central/source/xpcom/base/
 *     nsMemoryReporterManager.cpp
 */
static PyObject *
psutil_proc_memory_uss(PyObject *self, PyObject *args)
{
    DWORD pid;
    HANDLE proc;
    PSAPI_WORKING_SET_INFORMATION tmp;
    DWORD tmp_size = sizeof(tmp);
    size_t entries;
    size_t private_pages;
    size_t i;
    DWORD info_array_size;
    PSAPI_WORKING_SET_INFORMATION* info_array;
    SYSTEM_INFO system_info;
    PyObject* py_result = NULL;
    unsigned long long total = 0;

    if (! PyArg_ParseTuple(args, "l", &pid))
        return NULL;

    proc = psutil_handle_from_pid(pid);
    if (proc == NULL)
        return NULL;

    // Determine how many entries we need.
    memset(&tmp, 0, tmp_size);
    if (!QueryWorkingSet(proc, &tmp, tmp_size)) {
        // NB: QueryWorkingSet is expected to fail here due to the
        // buffer being too small.
        if (tmp.NumberOfEntries == 0) {
            PyErr_SetFromWindowsErr(0);
            goto done;
        }
    }

    // Fudge the size in case new entries are added between calls.
    entries = tmp.NumberOfEntries * 2;

    if (!entries) {
        goto done;
    }

    info_array_size = tmp_size + (entries * sizeof(PSAPI_WORKING_SET_BLOCK));
    info_array = (PSAPI_WORKING_SET_INFORMATION*)malloc(info_array_size);
    if (!info_array) {
        PyErr_NoMemory();
        goto done;
    }

    if (!QueryWorkingSet(proc, info_array, info_array_size)) {
        PyErr_SetFromWindowsErr(0);
        goto done;
    }

    entries = (size_t)info_array->NumberOfEntries;
    private_pages = 0;
    for (i = 0; i < entries; i++) {
        // Count shared pages that only one process is using as private.
        if (!info_array->WorkingSetInfo[i].Shared ||
                info_array->WorkingSetInfo[i].ShareCount <= 1) {
            private_pages++;
        }
    }

    // GetSystemInfo has no return value.
    GetSystemInfo(&system_info);
    total = private_pages * system_info.dwPageSize;
    py_result = Py_BuildValue("K", total);

done:
    if (proc) {
        CloseHandle(proc);
    }

    if (info_array) {
        free(info_array);
    }

    return py_result;
}


/*
 * Set process CPU affinity
 */
static PyObject *
psutil_proc_cpu_affinity_set(PyObject *self, PyObject *args) {
    DWORD pid;
    HANDLE hProcess;
    DWORD dwDesiredAccess = \
        PROCESS_QUERY_INFORMATION | PROCESS_SET_INFORMATION;
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
    if (hProcess == NULL)
        return NULL;

    if (SetProcessAffinityMask(hProcess, mask) == 0) {
        CloseHandle(hProcess);
        PyErr_SetFromWindowsErr(0);
        return NULL;
    }

    CloseHandle(hProcess);
    Py_RETURN_NONE;
}


/*
 * Return a Python float indicating the process create time expressed in
 * seconds since the epoch.
 */
static PyObject *
psutil_proc_create_time(PyObject *self, PyObject *args) {
    long        pid;
    long long   unix_time;
    DWORD       exitCode;
    HANDLE      hProcess;
    BOOL        ret;
    FILETIME    ftCreate, ftExit, ftKernel, ftUser;

    if (! PyArg_ParseTuple(args, "l", &pid))
        return NULL;

    // special case for PIDs 0 and 4, return system boot time
    if (0 == pid || 4 == pid)
        return psutil_boot_time(NULL, NULL);

    hProcess = psutil_handle_from_pid(pid);
    if (hProcess == NULL) 
        return NULL;

    if (! GetProcessTimes(hProcess, &ftCreate, &ftExit, &ftKernel, &ftUser)) {
        CloseHandle(hProcess);
        printf("GetLastError() = %d\n", GetLastError());
        if (GetLastError() == ERROR_ACCESS_DENIED) {
            // usually means the process has died so we throw a
            // NoSuchProcess here
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
        if (exitCode != STILL_ACTIVE)
            return NoSuchProcess();
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


// TODO: Copied verbatim from the windows module
/*
 * Get various process information by using NtQuerySystemInformation.
 * We use this as a fallback when faster functions fail with access
 * denied. This is slower because it iterates over all processes.
 * Returned tuple includes the following process info:
 *
 * - num_threads
 * - ctx_switches
 * - num_handles (fallback)
 * - user/kernel times (fallback)
 * - create time (fallback)
 * - io counters (fallback)
 */
static PyObject *
psutil_proc_info(PyObject *self, PyObject *args) {
    DWORD pid;
    PSYSTEM_PROCESS_INFORMATION process;
    PVOID buffer;
    ULONG num_handles;
    ULONG i;
    ULONG ctx_switches = 0;
    double user_time;
    double kernel_time;
    long long create_time;
    int num_threads;
    LONGLONG io_rcount, io_wcount, io_rbytes, io_wbytes;


    if (! PyArg_ParseTuple(args, "l", &pid))
        return NULL;
    if (! psutil_get_proc_info(pid, &process, &buffer))
        return NULL;

    num_handles = process->HandleCount;
    for (i = 0; i < process->NumberOfThreads; i++)
        ctx_switches += process->Threads[i].ContextSwitches;
    user_time = (double)process->UserTime.HighPart * 429.4967296 + \
                (double)process->UserTime.LowPart * 1e-7;
    kernel_time = (double)process->KernelTime.HighPart * 429.4967296 + \
                  (double)process->KernelTime.LowPart * 1e-7;
    // Convert the LARGE_INTEGER union to a Unix time.
    // It's the best I could find by googling and borrowing code here
    // and there. The time returned has a precision of 1 second.
    if (0 == pid || 4 == pid) {
        // the python module will translate this into BOOT_TIME later
        create_time = 0;
    }
    else {
        create_time = ((LONGLONG)process->CreateTime.HighPart) << 32;
        create_time += process->CreateTime.LowPart - 116444736000000000LL;
        create_time /= 10000000;
    }
    num_threads = (int)process->NumberOfThreads;
    io_rcount = process->ReadOperationCount.QuadPart;
    io_wcount = process->WriteOperationCount.QuadPart;
    io_rbytes = process->ReadTransferCount.QuadPart;
    io_wbytes = process->WriteTransferCount.QuadPart;
    free(buffer);

    return Py_BuildValue(
        "kkdddiKKKK",
        num_handles,
        ctx_switches,
        user_time,
        kernel_time,
        (double)create_time,
        num_threads,
        io_rcount,
        io_wcount,
        io_rbytes,
        io_wbytes
    );
}


// TODO: Copied verbatim from windows module
/*
 * Return a Python tuple referencing process I/O counters.
 */
static PyObject *
psutil_proc_io_counters(PyObject *self, PyObject *args) {
    DWORD pid;
    HANDLE hProcess;
    IO_COUNTERS IoCounters;

    if (! PyArg_ParseTuple(args, "l", &pid))
        return NULL;
    hProcess = psutil_handle_from_pid(pid);
    if (NULL == hProcess)
        return NULL;
    if (! GetProcessIoCounters(hProcess, &IoCounters)) {
        CloseHandle(hProcess);
        return PyErr_SetFromWindowsErr(0);
    }
    CloseHandle(hProcess);
    return Py_BuildValue("(KKKK)",
                         IoCounters.ReadOperationCount,
                         IoCounters.WriteOperationCount,
                         IoCounters.ReadTransferCount,
                         IoCounters.WriteTransferCount);
}


static PyObject *
psutil_proc_threads(PyObject *self, PyObject *args) {
    HANDLE hThread;
    THREADENTRY32 te32 = {0};
    long pid;
    int pid_return;
    int rc;
    FILETIME ftDummy, ftKernel, ftUser;
    HANDLE hThreadSnap = NULL;
    PyObject *py_tuple = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;
    if (! PyArg_ParseTuple(args, "l", &pid))
        goto error;
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
    if (pid_return == -1)
        goto error;

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
    do {
        if (te32.th32OwnerProcessID == pid) {
            py_tuple = NULL;
            hThread = NULL;
            hThread = OpenThread(THREAD_QUERY_INFORMATION,
                                 FALSE, te32.th32ThreadID);
            if (hThread == NULL) {
                // thread has disappeared on us
                continue;
            }

            rc = GetThreadTimes(hThread, &ftDummy, &ftDummy, &ftKernel,
                                &ftUser);
            if (rc == 0) {
                PyErr_SetFromWindowsErr(0);
                goto error;
            }

            /*
             * User and kernel times are represented as a FILETIME structure
             * wich contains a 64-bit value representing the number of
             * 100-nanosecond intervals since January 1, 1601 (UTC):
             * http://msdn.microsoft.com/en-us/library/ms724284(VS.85).aspx
             * To convert it into a float representing the seconds that the
             * process has executed in user/kernel mode I borrowed the code
             * below from Python's Modules/posixmodule.c
             */
            py_tuple = Py_BuildValue(
                "kdd",
                te32.th32ThreadID,
                (double)(ftUser.dwHighDateTime * 429.4967296 + \
                         ftUser.dwLowDateTime * 1e-7),
                (double)(ftKernel.dwHighDateTime * 429.4967296 + \
                         ftKernel.dwLowDateTime * 1e-7));
            if (!py_tuple)
                goto error;
            if (PyList_Append(py_retlist, py_tuple))
                goto error;
            Py_DECREF(py_tuple);

            CloseHandle(hThread);
        }
    } while (Thread32Next(hThreadSnap, &te32));

    CloseHandle(hThreadSnap);
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    if (hThread != NULL)
        CloseHandle(hThread);
    if (hThreadSnap != NULL)
        CloseHandle(hThreadSnap);
    return NULL;
}


// TODO: This is copied almost verbatim from the Linux module, but on Cygwin
// it's necessary to use the utmpx APIs in order to access some of the extended
// utmp fields, such as ut_tv.
/*
 * Return currently connected users as a list of tuples.
 */
static PyObject *
psutil_users(PyObject *self, PyObject *args) {
    struct utmpx *ut;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;
    PyObject *py_user_proc = NULL;

    if (py_retlist == NULL)
        return NULL;
    setutxent();
    while (NULL != (ut = getutxent())) {
        py_tuple = NULL;
        py_user_proc = NULL;
        if (ut->ut_type == USER_PROCESS)
            py_user_proc = Py_True;
        else
            py_user_proc = Py_False;
        py_tuple = Py_BuildValue(
            "(sssfO)",
            ut->ut_user,              // username
            ut->ut_line,              // tty
            ut->ut_host,              // hostname
            (float)ut->ut_tv.tv_sec,  // tstamp
            py_user_proc              // (bool) user process
        );
    if (! py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_DECREF(py_tuple);
    }
    endutent();
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_XDECREF(py_user_proc);
    Py_DECREF(py_retlist);
    endutent();
    return NULL;
}


PIP_ADAPTER_ADDRESSES
psutil_get_nic_addresses(int all) {
    // allocate a 15 KB buffer to start with
    int outBufLen = 15000;
    DWORD dwRetVal = 0;
    ULONG attempts = 0;
    PIP_ADAPTER_ADDRESSES pAddresses = NULL;

    do {
        pAddresses = (IP_ADAPTER_ADDRESSES *) malloc(outBufLen);
        if (pAddresses == NULL) {
            PyErr_NoMemory();
            return NULL;
        }

        dwRetVal = GetAdaptersAddresses(
                AF_UNSPEC,
                all ? GAA_FLAG_INCLUDE_ALL_INTERFACES : 0,
                NULL, pAddresses,
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
        PyErr_SetString(PyExc_RuntimeError, "GetAdaptersAddresses() failed.");
        return NULL;
    }

    return pAddresses;
}


/*
 * Provides stats about NIC interfaces installed on the system.
 * TODO: get 'duplex' (currently it's hard coded to '2', aka
         'full duplex')
 */

/* TODO: This and the helper get_nic_addresses are copied *almost* verbatim
   from the windows module.  One difference is the use of snprintf with
   the %ls format, as opposed to using sprintf_s from MSCRT
   The other difference is that get_nic_addresses() returns all interfaces,
   */
static PyObject *
psutil_net_if_stats(PyObject *self, PyObject *args) {
    int i;
    DWORD dwSize = 0;
    DWORD dwRetVal = 0;
    MIB_IFTABLE *pIfTable;
    MIB_IFROW *pIfRow;
    PIP_ADAPTER_ADDRESSES pAddresses = NULL;
    PIP_ADAPTER_ADDRESSES pCurrAddresses = NULL;
    char descr[MAX_PATH];
    int ifname_found;

    PyObject *py_nic_name = NULL;
    PyObject *py_retdict = PyDict_New();
    PyObject *py_ifc_info = NULL;
    PyObject *py_is_up = NULL;

    if (py_retdict == NULL)
        return NULL;

    pAddresses = psutil_get_nic_addresses(1);
    if (pAddresses == NULL)
        goto error;

    pIfTable = (MIB_IFTABLE *) malloc(sizeof (MIB_IFTABLE));
    if (pIfTable == NULL) {
        PyErr_NoMemory();
        goto error;
    }
    dwSize = sizeof(MIB_IFTABLE);
    if (GetIfTable(pIfTable, &dwSize, FALSE) == ERROR_INSUFFICIENT_BUFFER) {
        free(pIfTable);
        pIfTable = (MIB_IFTABLE *) malloc(dwSize);
        if (pIfTable == NULL) {
            PyErr_NoMemory();
            goto error;
        }
    }
    // Make a second call to GetIfTable to get the actual
    // data we want.
    if ((dwRetVal = GetIfTable(pIfTable, &dwSize, FALSE)) != NO_ERROR) {
        PyErr_SetString(PyExc_RuntimeError, "GetIfTable() failed");
        goto error;
    }

    for (i = 0; i < (int) pIfTable->dwNumEntries; i++) {
        pIfRow = (MIB_IFROW *) & pIfTable->table[i];

        // GetIfTable is not able to give us NIC with "friendly names"
        // so we determine them via GetAdapterAddresses() which
        // provides friendly names *and* descriptions and find the
        // ones that match.
        ifname_found = 0;
        pCurrAddresses = pAddresses;
        while (pCurrAddresses) {
            snprintf(descr, MAX_PATH, "%ls", pCurrAddresses->Description);
            if (lstrcmp(descr, pIfRow->bDescr) == 0) {
                py_nic_name = PyUnicode_FromWideChar(
                    pCurrAddresses->FriendlyName,
                    wcslen(pCurrAddresses->FriendlyName));
                if (py_nic_name == NULL)
                    goto error;
                ifname_found = 1;
                break;
            }
            pCurrAddresses = pCurrAddresses->Next;
        }
        if (ifname_found == 0) {
            // Name not found means GetAdapterAddresses() doesn't list
            // this NIC, only GetIfTable, meaning it's not really a NIC
            // interface so we skip it.
            continue;
        }

        // is up?
        if((pIfRow->dwOperStatus == MIB_IF_OPER_STATUS_CONNECTED ||
                pIfRow->dwOperStatus == MIB_IF_OPER_STATUS_OPERATIONAL) &&
                pIfRow->dwAdminStatus == 1 ) {
            py_is_up = Py_True;
        }
        else {
            py_is_up = Py_False;
        }
        Py_INCREF(py_is_up);

        py_ifc_info = Py_BuildValue(
            "(Oikk)",
            py_is_up,
            2,  // there's no way to know duplex so let's assume 'full'
            pIfRow->dwSpeed / 1000000,  // expressed in bytes, we want Mb
            pIfRow->dwMtu
        );
        if (!py_ifc_info)
            goto error;
        if (PyDict_SetItem(py_retdict, py_nic_name, py_ifc_info))
            goto error;
        Py_DECREF(py_nic_name);
        Py_DECREF(py_ifc_info);
    }

    free(pIfTable);
    free(pAddresses);
    return py_retdict;

error:
    Py_XDECREF(py_is_up);
    Py_XDECREF(py_ifc_info);
    Py_XDECREF(py_nic_name);
    Py_DECREF(py_retdict);
    if (pIfTable != NULL)
        free(pIfTable);
    if (pAddresses != NULL)
        free(pAddresses);
    return NULL;
}


/*
 * Return a Python list of named tuples with overall network I/O information
 */
static PyObject *
psutil_net_io_counters(PyObject *self, PyObject *args) {
    DWORD dwRetVal = 0;

#if (_WIN32_WINNT >= 0x0600) // Windows Vista and above
    MIB_IF_ROW2 *pIfRow = NULL;
#else // Windows XP
    MIB_IFROW *pIfRow = NULL;
#endif

    PIP_ADAPTER_ADDRESSES pAddresses = NULL;
    PIP_ADAPTER_ADDRESSES pCurrAddresses = NULL;
    PyObject *py_retdict = PyDict_New();
    PyObject *py_nic_info = NULL;
    PyObject *py_nic_name = NULL;

    if (py_retdict == NULL)
        return NULL;
    pAddresses = psutil_get_nic_addresses(0);
    if (pAddresses == NULL)
        goto error;
    pCurrAddresses = pAddresses;

    while (pCurrAddresses) {
        py_nic_name = NULL;
        py_nic_info = NULL;

#if (_WIN32_WINNT >= 0x0600) // Windows Vista and above
        pIfRow = (MIB_IF_ROW2 *) malloc(sizeof(MIB_IF_ROW2));
#else // Windows XP
        pIfRow = (MIB_IFROW *) malloc(sizeof(MIB_IFROW));
#endif

        if (pIfRow == NULL) {
            PyErr_NoMemory();
            goto error;
        }

#if (_WIN32_WINNT >= 0x0600) // Windows Vista and above
        SecureZeroMemory((PVOID)pIfRow, sizeof(MIB_IF_ROW2));
        pIfRow->InterfaceIndex = pCurrAddresses->IfIndex;
        dwRetVal = GetIfEntry2(pIfRow);
#else // Windows XP
        pIfRow->dwIndex = pCurrAddresses->IfIndex;
        dwRetVal = GetIfEntry(pIfRow);
#endif

        if (dwRetVal != NO_ERROR) {
            PyErr_SetString(PyExc_RuntimeError,
                            "GetIfEntry() or GetIfEntry2() failed.");
            goto error;
        }

#if (_WIN32_WINNT >= 0x0600) // Windows Vista and above
        py_nic_info = Py_BuildValue("(KKKKKKKK)",
                                    pIfRow->OutOctets,
                                    pIfRow->InOctets,
                                    pIfRow->OutUcastPkts,
                                    pIfRow->InUcastPkts,
                                    pIfRow->InErrors,
                                    pIfRow->OutErrors,
                                    pIfRow->InDiscards,
                                    pIfRow->OutDiscards);
#else // Windows XP
        py_nic_info = Py_BuildValue("(kkkkkkkk)",
                                    pIfRow->dwOutOctets,
                                    pIfRow->dwInOctets,
                                    pIfRow->dwOutUcastPkts,
                                    pIfRow->dwInUcastPkts,
                                    pIfRow->dwInErrors,
                                    pIfRow->dwOutErrors,
                                    pIfRow->dwInDiscards,
                                    pIfRow->dwOutDiscards);
#endif

        if (!py_nic_info)
            goto error;

        py_nic_name = PyUnicode_FromWideChar(
            pCurrAddresses->FriendlyName,
            wcslen(pCurrAddresses->FriendlyName));

        if (py_nic_name == NULL)
            goto error;
        if (PyDict_SetItem(py_retdict, py_nic_name, py_nic_info))
            goto error;
        Py_XDECREF(py_nic_name);
        Py_XDECREF(py_nic_info);

        free(pIfRow);
        pCurrAddresses = pCurrAddresses->Next;
    }

    free(pAddresses);
    return py_retdict;

error:
    Py_XDECREF(py_nic_name);
    Py_XDECREF(py_nic_info);
    Py_DECREF(py_retdict);
    if (pAddresses != NULL)
        free(pAddresses);
    if (pIfRow != NULL)
        free(pIfRow);
    return NULL;
}


// TODO: Copied verbatim from the windows module, so again the usual admonition
// about refactoring
/*
 * Return a Python dict of tuples for disk I/O information
 */
static PyObject *
psutil_disk_io_counters(PyObject *self, PyObject *args) {
    DISK_PERFORMANCE_WIN_2008 diskPerformance;
    DWORD dwSize;
    HANDLE hDevice = NULL;
    char szDevice[MAX_PATH];
    char szDeviceDisplay[MAX_PATH];
    int devNum;
    PyObject *py_retdict = PyDict_New();
    PyObject *py_tuple = NULL;

    if (py_retdict == NULL)
        return NULL;
    // Apparently there's no way to figure out how many times we have
    // to iterate in order to find valid drives.
    // Let's assume 32, which is higher than 26, the number of letters
    // in the alphabet (from A:\ to Z:\).
    for (devNum = 0; devNum <= 32; ++devNum) {
        py_tuple = NULL;
        snprintf(szDevice, MAX_PATH, "\\\\.\\PhysicalDrive%d", devNum);
        hDevice = CreateFile(szDevice, 0, FILE_SHARE_READ | FILE_SHARE_WRITE,
                             NULL, OPEN_EXISTING, 0, NULL);

        if (hDevice == INVALID_HANDLE_VALUE)
            continue;
        if (DeviceIoControl(hDevice, IOCTL_DISK_PERFORMANCE, NULL, 0,
                            &diskPerformance, sizeof(diskPerformance),
                            &dwSize, NULL))
        {
            snprintf(szDeviceDisplay, MAX_PATH, "PhysicalDrive%d", devNum);
            py_tuple = Py_BuildValue(
                "(IILLKK)",
                diskPerformance.ReadCount,
                diskPerformance.WriteCount,
                diskPerformance.BytesRead,
                diskPerformance.BytesWritten,
                (unsigned long long)(diskPerformance.ReadTime.QuadPart * 10) / 1000,
                (unsigned long long)(diskPerformance.WriteTime.QuadPart * 10) / 1000);
            if (!py_tuple)
                goto error;
            if (PyDict_SetItemString(py_retdict, szDeviceDisplay,
                                     py_tuple))
            {
                goto error;
            }
            Py_XDECREF(py_tuple);
        }
        else {
            // XXX we might get here with ERROR_INSUFFICIENT_BUFFER when
            // compiling with mingw32; not sure what to do.
            // return PyErr_SetFromWindowsErr(0);
            ;;
        }

        CloseHandle(hDevice);
    }

    return py_retdict;

error:
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retdict);
    if (hDevice != NULL)
        CloseHandle(hDevice);
    return NULL;
}


// TODO: _GetExtended(Tcp|Udp)Table are copied straight out of the windows
// module, and really ought to live somewhere in arch/windows


typedef DWORD (WINAPI * _GetExtendedTcpTable)(PVOID, PDWORD, BOOL, ULONG,
                                              TCP_TABLE_CLASS, ULONG);


// https://msdn.microsoft.com/library/aa365928.aspx
static DWORD __GetExtendedTcpTable(_GetExtendedTcpTable call,
                                   ULONG address_family,
                                   PVOID * data, DWORD * size)
{
    // Due to other processes being active on the machine, it's possible
    // that the size of the table increases between the moment where we
    // query the size and the moment where we query the data.  Therefore, it's
    // important to call this in a loop to retry if that happens.
    //
    // Also, since we may loop a theoretically unbounded number of times here,
    // release the GIL while we're doing this.
    DWORD error = ERROR_INSUFFICIENT_BUFFER;
    *size = 0;
    *data = NULL;
    Py_BEGIN_ALLOW_THREADS;
    error = call(NULL, size, FALSE, address_family,
                 TCP_TABLE_OWNER_PID_ALL, 0);
    while (error == ERROR_INSUFFICIENT_BUFFER)
    {
        *data = malloc(*size);
        if (*data == NULL) {
            error = ERROR_NOT_ENOUGH_MEMORY;
            continue;
        }
        error = call(*data, size, FALSE, address_family,
                     TCP_TABLE_OWNER_PID_ALL, 0);
        if (error != NO_ERROR) {
            free(*data);
            *data = NULL;
        }
    }
    Py_END_ALLOW_THREADS;
    return error;
}


typedef DWORD (WINAPI * _GetExtendedUdpTable)(PVOID, PDWORD, BOOL, ULONG,
                                              UDP_TABLE_CLASS, ULONG);


// https://msdn.microsoft.com/library/aa365930.aspx
static DWORD __GetExtendedUdpTable(_GetExtendedUdpTable call,
                                   ULONG address_family,
                                   PVOID * data, DWORD * size)
{
    // Due to other processes being active on the machine, it's possible
    // that the size of the table increases between the moment where we
    // query the size and the moment where we query the data.  Therefore, it's
    // important to call this in a loop to retry if that happens.
    //
    // Also, since we may loop a theoretically unbounded number of times here,
    // release the GIL while we're doing this.
    DWORD error = ERROR_INSUFFICIENT_BUFFER;
    *size = 0;
    *data = NULL;
    Py_BEGIN_ALLOW_THREADS;
    error = call(NULL, size, FALSE, address_family,
                 UDP_TABLE_OWNER_PID, 0);
    while (error == ERROR_INSUFFICIENT_BUFFER)
    {
        *data = malloc(*size);
        if (*data == NULL) {
            error = ERROR_NOT_ENOUGH_MEMORY;
            continue;
        }
        error = call(*data, size, FALSE, address_family,
                     UDP_TABLE_OWNER_PID, 0);
        if (error != NO_ERROR) {
            free(*data);
            *data = NULL;
        }
    }
    Py_END_ALLOW_THREADS;
    return error;
}


/*
 * Return a list of network connections opened by a process
 */
static PyObject *
psutil_net_connections(PyObject *self, PyObject *args) {
    static long null_address[4] = { 0, 0, 0, 0 };
    unsigned long pid;
    typedef PSTR (NTAPI * _RtlIpv4AddressToStringA)(struct in_addr *, PSTR);
    _RtlIpv4AddressToStringA rtlIpv4AddressToStringA;
    typedef PSTR (NTAPI * _RtlIpv6AddressToStringA)(struct in6_addr *, PSTR);
    _RtlIpv6AddressToStringA rtlIpv6AddressToStringA;
    _GetExtendedTcpTable getExtendedTcpTable;
    _GetExtendedUdpTable getExtendedUdpTable;
    PVOID table = NULL;
    DWORD tableSize;
    DWORD error;
    PMIB_TCPTABLE_OWNER_PID tcp4Table;
    PMIB_UDPTABLE_OWNER_PID udp4Table;
    PMIB_TCP6TABLE_OWNER_PID tcp6Table;
    PMIB_UDP6TABLE_OWNER_PID udp6Table;
    ULONG i;
    CHAR addressBufferLocal[65];
    CHAR addressBufferRemote[65];

    PyObject *py_retlist;
    PyObject *py_conn_tuple = NULL;
    PyObject *py_af_filter = NULL;
    PyObject *py_type_filter = NULL;
    PyObject *py_addr_tuple_local = NULL;
    PyObject *py_addr_tuple_remote = NULL;
    PyObject *_AF_INET = PyLong_FromLong((long)AF_INET);
    PyObject *_AF_INET6 = PyLong_FromLong((long)AF_INET6);
    PyObject *_SOCK_STREAM = PyLong_FromLong((long)SOCK_STREAM);
    PyObject *_SOCK_DGRAM = PyLong_FromLong((long)SOCK_DGRAM);

    if (! PyArg_ParseTuple(args, "lOO", &pid, &py_af_filter, &py_type_filter))
    {
        _psutil_conn_decref_objs();
        return NULL;
    }

    if (!PySequence_Check(py_af_filter) || !PySequence_Check(py_type_filter)) {
        _psutil_conn_decref_objs();
        PyErr_SetString(PyExc_TypeError, "arg 2 or 3 is not a sequence");
        return NULL;
    }

    if (pid != -1) {
        if (psutil_pid_is_running(pid) == 0) {
            _psutil_conn_decref_objs();
            return NoSuchProcess();
        }
    }

    // Import some functions.
    {
        HMODULE ntdll;
        HMODULE iphlpapi;

        ntdll = LoadLibrary(TEXT("ntdll.dll"));
        rtlIpv4AddressToStringA = (_RtlIpv4AddressToStringA)GetProcAddress(
                                   ntdll, "RtlIpv4AddressToStringA");
        rtlIpv6AddressToStringA = (_RtlIpv6AddressToStringA)GetProcAddress(
                                   ntdll, "RtlIpv6AddressToStringA");
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
        _psutil_conn_decref_objs();
        return NULL;
    }

    py_retlist = PyList_New(0);
    if (py_retlist == NULL) {
        _psutil_conn_decref_objs();
        return NULL;
    }

    // TCP IPv4

    if ((PySequence_Contains(py_af_filter, _AF_INET) == 1) &&
            (PySequence_Contains(py_type_filter, _SOCK_STREAM) == 1))
    {
        table = NULL;
        py_conn_tuple = NULL;
        py_addr_tuple_local = NULL;
        py_addr_tuple_remote = NULL;
        tableSize = 0;

        error = __GetExtendedTcpTable(getExtendedTcpTable,
                                      AF_INET, &table, &tableSize);
        if (error == ERROR_NOT_ENOUGH_MEMORY) {
            PyErr_NoMemory();
            goto error;
        }

        if (error == NO_ERROR)
        {
            tcp4Table = table;

            for (i = 0; i < tcp4Table->dwNumEntries; i++)
            {
                if (pid != -1) {
                    if (tcp4Table->table[i].dwOwningPid != pid) {
                        continue;
                    }
                }

                if (tcp4Table->table[i].dwLocalAddr != 0 ||
                        tcp4Table->table[i].dwLocalPort != 0)
                {
                    struct in_addr addr;

                    addr.S_un.S_addr = tcp4Table->table[i].dwLocalAddr;
                    rtlIpv4AddressToStringA(&addr, addressBufferLocal);
                    py_addr_tuple_local = Py_BuildValue(
                        "(si)",
                        addressBufferLocal,
                        BYTESWAP_USHORT(tcp4Table->table[i].dwLocalPort));
                }
                else {
                    py_addr_tuple_local = PyTuple_New(0);
                }

                if (py_addr_tuple_local == NULL)
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
                    py_addr_tuple_remote = Py_BuildValue(
                        "(si)",
                        addressBufferRemote,
                        BYTESWAP_USHORT(tcp4Table->table[i].dwRemotePort));
                }
                else
                {
                    py_addr_tuple_remote = PyTuple_New(0);
                }

                if (py_addr_tuple_remote == NULL)
                    goto error;

                py_conn_tuple = Py_BuildValue(
                    "(iiiNNiI)",
                    -1,
                    AF_INET,
                    SOCK_STREAM,
                    py_addr_tuple_local,
                    py_addr_tuple_remote,
                    tcp4Table->table[i].dwState,
                    tcp4Table->table[i].dwOwningPid);
                if (!py_conn_tuple)
                    goto error;
                if (PyList_Append(py_retlist, py_conn_tuple))
                    goto error;
                Py_DECREF(py_conn_tuple);
            }
        }
        else {
            PyErr_SetFromWindowsErr(error);
            goto error;
        }

        free(table);
        table = NULL;
        tableSize = 0;
    }

    // TCP IPv6
    if ((PySequence_Contains(py_af_filter, _AF_INET6) == 1) &&
            (PySequence_Contains(py_type_filter, _SOCK_STREAM) == 1))
    {
        table = NULL;
        py_conn_tuple = NULL;
        py_addr_tuple_local = NULL;
        py_addr_tuple_remote = NULL;
        tableSize = 0;

        error = __GetExtendedTcpTable(getExtendedTcpTable,
                                      AF_INET6, &table, &tableSize);
        if (error == ERROR_NOT_ENOUGH_MEMORY) {
            PyErr_NoMemory();
            goto error;
        }

        if (error == NO_ERROR)
        {
            tcp6Table = table;

            for (i = 0; i < tcp6Table->dwNumEntries; i++)
            {
                if (pid != -1) {
                    if (tcp6Table->table[i].dwOwningPid != pid) {
                        continue;
                    }
                }

                if (memcmp(tcp6Table->table[i].ucLocalAddr, null_address, 16)
                        != 0 || tcp6Table->table[i].dwLocalPort != 0)
                {
                    struct in6_addr addr;

                    memcpy(&addr, tcp6Table->table[i].ucLocalAddr, 16);
                    rtlIpv6AddressToStringA(&addr, addressBufferLocal);
                    py_addr_tuple_local = Py_BuildValue(
                        "(si)",
                        addressBufferLocal,
                        BYTESWAP_USHORT(tcp6Table->table[i].dwLocalPort));
                }
                else {
                    py_addr_tuple_local = PyTuple_New(0);
                }

                if (py_addr_tuple_local == NULL)
                    goto error;

                // On Windows <= XP, remote addr is filled even if socket
                // is in LISTEN mode in which case we just ignore it.
                if ((memcmp(tcp6Table->table[i].ucRemoteAddr, null_address, 16)
                        != 0 ||
                        tcp6Table->table[i].dwRemotePort != 0) &&
                        (tcp6Table->table[i].dwState != MIB_TCP_STATE_LISTEN))
                {
                    struct in6_addr addr;

                    memcpy(&addr, tcp6Table->table[i].ucRemoteAddr, 16);
                    rtlIpv6AddressToStringA(&addr, addressBufferRemote);
                    py_addr_tuple_remote = Py_BuildValue(
                        "(si)",
                        addressBufferRemote,
                        BYTESWAP_USHORT(tcp6Table->table[i].dwRemotePort));
                }
                else {
                    py_addr_tuple_remote = PyTuple_New(0);
                }

                if (py_addr_tuple_remote == NULL)
                    goto error;

                py_conn_tuple = Py_BuildValue(
                    "(iiiNNiI)",
                    -1,
                    AF_INET6,
                    SOCK_STREAM,
                    py_addr_tuple_local,
                    py_addr_tuple_remote,
                    tcp6Table->table[i].dwState,
                    tcp6Table->table[i].dwOwningPid);
                if (!py_conn_tuple)
                    goto error;
                if (PyList_Append(py_retlist, py_conn_tuple))
                    goto error;
                Py_DECREF(py_conn_tuple);
            }
        }
        else {
            PyErr_SetFromWindowsErr(error);
            goto error;
        }

        free(table);
        table = NULL;
        tableSize = 0;
    }

    // UDP IPv4

    if ((PySequence_Contains(py_af_filter, _AF_INET) == 1) &&
            (PySequence_Contains(py_type_filter, _SOCK_DGRAM) == 1))
    {
        table = NULL;
        py_conn_tuple = NULL;
        py_addr_tuple_local = NULL;
        py_addr_tuple_remote = NULL;
        tableSize = 0;
        error = __GetExtendedUdpTable(getExtendedUdpTable,
                                      AF_INET, &table, &tableSize);
        if (error == ERROR_NOT_ENOUGH_MEMORY) {
            PyErr_NoMemory();
            goto error;
        }

        if (error == NO_ERROR)
        {
            udp4Table = table;

            for (i = 0; i < udp4Table->dwNumEntries; i++)
            {
                if (pid != -1) {
                    if (udp4Table->table[i].dwOwningPid != pid) {
                        continue;
                    }
                }

                if (udp4Table->table[i].dwLocalAddr != 0 ||
                    udp4Table->table[i].dwLocalPort != 0)
                {
                    struct in_addr addr;

                    addr.S_un.S_addr = udp4Table->table[i].dwLocalAddr;
                    rtlIpv4AddressToStringA(&addr, addressBufferLocal);
                    py_addr_tuple_local = Py_BuildValue(
                        "(si)",
                        addressBufferLocal,
                        BYTESWAP_USHORT(udp4Table->table[i].dwLocalPort));
                }
                else {
                    py_addr_tuple_local = PyTuple_New(0);
                }

                if (py_addr_tuple_local == NULL)
                    goto error;

                py_conn_tuple = Py_BuildValue(
                    "(iiiNNiI)",
                    -1,
                    AF_INET,
                    SOCK_DGRAM,
                    py_addr_tuple_local,
                    PyTuple_New(0),
                    PSUTIL_CONN_NONE,
                    udp4Table->table[i].dwOwningPid);
                if (!py_conn_tuple)
                    goto error;
                if (PyList_Append(py_retlist, py_conn_tuple))
                    goto error;
                Py_DECREF(py_conn_tuple);
            }
        }
        else {
            PyErr_SetFromWindowsErr(error);
            goto error;
        }

        free(table);
        table = NULL;
        tableSize = 0;
    }

    // UDP IPv6

    if ((PySequence_Contains(py_af_filter, _AF_INET6) == 1) &&
            (PySequence_Contains(py_type_filter, _SOCK_DGRAM) == 1))
    {
        table = NULL;
        py_conn_tuple = NULL;
        py_addr_tuple_local = NULL;
        py_addr_tuple_remote = NULL;
        tableSize = 0;
        error = __GetExtendedUdpTable(getExtendedUdpTable,
                                      AF_INET6, &table, &tableSize);
        if (error == ERROR_NOT_ENOUGH_MEMORY) {
            PyErr_NoMemory();
            goto error;
        }

        if (error == NO_ERROR)
        {
            udp6Table = table;

            for (i = 0; i < udp6Table->dwNumEntries; i++) {
                if (pid != -1) {
                    if (udp6Table->table[i].dwOwningPid != pid) {
                        continue;
                    }
                }

                if (memcmp(udp6Table->table[i].ucLocalAddr, null_address, 16)
                        != 0 || udp6Table->table[i].dwLocalPort != 0)
                {
                    struct in6_addr addr;

                    memcpy(&addr, udp6Table->table[i].ucLocalAddr, 16);
                    rtlIpv6AddressToStringA(&addr, addressBufferLocal);
                    py_addr_tuple_local = Py_BuildValue(
                        "(si)",
                        addressBufferLocal,
                        BYTESWAP_USHORT(udp6Table->table[i].dwLocalPort));
                }
                else {
                    py_addr_tuple_local = PyTuple_New(0);
                }

                if (py_addr_tuple_local == NULL)
                    goto error;

                py_conn_tuple = Py_BuildValue(
                    "(iiiNNiI)",
                    -1,
                    AF_INET6,
                    SOCK_DGRAM,
                    py_addr_tuple_local,
                    PyTuple_New(0),
                    PSUTIL_CONN_NONE,
                    udp6Table->table[i].dwOwningPid);
                if (!py_conn_tuple)
                    goto error;
                if (PyList_Append(py_retlist, py_conn_tuple))
                    goto error;
                Py_DECREF(py_conn_tuple);
            }
        }
        else {
            PyErr_SetFromWindowsErr(error);
            goto error;
        }

        free(table);
        table = NULL;
        tableSize = 0;
    }

    _psutil_conn_decref_objs();
    return py_retlist;

error:
    _psutil_conn_decref_objs();
    Py_XDECREF(py_conn_tuple);
    Py_XDECREF(py_addr_tuple_local);
    Py_XDECREF(py_addr_tuple_remote);
    Py_DECREF(py_retlist);
    if (table != NULL)
        free(table);
    return NULL;
}


static char *get_region_protection_string(ULONG protection) {
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


/* TODO: Copied verbatim from the windows module; this should be refactored
 * as well
 */
/*
 * Return a list of process's memory mappings.
 */
static PyObject *
psutil_proc_memory_maps(PyObject *self, PyObject *args) {
#ifdef _WIN64
    MEMORY_BASIC_INFORMATION64 basicInfo;
#else
    MEMORY_BASIC_INFORMATION basicInfo;
#endif
    DWORD pid;
    HANDLE hProcess = NULL;
    PVOID baseAddress;
    PVOID previousAllocationBase;
    CHAR mappedFileName[MAX_PATH];
    SYSTEM_INFO system_info;
    LPVOID maxAddr;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;

    if (py_retlist == NULL)
        return NULL;
    if (! PyArg_ParseTuple(args, "l", &pid))
        goto error;
    hProcess = psutil_handle_from_pid(pid);
    if (NULL == hProcess)
        goto error;

    GetSystemInfo(&system_info);
    maxAddr = system_info.lpMaximumApplicationAddress;
    baseAddress = NULL;
    previousAllocationBase = NULL;

    while (VirtualQueryEx(hProcess, baseAddress, &basicInfo,
                          sizeof(MEMORY_BASIC_INFORMATION)))
    {
        py_tuple = NULL;
        if (baseAddress > maxAddr)
            break;
        if (GetMappedFileNameA(hProcess, baseAddress, mappedFileName,
                               sizeof(mappedFileName)))
        {
#ifdef _WIN64
           py_tuple = Py_BuildValue(
              "(KssI)",
              (unsigned long long)baseAddress,
#else
           py_tuple = Py_BuildValue(
              "(kssI)",
              (unsigned long)baseAddress,
#endif
              get_region_protection_string(basicInfo.Protect),
              mappedFileName,
              basicInfo.RegionSize);

            if (!py_tuple)
                goto error;
            if (PyList_Append(py_retlist, py_tuple))
                goto error;
            Py_DECREF(py_tuple);
        }
        previousAllocationBase = basicInfo.AllocationBase;
        baseAddress = (PCHAR)baseAddress + basicInfo.RegionSize;
    }

    CloseHandle(hProcess);
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    if (hProcess != NULL)
        CloseHandle(hProcess);
    return NULL;
}


/*
 * Return battery usage stats.
 */
static PyObject *
psutil_sensors_battery(PyObject *self, PyObject *args) {
    SYSTEM_POWER_STATUS sps;

    if (GetSystemPowerStatus(&sps) == 0) {
        PyErr_SetFromWindowsErr(0);
        return NULL;
    }
    return Py_BuildValue(
        "iiiI",
        sps.ACLineStatus,  // whether AC is connected: 0=no, 1=yes, 255=unknown
        // status flag:
        // 1, 2, 4 = high, low, critical
        // 8 = charging
        // 128 = no battery
        sps.BatteryFlag,
        sps.BatteryLifePercent,  // percent
        sps.BatteryLifeTime  // remaining secs
    );
}


/*
 * define the psutil C module methods and initialize the module.
 */
static PyMethodDef
PsutilMethods[] = {
    {"cygpath_to_winpath", psutil_cygpath_to_winpath, METH_VARARGS,
     "Convert a Cygwin path to a Windows path"},
    {"winpath_to_cygpath", psutil_winpath_to_cygpath, METH_VARARGS,
     "Convert a Windows path to a Cygwin path"},
    {"cygpid_to_winpid", psutil_cygpid_to_winpid, METH_VARARGS,
     "Converts Cygwin's internal PID (the one exposed by all POSIX interfaces) "
     "to the associated Windows PID."},
    {"winpid_to_cygpid", psutil_winpid_to_cygpid, METH_VARARGS,
     "Converts a Windows PID to its associated Cygwin PID."},
    {"boot_time", psutil_boot_time, METH_VARARGS,
     "Return the system boot time expressed in seconds since the epoch."},
    {"disk_partitions", psutil_disk_partitions, METH_VARARGS,
     "Return disk mounted partitions as a list of tuples including "
     "device, mount point and filesystem type"},
    {"net_connections", psutil_net_connections, METH_VARARGS,
     "Return system-wide connections"},
    {"net_if_stats", psutil_net_if_stats, METH_VARARGS,
     "Return NICs stats."},
    {"net_io_counters", psutil_net_io_counters, METH_VARARGS,
     "Return dict of tuples of networks I/O information."},
    {"sensors_battery", psutil_sensors_battery, METH_VARARGS,
     "Return battery metrics usage."},
    {"disk_io_counters", psutil_disk_io_counters, METH_VARARGS,
     "Return dict of tuples of disks I/O information."},
    {"proc_memory_info", psutil_proc_memory_info, METH_VARARGS,
     "Return a tuple of process memory information"},
    {"proc_memory_info_2", psutil_proc_memory_info_2, METH_VARARGS,
     "Alternate implementation"},
    {"proc_memory_uss", psutil_proc_memory_uss, METH_VARARGS,
     "Return the USS of the process"},
    {"proc_cpu_affinity_get", psutil_proc_cpu_affinity_get, METH_VARARGS,
     "Return process CPU affinity as a bitmask."},
    {"proc_cpu_affinity_set", psutil_proc_cpu_affinity_set, METH_VARARGS,
     "Set process CPU affinity."},
    {"proc_io_counters", psutil_proc_io_counters, METH_VARARGS,
     "Get process I/O counters."},
    {"proc_threads", psutil_proc_threads, METH_VARARGS,
     "Return process threads information as a list of tuple"},
    {"proc_create_time", psutil_proc_create_time, METH_VARARGS,
     "Return a float indicating the process create time expressed in "
     "seconds since the epoch"},
    // --- alternative pinfo interface
    {"proc_info", psutil_proc_info, METH_VARARGS,
     "Various process information"},
    {"users", psutil_users, METH_VARARGS,
     "Return currently connected users as a list of tuples"},
    {"proc_memory_maps", psutil_proc_memory_maps, METH_VARARGS,
     "Return a list of process's memory mappings"},

    // --- windows API bindings
    {"win32_QueryDosDevice", psutil_win32_QueryDosDevice, METH_VARARGS,
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
#endif

#if PY_MAJOR_VERSION >= 3

static int
psutil_cygwin_traverse(PyObject *m, visitproc visit, void *arg) {
    Py_VISIT(GETSTATE(m)->error);
    return 0;
}

static int
psutil_cygwin_clear(PyObject *m) {
    Py_CLEAR(GETSTATE(m)->error);
    return 0;
}

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "psutil_cygwin",
    NULL,
    sizeof(struct module_state),
    PsutilMethods,
    NULL,
    psutil_cygwin_traverse,
    psutil_cygwin_clear,
    NULL
};

#define INITERROR return NULL

PyMODINIT_FUNC PyInit__psutil_cygwin(void)

#else
#define INITERROR return

void init_psutil_cygwin(void)
#endif
{
#if PY_MAJOR_VERSION >= 3
    PyObject *module = PyModule_Create(&moduledef);
#else
    PyObject *module = Py_InitModule("_psutil_cygwin", PsutilMethods);
#endif

    PyModule_AddIntConstant(module, "version", PSUTIL_VERSION);

    // TODO: Copied verbatim from the Windows module; there ought to be a
    // a function implementing these constants that can be shared between
    // the two modules...
    // connection status constants
    // http://msdn.microsoft.com/en-us/library/cc669305.aspx
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_CLOSED", MIB_TCP_STATE_CLOSED);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_CLOSING", MIB_TCP_STATE_CLOSING);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_CLOSE_WAIT", MIB_TCP_STATE_CLOSE_WAIT);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_LISTEN", MIB_TCP_STATE_LISTEN);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_ESTAB", MIB_TCP_STATE_ESTAB);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_SYN_SENT", MIB_TCP_STATE_SYN_SENT);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_SYN_RCVD", MIB_TCP_STATE_SYN_RCVD);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_FIN_WAIT1", MIB_TCP_STATE_FIN_WAIT1);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_FIN_WAIT2", MIB_TCP_STATE_FIN_WAIT2);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_LAST_ACK", MIB_TCP_STATE_LAST_ACK);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_TIME_WAIT", MIB_TCP_STATE_TIME_WAIT);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_TIME_WAIT", MIB_TCP_STATE_TIME_WAIT);
    PyModule_AddIntConstant(
        module, "MIB_TCP_STATE_DELETE_TCB", MIB_TCP_STATE_DELETE_TCB);
    PyModule_AddIntConstant(
        module, "PSUTIL_CONN_NONE", PSUTIL_CONN_NONE);

    /* TODO: More Windows constants that are defined as module constants
     * Used both in the cygwin module (for now) and the windows module */
    PyModule_AddIntConstant(
        module, "ERROR_ACCESS_DENIED", ERROR_ACCESS_DENIED);

    if (module == NULL)
        INITERROR;
#if PY_MAJOR_VERSION >= 3
    return module;
#endif
}
