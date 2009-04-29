/*
 * $Id$
 *
 * Windows platform-specific module methods for _psutil_mswindows
 */


#ifndef _AVAIL_WINVER_
    #define _AVAIL_WINVER_ 0x500
#endif

#include <Python.h>
#include <windows.h>
#include <Psapi.h>
#include <time.h>

#include "_psutil_mswindows.h"
#include "arch/mswindows/security.h"
#include "arch/mswindows/process_info.h"


static PyMethodDef PsutilMethods[] =
{
     {"get_pid_list", get_pid_list, METH_VARARGS,
     	"Returns a python list of PIDs currently running on the host system"},
     {"get_process_info", get_process_info, METH_VARARGS,
       	"Returns a psutil.ProcessInfo object for the given PID"},
     {"kill_process", kill_process, METH_VARARGS,
         "Kill the process identified by the given PID"},
     {"pid_exists", pid_exists, METH_VARARGS,
         "Determine if the process exists in the current process list."},
     {"get_process_cpu_times", get_process_cpu_times, METH_VARARGS,
         "Return process CPU kernel/user times."},
     {"get_process_create_time", get_process_create_time, METH_VARARGS,
         "Return process creation time."},
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
         "Return system cpu times"},
     {NULL, NULL, 0, NULL}
};

static PyObject *NoSuchProcessException;

PyMODINIT_FUNC
init_psutil_mswindows(void)
{
     PyObject *m;
     m = Py_InitModule("_psutil_mswindows", PsutilMethods);
     NoSuchProcessException = PyErr_NewException("_psutil_mswindows.NoSuchProcess", NULL, NULL);
     Py_INCREF(NoSuchProcessException);
     PyModule_AddObject(m, "NoSuchProcess", NoSuchProcessException);
     SetSeDebug();
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

    // HUGE thanks to:
    // http://johnstewien.spaces.live.com/blog/cns!E6885DB5CEBABBC8!831.entry
    //
    // This function converts the FILETIME structure to the 32 bit
    // Unix time structure.
    // The time_t is a 32-bit value for the number of seconds since
    // January 1, 1970. A FILETIME is a 64-bit for the number of
    // 100-nanosecond periods since January 1, 1601. Convert by
    // subtracting the number of 100-nanosecond period betwee 01-01-1970
    // and 01-01-1601, from time_t the divide by 1e+7 to get to the same
    // base granularity.
    ll = (((LONGLONG)(fileTime.dwHighDateTime)) << 32) + fileTime.dwLowDateTime;
    pt = (time_t)((ll - 116444736000000000ull)/10000000ull);

    // XXX - By using GetTickCount() time will wrap around to zero if the
    // system is run continuously for 49.7 days.
    uptime = GetTickCount() / 1000.00;
    return Py_BuildValue("f", (float)pt - uptime);
}


/*
 * Return 1 if PID exists in the current process list, else 0.
 */
static PyObject* pid_exists(PyObject* self, PyObject* args)
{
    long pid;
    int status;

	if (! PyArg_ParseTuple(args, "l", &pid)) {
        return PyErr_Format(PyExc_RuntimeError, "Invalid argument - no PID provided.");
	}

    status = pid_is_running(pid);
    if (-1 == status) {
        return NULL; //exception raised in pid_is_running()
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

    //free C array allocated for PIDs
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
    ret = PyInt_FromLong(0);

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        PyErr_SetString(PyExc_RuntimeError, "Invalid argument");
        return NULL;
    }

    if (pid < 0) {
        return NULL;
    }

    pid_return = pid_is_running(pid);
    if (pid_return == 0) {
        return PyErr_Format(NoSuchProcessException, "No process found with pid %lu", pid);
    }

    if (pid_return == -1) {
        return NULL; //exception raised from within pid_is_running()
    }

    //get a process handle
    hProcess = OpenProcess(PROCESS_TERMINATE, FALSE, pid);
    if (hProcess == NULL) {
        PyErr_SetFromWindowsErr(0);
        return NULL;
    }

    //kill the process
    if (! TerminateProcess(hProcess, 0) ){
        PyErr_SetFromWindowsErr(0);
        CloseHandle(hProcess);
        return NULL;
    }

    CloseHandle(hProcess);
    return PyInt_FromLong(1);
}


/*
 * Return a Python tuple (user_time, kernel_time)
 */
static PyObject* get_process_cpu_times(PyObject* self, PyObject* args)
{
    long        pid;
    HANDLE      hProcess;
    FILETIME    ftCreate, ftExit, ftKernel, ftUser;

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
            //bad PID so no such process
            PyErr_Format(NoSuchProcessException, "No process found with pid %lu", pid);
        }
        return NULL;
    }

    if (! GetProcessTimes(hProcess, &ftCreate, &ftExit, &ftKernel, &ftUser)) {
        PyErr_SetFromWindowsErr(0);
        if (GetLastError() == ERROR_ACCESS_DENIED) {
            //usually means the process has died so we throw a NoSuchProcess here
            PyErr_Format(NoSuchProcessException, "No process found with pid %lu", pid);
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

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        PyErr_SetString(PyExc_RuntimeError, "Invalid argument");
        return NULL;
    }

    // special case for PIDs 0 and 4
    // XXX - 0.0 means year 1970. Should we return uptime instead?
    if ( (0 == pid) || (4 == pid) ){
	   return Py_BuildValue("d", 0.0);
    }

    hProcess = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid);
    if (hProcess == NULL){
        PyErr_SetFromWindowsErr(0);
        if (GetLastError() == ERROR_INVALID_PARAMETER) {
            //bad PID so no such process
            PyErr_Format(NoSuchProcessException, "No process found with pid %lu", pid);
        }
        return NULL;
    }

    if (! GetProcessTimes(hProcess, &ftCreate, &ftExit, &ftKernel, &ftUser)) {
        PyErr_SetFromWindowsErr(0);
        if (GetLastError() == ERROR_ACCESS_DENIED) {
            //usually means the process has died so we throw a NoSuchProcess here
            PyErr_Format(NoSuchProcessException, "No process found with pid %lu", pid);
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
	//the argument passed should be a process id
	long pid;
    int pid_return;
    PyObject* infoTuple;
    PyObject* ppid;
    PyObject* arglist;
    PyObject* name;

	if (! PyArg_ParseTuple(args, "l", &pid)) {
        return PyErr_Format(PyExc_RuntimeError, "get_process_info(): Invalid argument - no PID provided.");
	}

    //special case for PID 0 (System Idle Process)
    if (0 == pid) {
        arglist = Py_BuildValue("[]");
	    infoTuple = Py_BuildValue("llssNll", pid, 0, "System Idle Process", "", arglist, -1, -1);
        return infoTuple;
    }

    //special case for PID 4 (System)
    if (4 == pid) {
        arglist = Py_BuildValue("[]");
	    infoTuple = Py_BuildValue("llssNll", pid, 0, "System", "", arglist, -1, -1);
        return infoTuple;
    }

    //check if the process exists before we waste time trying to read info
    pid_return = pid_is_running(pid);
    if (pid_return == 0) {
        return PyErr_Format(NoSuchProcessException, "No process found with pid %lu", pid);
    }

    if (pid_return == -1) {
        return NULL; //exception raised from within pid_is_running()
    }


    /* Now fetch the actual properties of the process */
    ppid = get_ppid(pid);
    if ( NULL == ppid ) {
        return NULL;  //exception string set in get_ppid()
    }

    name = get_name(pid);
    if ( NULL == name ) {
        return NULL;  //exception string set in get_name()
    }

    //If get_name or get_pid returns None that means the process is dead
    if (Py_None == name) {
        return PyErr_Format(NoSuchProcessException, "Process with pid %lu has disappeared", pid);
    }

    if (Py_None == ppid) {
        return PyErr_Format(NoSuchProcessException, "Process with pid %lu has disappeared", pid);
    }

    //May fail any of several ReadProcessMemory calls etc. and not indicate
    //a real problem so we ignore any errors and just live without commandline
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

	if (! PyArg_ParseTuple(args, "l", &pid)) {
        return PyErr_Format(PyExc_RuntimeError, "Invalid argument - no PID provided.");
	}

    hProcess = handle_from_pid(pid);
    if (NULL == hProcess) {
        return PyErr_SetFromWindowsErr(0);
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


/*
 * Return a Python tuple representing user, kernel and idle CPU times
 */
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


static PyObject* get_system_cpu_times(PyObject* self, PyObject* args)
{
	typedef BOOL (_stdcall *GST_PROC) (LPFILETIME, LPFILETIME, LPFILETIME);
	float idle, kernel, user;

#if _AVAIL_WINVER_ >= 0x501
    // GetSystemTimes supported

    FILETIME idle_time
    FILETIME kernel_time;
    FILETIME user_time;

    if (!GetSystemTimes(&idle_time, &kernel_time, &user_time))
    {
        return PyErr_SetFromWindowsErr(0);
    }

    idle = (float)(HI_T*idle_time.dwHighDateTime + LO_T*idle_time.dwLowDateTime);
    user = (float)(HI_T*user_time.dwHighDateTime + LO_T*user_time.dwLowDateTime);
    kernel = (float)(HI_T*kernel_time.dwHighDateTime + LO_T*kernel_time.dwLowDateTime);

    return Py_BuildValue("(ddd)", user, kernel, idle );

#else //Older Windows version, GetSystemTimes NOT supported (or using MinGW)

    typedef DWORD (_stdcall *NTQSI_PROC) (int, PVOID, ULONG, PULONG);
    NTQSI_PROC NtQuerySystemInformation;
    HINSTANCE hNtDll;
    SYSTEM_INFO si;
    UINT i;
    SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION *sppi = NULL;

    // dynamic linking is mandatory to use NtQuerySystemInformation
    hNtDll = LoadLibrary(TEXT("ntdll.dll"));
    if (hNtDll != NULL)
    {
        // gets NtQuerySystemInformation address
        NtQuerySystemInformation = (NTQSI_PROC)GetProcAddress(hNtDll, "NtQuerySystemInformation");
        if (NtQuerySystemInformation != NULL)
        {
            // retrives number of processors
            GetSystemInfo(&si);

            // allocates an array of SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION structures, one per processor
            sppi=(SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION *)
                malloc(si.dwNumberOfProcessors*sizeof(SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION));
            if (sppi != NULL)
            {
                // gets cpu time informations
                if (0 == NtQuerySystemInformation(
                            SystemProcessorPerformanceInformation,
                            sppi,
                            si.dwNumberOfProcessors*sizeof(SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION),
                            NULL))
                {
                    // computes system global times summing each processor value
                    idle = user = kernel = 0;
                    for (i=0; i<si.dwNumberOfProcessors; i++)
                    {
                        idle += (float)(HI_T*sppi[i].IdleTime.HighPart + LO_T*sppi[i].IdleTime.LowPart);
                        user += (float)(HI_T*sppi[i].UserTime.HighPart + LO_T*sppi[i].UserTime.LowPart);
                        kernel += (float)(HI_T*sppi[i].KernelTime.HighPart + LO_T*sppi[i].KernelTime.LowPart);
                    }

                    return Py_BuildValue("(ddd)", user, kernel, idle );


                } // END NtQuerySystemInformation

            } // END malloc SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION

        } // END GetProcAddress

    } // END LoadLibrary

    PyErr_SetFromWindowsErr(0);
    if (sppi) free(sppi);
    if (hNtDll) FreeLibrary(hNtDll);
    return 0;

#endif

}


