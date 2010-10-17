/*
 * $Id$
 *
 * Windows platform-specific module methods for _psutil_mswindows
 */

#include <Python.h>
#include <windows.h>
#include <Psapi.h>
#include <time.h>
#include <lm.h>
#include <tchar.h>
#include <tlhelp32.h>
#include <iphlpapi.h>

#include "_psutil_mswindows.h"
#include "arch/mswindows/security.h"
#include "arch/mswindows/process_info.h"
#include "arch/mswindows/process_handles.h"

static PyMethodDef PsutilMethods[] =
{
     {"get_pid_list", get_pid_list, METH_VARARGS,
     	"Returns a list of PIDs currently running on the system"},
     {"get_process_info", get_process_info, METH_VARARGS,
        "Return a tuple containing a set of information about the "
        "process (pid, ppid, name, path, cmdline)"},
     {"kill_process", kill_process, METH_VARARGS,
         "Kill the process identified by the given PID"},
     {"pid_exists", pid_exists, METH_VARARGS,
         "Determine if the process exists in the current process list."},
     {"get_process_cpu_times", get_process_cpu_times, METH_VARARGS,
       	"Return tuple of user/kern time for the given PID"},
     {"get_process_create_time", get_process_create_time, METH_VARARGS,
         "Return a float indicating the process create time expressed in "
         "seconds since the epoch"},
     {"get_num_cpus", get_num_cpus, METH_VARARGS,
         "Returns the number of CPUs on the system"},
     {"get_system_uptime", get_system_uptime, METH_VARARGS,
         "Return system uptime"},
     {"get_memory_info", get_memory_info, METH_VARARGS,
         "Return a tuple of RSS/VMS memory information"},
     {"get_total_phymem", get_total_phymem, METH_VARARGS,
         "Return the total amount of physical memory, in bytes"},
     {"get_total_virtmem", get_total_virtmem, METH_VARARGS,
         "Return the total amount of virtual memory, in bytes"},
     {"get_avail_phymem", get_avail_phymem, METH_VARARGS,
         "Return the amount of available physical memory, in bytes"},
     {"get_avail_virtmem", get_avail_virtmem, METH_VARARGS,
         "Return the amount of available virtual memory, in bytes"},
     {"get_system_cpu_times", get_system_cpu_times, METH_VARARGS,
         "Return system cpu times as a tuple (user, system, idle)"},
    {"get_process_cwd", get_process_cwd, METH_VARARGS,
        "Return process current working directory"},
    {"suspend_process", suspend_process, METH_VARARGS,
        "Suspend a process"},
    {"resume_process", resume_process, METH_VARARGS,
        "Resume a process"},
    {"get_process_open_files", get_process_open_files, METH_VARARGS,
        "Return files opened by process"},
    {"_QueryDosDevice", _QueryDosDevice, METH_VARARGS,
        "QueryDosDevice binding"},
    {"get_process_username", get_process_username, METH_VARARGS,
        "Return the username of a process"},
    {"get_process_connections", get_process_connections, METH_VARARGS,
        "Return the network connections of a process"},
     {NULL, NULL, 0, NULL}
};

/*
 * Raises an OSError(errno=ESRCH, strerror="No such process") exception
 * in Python.
 */
static PyObject *
NoSuchProcess(void) {
    PyObject *exc;
    char *msg = strerror(ESRCH);
    exc = PyObject_CallFunction(PyExc_OSError, "(is)", ESRCH, msg);
    PyErr_SetObject(PyExc_OSError, exc);
    Py_XDECREF(exc);
    return NULL;
}

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
    struct module_state *st;
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

    SetSeDebug();

#if PY_MAJOR_VERSION >= 3
    return module;
#endif
}


/*
 * Return a Python float representing the system uptime expressed in seconds
 * since the epoch.
 */
static PyObject* get_system_uptime(PyObject* self, PyObject* args)
{
    float uptime;
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
static PyObject* pid_exists(PyObject* self, PyObject* args)
{
    long pid;
    int status;

	if (! PyArg_ParseTuple(args, "l", &pid)) {
        return PyErr_Format(PyExc_RuntimeError,
                            "Invalid argument - no PID provided.");
	}

    status = pid_is_running(pid);
    if (-1 == status) {
        return NULL; // exception raised in pid_is_running()
    }

    return PyBool_FromLong(status);
}


/*
 * Return a Python list of all the PIDs running on the system.
 */
static PyObject* get_pid_list(PyObject* self, PyObject* args)
{
    DWORD *proclist = NULL;
    DWORD numberOfReturnedPIDs;
    DWORD i;
    PyObject* pid = NULL;
	PyObject* retlist = PyList_New(0);

    proclist = get_pids(&numberOfReturnedPIDs);
    if (NULL == proclist) {
        Py_DECREF(retlist);
		PyErr_SetString(PyExc_RuntimeError, "get_pids() failed in get_pid_list()");
        return NULL;
    }

    for (i = 0; i < numberOfReturnedPIDs; i++) {
        pid = Py_BuildValue("i", proclist[i]);
        PyList_Append(retlist, pid);
        Py_XDECREF(pid);
    }

    // free C array allocated for PIDs
    free(proclist);

    return retlist;
}


/*
 * Kill a process given its PID.
 */
static PyObject* kill_process(PyObject* self, PyObject* args)
{
    HANDLE hProcess;
    long pid;
    int pid_return;
    PyObject* ret;
    ret = PyLong_FromLong(0);

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        PyErr_SetString(PyExc_RuntimeError, "Invalid argument");
        return NULL;
    }

    if (pid < 0) {
        return NULL;
    }

    pid_return = pid_is_running(pid);
    if (pid_return == 0) {
        return NoSuchProcess();
    }

    if (pid_return == -1) {
        return NULL; // exception raised from within pid_is_running()
    }

    // get a process handle
    hProcess = OpenProcess(PROCESS_TERMINATE, FALSE, pid);
    if (hProcess == NULL) {
        PyErr_SetFromWindowsErr(0);
        return NULL;
    }

    // kill the process
    if (! TerminateProcess(hProcess, 0) ){
        PyErr_SetFromWindowsErr(0);
        CloseHandle(hProcess);
        return NULL;
    }

    CloseHandle(hProcess);
    return PyLong_FromLong(1);
}


/*
 * Return a Python tuple (user_time, kernel_time)
 */
static PyObject* get_process_cpu_times(PyObject* self, PyObject* args)
{
    long        pid;
    HANDLE      hProcess;
    FILETIME    ftCreate, ftExit, ftKernel, ftUser;
    DWORD       ProcessExitCode = 0;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        PyErr_SetString(PyExc_RuntimeError, "Invalid argument");
        return NULL;
    }

    // special case for PID 0
    if (0 == pid){
	   return Py_BuildValue("(dd)", 0.0, 0.0);
    }

    hProcess = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid);
    if (hProcess == NULL){
        PyErr_SetFromWindowsErr(0);
        if (GetLastError() == ERROR_INVALID_PARAMETER) {
            // bad PID so no such process
            CloseHandle(hProcess);
            return NoSuchProcess();
        }
        return NULL;
    }

    /* make sure the process is running */
    GetExitCodeProcess(hProcess, &ProcessExitCode);
    if (ProcessExitCode == 0) {
        CloseHandle(hProcess);
        return NoSuchProcess();
    }

    if (! GetProcessTimes(hProcess, &ftCreate, &ftExit, &ftKernel, &ftUser)) {
        PyErr_SetFromWindowsErr(0);
        if (GetLastError() == ERROR_ACCESS_DENIED) {
            // usually means the process has died so we throw a NoSuchProcess
            // here
            CloseHandle(hProcess);
            return NoSuchProcess();
        }
        CloseHandle(hProcess);
        return NULL;
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
 * Return a Python float indicating the process create time expressed in
 * seconds since the epoch.
 */
static PyObject* get_process_create_time(PyObject* self, PyObject* args)
{
    long        pid;
    long long unix_time;
    HANDLE      hProcess;
    FILETIME    ftCreate, ftExit, ftKernel, ftUser;
    DWORD     ProcessExitCode = 0;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        PyErr_SetString(PyExc_RuntimeError, "Invalid argument");
        return NULL;
    }

    // special case for PIDs 0 and 4
    if ( (0 == pid) || (4 == pid) ){
	   return Py_BuildValue("d", 0.0);
    }

    hProcess = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid);
    if (hProcess == NULL){
        PyErr_SetFromWindowsErr(0);
        if (GetLastError() == ERROR_INVALID_PARAMETER) {
            // bad PID so no such process
            return NoSuchProcess();
        }
        return NULL;
    }

    /* make sure the process is running */
    GetExitCodeProcess(hProcess, &ProcessExitCode);
    if (ProcessExitCode == 0) {
        return NoSuchProcess();
    }

    if (! GetProcessTimes(hProcess, &ftCreate, &ftExit, &ftKernel, &ftUser)) {
        PyErr_SetFromWindowsErr(0);
        if (GetLastError() == ERROR_ACCESS_DENIED) {
            // usually means the process has died so we throw a NoSuchProcess here
            return NoSuchProcess();
        }
        CloseHandle(hProcess);
        return NULL;
    }

    CloseHandle(hProcess);

    /*
    Convert the FILETIME structure to a Unix time.
    It's the best I could find by googling and borrowing code here and there.
    The time returned has a precision of 1 second.
    */
    unix_time = ((LONGLONG)ftCreate.dwHighDateTime) << 32;
    unix_time += ftCreate.dwLowDateTime - 116444736000000000LL;
    unix_time /= 10000000;
    return Py_BuildValue("f", (float)unix_time);
}


/*
 * Return a Python integer indicating the number of CPUs on the system.
 */
static PyObject* get_num_cpus(PyObject* self, PyObject* args)
{
    SYSTEM_INFO system_info;
    system_info.dwNumberOfProcessors = 0;

    GetSystemInfo(&system_info);
    if (system_info.dwNumberOfProcessors == 0){
        // GetSystemInfo failed for some reason; return 1 as default
        return Py_BuildValue("i", 1);
    }
    return Py_BuildValue("i", system_info.dwNumberOfProcessors);
}


/*
 * Return a Python tuple containing a set of information about the process:
 * (pid, ppid, name, path, cmdline).
 */
static PyObject* get_process_info(PyObject* self, PyObject* args)
{
	// the argument passed should be a process id
	long pid;
    int pid_return;
    PyObject* infoTuple;
    PyObject* ppid;
    PyObject* arglist;
    PyObject* name;

	if (! PyArg_ParseTuple(args, "l", &pid)) {
        return PyErr_Format(PyExc_RuntimeError,
                       "get_process_info(): Invalid argument - no PID provided.");
	}

    // special case for PID 0 (System Idle Process)
    if (0 == pid) {
        arglist = Py_BuildValue("[]");
	    infoTuple = Py_BuildValue("llssNll", pid, 0, "System Idle Process", "",
                                  arglist, -1, -1);
        return infoTuple;
    }

    // special case for PID 4 (System)
    if (4 == pid) {
        arglist = Py_BuildValue("[]");
	    infoTuple = Py_BuildValue("llssNll", pid, 0, "System", "", arglist, -1, -1);
        return infoTuple;
    }

    // check if the process exists before we waste time trying to read info
    pid_return = pid_is_running(pid);
    if (pid_return == 0) {
        return NoSuchProcess();
    }

    if (pid_return == -1) {
        return NULL; // exception raised from within pid_is_running()
    }


    // Now fetch the actual properties of the process
    ppid = get_ppid(pid);
    if ( NULL == ppid ) {
        return NULL;  // exception string set in get_ppid()
    }

    name = get_name(pid);
    if ( NULL == name ) {
        return NULL;  //exception string set in get_name()
    }

    // If get_name or get_pid returns None that means the process is dead
    if (Py_None == name) {
        return NoSuchProcess();
    }

    if (Py_None == ppid) {
        return NoSuchProcess();
    }

    // May fail any of several ReadProcessMemory calls etc. and not indicate
    // a real problem so we ignore any errors and just live without commandline
    arglist = get_arg_list(pid);
    if ( NULL == arglist ) {
        // carry on anyway, clear any exceptions too
        PyErr_Clear();
        arglist = Py_BuildValue("[]");
    }

	infoTuple = Py_BuildValue("lNNsNll", pid, ppid, name, "", arglist, -1, -1);
    if (infoTuple == NULL) {
        PyErr_SetString(PyExc_RuntimeError, "error building info tuple");
    }
	return infoTuple;
}


/*
 * Return the RSS and VMS as a Python tuple.
 */
static PyObject* get_memory_info(PyObject* self, PyObject* args)
{
    HANDLE hProcess;
    PROCESS_MEMORY_COUNTERS counters;
    DWORD pid;
    DWORD ProcessExitCode = 0;

	if (! PyArg_ParseTuple(args, "l", &pid)) {
        return PyErr_Format(PyExc_RuntimeError,
                            "Invalid argument - no PID provided.");
	}

    hProcess = handle_from_pid(pid);
    if (NULL == hProcess) {
        if (GetLastError() == ERROR_INVALID_PARAMETER) {
            return NoSuchProcess();
        }
        return PyErr_SetFromWindowsErr(0);
    }

    /* make sure the process is running */
    GetExitCodeProcess(hProcess, &ProcessExitCode);
    if (ProcessExitCode == 0) {
        return NoSuchProcess();
    }

    if (! GetProcessMemoryInfo(hProcess, &counters, sizeof(counters)) ) {
        return PyErr_SetFromWindowsErr(0);
    }

    return Py_BuildValue("(ll)", counters.WorkingSetSize, counters.PagefileUsage);
}


/*
 * Return a Python integer indicating the total amount of physical memory
 * in bytes.
 */
static PyObject* get_total_phymem(PyObject* self, PyObject* args)
{
    MEMORYSTATUSEX memInfo;
    memInfo.dwLength = sizeof(MEMORYSTATUSEX);

    if (! GlobalMemoryStatusEx(&memInfo) ) {
        return PyErr_SetFromWindowsErr(0);
    }

    return Py_BuildValue("L", memInfo.ullTotalPhys);
}


/*
 * Return a Python integer indicating the total amount of virtual memory
 * in bytes.
 */
static PyObject* get_total_virtmem(PyObject* self, PyObject* args)
{
    MEMORYSTATUSEX memInfo;
    memInfo.dwLength = sizeof(MEMORYSTATUSEX);

    if (! GlobalMemoryStatusEx(&memInfo) ) {
        return PyErr_SetFromWindowsErr(0);
    }

    return Py_BuildValue("L", memInfo.ullTotalPageFile);
}


/*
 * Return a Python integer indicating the amount of available physical memory
 * in bytes.
 */
static PyObject* get_avail_phymem(PyObject* self, PyObject* args)
{
    MEMORYSTATUSEX memInfo;
    memInfo.dwLength = sizeof(MEMORYSTATUSEX);
    if (! GlobalMemoryStatusEx(&memInfo) ) {
        return PyErr_SetFromWindowsErr(0);
    }
    return Py_BuildValue("L", memInfo.ullAvailPhys);
}


/*
 * Return a Python integer indicating the amount of available virtual memory
 * in bytes.
 */
static PyObject* get_avail_virtmem(PyObject* self, PyObject* args)
{
    MEMORYSTATUSEX memInfo;
    memInfo.dwLength = sizeof(MEMORYSTATUSEX);

    if (! GlobalMemoryStatusEx(&memInfo) ) {
        return PyErr_SetFromWindowsErr(0);
    }
    return Py_BuildValue("L", memInfo.ullAvailPageFile);
}


#define LO_T ((float)1e-7)
#define HI_T (LO_T*4294967296.0)

// structures and enums from winternl.h (not available under mingw)
typedef struct _SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION {
    LARGE_INTEGER IdleTime;
    LARGE_INTEGER KernelTime;
    LARGE_INTEGER UserTime;
    LARGE_INTEGER Reserved1[2];
    ULONG Reserved2;
} SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION, *PSYSTEM_PROCESSOR_PERFORMANCE_INFORMATION;


typedef enum _SYSTEM_INFORMATION_CLASS {
    SystemBasicInformation = 0,
    SystemPerformanceInformation = 2,
    SystemTimeOfDayInformation = 3,
    SystemProcessInformation = 5,
    SystemProcessorPerformanceInformation = 8,
    SystemInterruptInformation = 23,
    SystemExceptionInformation = 33,
    SystemRegistryQuotaInformation = 37,
    SystemLookasideInformation = 45
} SYSTEM_INFORMATION_CLASS;


/*
 * Return a Python tuple representing user, kernel and idle CPU times
 */
static PyObject* get_system_cpu_times(PyObject* self, PyObject* args)
{
	typedef BOOL (_stdcall *GST_PROC) (LPFILETIME, LPFILETIME, LPFILETIME);
	static GST_PROC GetSystemTimes;
	static BOOL bFirstCall = TRUE;
	float idle, kernel, user;

	// Improves performance calling GetProcAddress only the first time
	if (bFirstCall)
	{
        // retrieves GetSystemTimes address in Kernel32
		GetSystemTimes=(GST_PROC)GetProcAddress(GetModuleHandle
                                               (TEXT("Kernel32.dll")),
                                               "GetSystemTimes");
		bFirstCall = FALSE;
	}


     // Uses GetSystemTimes if supported (winXP sp1+)
	if (NULL!=GetSystemTimes)
	{
		// GetSystemTimes supported

		FILETIME idle_time;
		FILETIME kernel_time;
		FILETIME user_time;

		if (!GetSystemTimes(&idle_time, &kernel_time, &user_time))
		{
			return PyErr_SetFromWindowsErr(0);
		}

		idle = (float)((HI_T * idle_time.dwHighDateTime) + \
                       (LO_T * idle_time.dwLowDateTime));
		user = (float)((HI_T * user_time.dwHighDateTime) + \
                       (LO_T * user_time.dwLowDateTime));
		kernel = (float)((HI_T * kernel_time.dwHighDateTime) + \
                         (LO_T * kernel_time.dwLowDateTime));

        // kernel time includes idle time on windows
        // we return only busy kernel time subtracting idle time from kernel time
		return Py_BuildValue("(ddd)", user,
                                      kernel - idle,
                                      idle);

	}
	else
	{
        // GetSystemTimes NOT supported, use NtQuerySystemInformation instead

		typedef DWORD (_stdcall *NTQSI_PROC) (int, PVOID, ULONG, PULONG);
		NTQSI_PROC NtQuerySystemInformation;
		HINSTANCE hNtDll;
		SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION *sppi = NULL;
		SYSTEM_INFO si;
		UINT i;

		// dynamic linking is mandatory to use NtQuerySystemInformation
		hNtDll = LoadLibrary(TEXT("ntdll.dll"));
		if (hNtDll != NULL)
		{
			// gets NtQuerySystemInformation address
			NtQuerySystemInformation = (NTQSI_PROC)GetProcAddress(
                                        hNtDll, "NtQuerySystemInformation");

			if (NtQuerySystemInformation != NULL)
			{
				// retrives number of processors
				GetSystemInfo(&si);

				// allocates an array of SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION
                // structures, one per processor
				sppi=(SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION *) \
    				  malloc(si.dwNumberOfProcessors * \
                             sizeof(SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION));
				if (sppi != NULL)
				{
					// gets cpu time informations
					if (0 == NtQuerySystemInformation(
								SystemProcessorPerformanceInformation,
								sppi,
								si.dwNumberOfProcessors * sizeof(SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION),
								NULL))
					{
						// computes system global times summing each processor value
						idle = user = kernel = 0;
						for (i=0; i<si.dwNumberOfProcessors; i++)
						{
							idle += (float)((HI_T * sppi[i].IdleTime.HighPart) + \
                                            (LO_T * sppi[i].IdleTime.LowPart));
							user += (float)((HI_T * sppi[i].UserTime.HighPart) + \
                                            (LO_T * sppi[i].UserTime.LowPart));
							kernel += (float)((HI_T * sppi[i].KernelTime.HighPart) + \
                                              (LO_T * sppi[i].KernelTime.LowPart));
						}

                        // kernel time includes idle time on windows
                        // we return only busy kernel time subtracting idle
                        // time from kernel time
						return Py_BuildValue("(fff)", user,
                                                      kernel - idle,
                                                      idle
                                             );

					} // END NtQuerySystemInformation

				} // END malloc SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION

			} // END GetProcAddress

		} // END LoadLibrary

		PyErr_SetFromWindowsErr(0);
		if (sppi)
            free(sppi);
		if (hNtDll)
            FreeLibrary(hNtDll);
		return 0;

	} // END GetSystemTimes NOT supported
}




/*
 * Sid to User convertion
 */
BOOL SidToUser(PSID pSid, LPTSTR szUser, DWORD dwUserLen, LPTSTR szDomain, DWORD
dwDomainLen, DWORD pid)
{
    SID_NAME_USE snuSIDNameUse;
    DWORD dwULen;
    DWORD dwDLen;

    dwULen = dwUserLen;
    dwDLen = dwDomainLen;

    if ( IsValidSid( pSid ) )
        {
            // Get user and domain name based on SID
            if ( LookupAccountSid( NULL, pSid, szUser, &dwULen, szDomain, &dwDLen, &snuSIDNameUse) )
                {
                    // LocalSystem processes are incorrectly reported as owned
                    // by BUILTIN\Administrators We modify that behavior to
                    // conform to standard taskmanager only if the process is
                    // actually a System process
                    if (is_system_proc(pid) == 1) {
                        // default to *not* changing the data if we fail to
                        // check for local system privileges, so only look for
                        // definite confirmed system processes and ignore errors
                        if ( lstrcmpi(szDomain, TEXT("builtin")) == 0 && lstrcmpi(szUser, TEXT("administrators")) == 0)
                            {
                                strncpy  (szUser, "SYSTEM", dwUserLen);
                                strncpy  (szDomain, "NT AUTHORITY", dwDomainLen);
                            }
                    }
                    return TRUE;
                }
        }

    return FALSE;
}

typedef struct _UNICODE_STRING {
    USHORT Length;
    USHORT MaximumLength;
    PWSTR Buffer;
} UNICODE_STRING, *PUNICODE_STRING;

/*
 * Return process current working directory as a Python string.
 */

static PyObject* get_process_cwd(PyObject* self, PyObject* args)
{
    long pid;
    HANDLE processHandle;
    PVOID pebAddress;
    PVOID rtlUserProcParamsAddress;
    UNICODE_STRING currentDirectory;
    WCHAR *currentDirectoryContent;
    DWORD ProcessExitCode = 0;
    PyObject *returnPyObj = NULL;
    PyObject *cwd_from_wchar = NULL;
    PyObject *cwd = NULL;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        PyErr_SetString(PyExc_RuntimeError, "Invalid argument");
        return NULL;
    }

    processHandle = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
                                FALSE, pid);

    /* check the process is running */
    GetExitCodeProcess(processHandle, &ProcessExitCode);
    if (ProcessExitCode == 0) {
        return NoSuchProcess();
    }

    if (processHandle == 0)
    {
        PyErr_SetFromWindowsErr(0);
        if (GetLastError() == ERROR_INVALID_PARAMETER) {
            return NoSuchProcess();
        }
        return NULL;
    }

    pebAddress = GetPebAddress(processHandle);

    /* get the address of ProcessParameters */
    if (!ReadProcessMemory(processHandle, (PCHAR)pebAddress + 0x10,
        &rtlUserProcParamsAddress, sizeof(PVOID), NULL))
    {
        CloseHandle(processHandle);
        if (GetLastError() == ERROR_PARTIAL_COPY) {
            /* Usually means the process has gone in the meantime */
            return NoSuchProcess();
        }
        else {
            return PyErr_SetFromWindowsErr(0);
        }

    }

    /* read the currentDirectory UNICODE_STRING structure.
       0x24 refers to "CurrentDirectoryPath" of RTL_USER_PROCESS_PARAMETERS
       structure (http://wj32.wordpress.com/2009/01/24/howto-get-the-command-line-of-processes/)
     */
    if (!ReadProcessMemory(processHandle, (PCHAR)rtlUserProcParamsAddress + 0x24,
        &currentDirectory, sizeof(currentDirectory), NULL))
    {
        CloseHandle(processHandle);
        if (GetLastError() == ERROR_PARTIAL_COPY) {
            /* Usually means the process has gone in the meantime */
            return NoSuchProcess();
        }
        else {
            return PyErr_SetFromWindowsErr(0);
        }
    }

    /* allocate memory to hold the command line */
    currentDirectoryContent = (WCHAR *)malloc(currentDirectory.Length+1);

    /* read the command line */
    if (!ReadProcessMemory(processHandle, currentDirectory.Buffer,
        currentDirectoryContent, currentDirectory.Length, NULL))
    {
        CloseHandle(processHandle);
        free(currentDirectoryContent);

        if (GetLastError() == ERROR_PARTIAL_COPY) {
            /* Usually means the process has gone in the meantime */
            return NoSuchProcess();
        }
        else {
            return PyErr_SetFromWindowsErr(0);
        }
    }

    // null-terminate the string to prevent wcslen from returning incorrect length
    // the length specifier is in characters, but commandLine.Length is in bytes
    currentDirectoryContent[(currentDirectory.Length/sizeof(WCHAR))] = '\0';

    // convert wchar array to a Python unicode string, and then to UTF8
    cwd_from_wchar = PyUnicode_FromWideChar(currentDirectoryContent,
                                            wcslen(currentDirectoryContent));

    #if PY_MAJOR_VERSION >= 3
        cwd = PyUnicode_FromObject(cwd_from_wchar);
    #else
        cwd = PyUnicode_AsUTF8String(cwd_from_wchar);
    #endif

    // decrement the reference count on our temp unicode str to avoid mem leak
    Py_XDECREF(cwd_from_wchar);
    returnPyObj = Py_BuildValue("N", cwd);

    CloseHandle(processHandle);
    free(currentDirectoryContent);
    return returnPyObj;
}


/*
Resume or suspends a process.
*/
int suspend_resume_process(DWORD pid, int suspend)
{
    // a huge thanks to http://www.codeproject.com/KB/threads/pausep.aspx
    HANDLE         hThreadSnap   = NULL;
    BOOL           bRet          = FALSE;
    THREADENTRY32  te32          = {0};

    hThreadSnap = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    if (hThreadSnap == INVALID_HANDLE_VALUE)
        return (FALSE);

    // Fill in the size of the structure before using it.
    te32.dwSize = sizeof(THREADENTRY32);

    // Walk the thread snapshot to find all threads of the process.
    // If the thread belongs to the process, add its information
    // to the display list.
    if (Thread32First(hThreadSnap, &te32))
    {
        do
        {
            if (te32.th32OwnerProcessID == pid)
            {
				HANDLE hThread = OpenThread(THREAD_SUSPEND_RESUME, FALSE,
                                            te32.th32ThreadID);
                if (hThread == NULL) {
                    CloseHandle(hThread);
                    PyErr_SetFromWindowsErr(0);
                    return FALSE;
                }
				if (suspend == 1)
				{
					//printf("Suspending Thread \n");
					if (SuspendThread(hThread) == (DWORD)-1) {
                        CloseHandle(hThread);
                        PyErr_SetFromWindowsErr(0);
                        return FALSE;
                    }
				}
				else
				{
					//printf("Resuming Thread \n");
					if (ResumeThread(hThread) == (DWORD)-1) {
                        CloseHandle(hThread);
                        PyErr_SetFromWindowsErr(0);
                        return FALSE;
                    }
				}
				CloseHandle(hThread);
            }
        }
        while (Thread32Next(hThreadSnap, &te32));
        bRet = TRUE;
    }
    else
        bRet = FALSE;  // could not walk the list of threads

    // Do not forget to clean up the snapshot object.
    CloseHandle(hThreadSnap);

    return (bRet);
}


static PyObject* suspend_process(PyObject* self, PyObject* args)
{
    long pid;
    int  suspend = 1;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        PyErr_SetString(PyExc_RuntimeError, "Invalid argument");
        return NULL;
    }
    if (! suspend_resume_process(pid, suspend)){
        PyErr_SetFromWindowsErr(0);
        return NULL;
    }
    Py_INCREF(Py_None);
    return Py_None;
}


static PyObject* resume_process(PyObject* self, PyObject* args)
{
    long pid;
    int suspend = 0;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        PyErr_SetString(PyExc_RuntimeError, "Invalid argument");
        return NULL;
    }
    if (! suspend_resume_process(pid, suspend)){
        PyErr_SetFromWindowsErr(0);
        return NULL;
    }
    Py_INCREF(Py_None);
    return Py_None;
}


static PyObject* get_process_open_files(PyObject* self, PyObject* args)
{
    long       pid;
    HANDLE     processHandle;
    DWORD      ProcessExitCode = 0;
    PyObject*  filesList;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        PyErr_SetString(PyExc_RuntimeError, "Invalid argument");
        return NULL;
    }

    if (!(processHandle = OpenProcess(PROCESS_DUP_HANDLE | PROCESS_QUERY_INFORMATION,
                                      FALSE,
                                      pid)))
    {
        if (GetLastError() == ERROR_INVALID_PARAMETER) {
            return NoSuchProcess();
        }
        return PyErr_SetFromWindowsErr(0);
    }

    GetExitCodeProcess(processHandle, &ProcessExitCode);
    if (ProcessExitCode == 0) {
        return NoSuchProcess();
    }

    filesList = get_open_files(pid, processHandle);
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
static PyObject* _QueryDosDevice(PyObject* self, PyObject* args)
{
    LPCTSTR   lpDevicePath;
    TCHAR d = TEXT('A');
    TCHAR     szBuff[5];

    if (!PyArg_ParseTuple(args, "s", &lpDevicePath)) {
        PyErr_SetString(PyExc_RuntimeError, "Invalid argument");
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
static PyObject* get_process_username(PyObject* self, PyObject* args)
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
    DWORD ProcessExitCode = 0;
    PyObject* returnObject;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        PyErr_SetString(PyExc_RuntimeError, "Invalid argument");
        return NULL;
    }

    /* Open the process and its token. */

    if (!(processHandle = OpenProcess(PROCESS_QUERY_INFORMATION, FALSE, pid))) {
        if (GetLastError() == ERROR_INVALID_PARAMETER) {
            return NoSuchProcess();
        }
        return PyErr_SetFromWindowsErr(0);
    }

    /* make sure the process is running */
    GetExitCodeProcess(processHandle, &ProcessExitCode);
    if (ProcessExitCode == 0) {
        return NoSuchProcess();
    }

    if (!OpenProcessToken(processHandle, TOKEN_QUERY, &tokenHandle)) {
        CloseHandle(processHandle);
        return PyErr_SetFromWindowsErr(0);
    }

    CloseHandle(processHandle);

    /* Get the user SID. */

    bufferSize = 0x100;
    user = malloc(bufferSize);

    if (!GetTokenInformation(tokenHandle,
                             TokenUser,
                             user,
                             bufferSize,
                             &bufferSize))
    {
        free(user);
        user = malloc(bufferSize);

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
    domainName = malloc(domainNameSize * sizeof(TCHAR));

    if (!LookupAccountSid(NULL, user->User.Sid, name, &nameSize, domainName,
                          &domainNameSize, &nameUse))
    {
        free(name);
        free(domainName);
        name = malloc(nameSize * sizeof(TCHAR));
        domainName = malloc(domainNameSize * sizeof(TCHAR));

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


/*
 * Return a list of network connections opened by a process
 */
static PyObject* get_process_connections(PyObject* self, PyObject* args)
{
    static long null_address[4] = { 0, 0, 0, 0 };

    unsigned long pid;
    PyObject* connectionsList;
    PyObject* connectionTuple;
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
    PVOID table;
    DWORD tableSize;
    PMIB_TCPTABLE_OWNER_PID tcp4Table;
    PMIB_UDPTABLE_OWNER_PID udp4Table;
    PMIB_TCP6TABLE_OWNER_PID tcp6Table;
    PMIB_UDP6TABLE_OWNER_PID udp6Table;
    ULONG i;
    CHAR addressBufferLocal[65];
    PyObject* addressTupleLocal;
    CHAR addressBufferRemote[65];
    PyObject* addressTupleRemote;

    if (!PyArg_ParseTuple(args, "l", &pid)) {
        PyErr_SetString(PyExc_RuntimeError, "Invalid argument");
        return NULL;
    }

    if (pid_is_running(pid) == 0) {
        return NoSuchProcess();
    }

    connectionsList = PyList_New(0);

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
    }

    if (getExtendedTcpTable)
    {
        /* TCP IPv4 */

        tableSize = 0;
        getExtendedTcpTable(NULL, &tableSize, FALSE, AF_INET,
                            TCP_TABLE_OWNER_PID_ALL, 0);

        table = malloc(tableSize);

        if (getExtendedTcpTable(table, &tableSize, FALSE, AF_INET,
                                TCP_TABLE_OWNER_PID_ALL, 0) == 0)
        {
            tcp4Table = table;

            for (i = 0; i < tcp4Table->dwNumEntries; i++)
            {
                if (tcp4Table->table[i].dwOwningPid != pid)
                    continue;

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

                connectionTuple = Py_BuildValue("(iiNNs)",
                    AF_INET,
                    SOCK_STREAM,
                    addressTupleLocal,
                    addressTupleRemote,
                    state_to_string(tcp4Table->table[i].dwState)
                    );
                PyList_Append(connectionsList, connectionTuple);
            }
        }

        free(table);

        /* TCP IPv6 */

        tableSize = 0;
        getExtendedTcpTable(NULL, &tableSize, FALSE, AF_INET6,
                            TCP_TABLE_OWNER_PID_ALL, 0);

        table = malloc(tableSize);

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

                connectionTuple = Py_BuildValue("(iiNNs)",
                    AF_INET6,
                    SOCK_STREAM,
                    addressTupleLocal,
                    addressTupleRemote,
                    state_to_string(tcp6Table->table[i].dwState)
                    );
                PyList_Append(connectionsList, connectionTuple);
            }
        }

        free(table);
    }

    if (getExtendedUdpTable)
    {
        /* UDP IPv4 */

        tableSize = 0;
        getExtendedUdpTable(NULL, &tableSize, FALSE, AF_INET,
                            UDP_TABLE_OWNER_PID, 0);

        table = malloc(tableSize);

        if (getExtendedUdpTable(table, &tableSize, FALSE, AF_INET,
                                UDP_TABLE_OWNER_PID, 0) == 0)
        {
            udp4Table = table;

            for (i = 0; i < udp4Table->dwNumEntries; i++)
            {
                if (udp4Table->table[i].dwOwningPid != pid)
                    continue;

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

                connectionTuple = Py_BuildValue("(iiNNs)",
                    AF_INET,
                    SOCK_DGRAM,
                    addressTupleLocal,
                    PyTuple_New(0),
                    ""
                    );
                PyList_Append(connectionsList, connectionTuple);
            }
        }

        free(table);

        /* UDP IPv6 */

        tableSize = 0;
        getExtendedUdpTable(NULL, &tableSize, FALSE, AF_INET6, UDP_TABLE_OWNER_PID, 0);

        table = malloc(tableSize);

        if (getExtendedUdpTable(table, &tableSize, FALSE, AF_INET6, UDP_TABLE_OWNER_PID, 0) == 0)
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

                connectionTuple = Py_BuildValue("(iiNNs)",
                    AF_INET6,
                    SOCK_DGRAM,
                    addressTupleLocal,
                    PyTuple_New(0),
                    ""
                    );
                PyList_Append(connectionsList, connectionTuple);
            }
        }

        free(table);
    }

    return connectionsList;
}

