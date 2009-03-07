/*
 * $Id$ 
 * 
 * Windows platform-specific module methods for _psutil_mswindows
 */

#include <windows.h>
#include <Psapi.h>
#include <Python.h>

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
}



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


static PyObject* kill_process(PyObject* self, PyObject* args)
{
    HANDLE hProcess;
    long pid;
    int pid_return;
    PyObject* ret;
    ret = PyInt_FromLong(0);
    
    SetSeDebug();

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
        CloseHandle(hProcess);
        PyErr_SetFromWindowsErr(0);
        return NULL;
    }

    if (! GetProcessTimes(hProcess, &ftCreate, &ftExit, &ftKernel, &ftUser)) {
        CloseHandle(hProcess);
        PyErr_SetFromWindowsErr(0);
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
		(double)(ftKernel.dwHighDateTime*429.4967296 + \
		         ftKernel.dwLowDateTime*1e-7),
		(double)(ftUser.dwHighDateTime*429.4967296 + \
		         ftUser.dwLowDateTime*1e-7)
        );
}




static PyObject* get_process_info(PyObject* self, PyObject* args)
{
	//the argument passed should be a process id
	long pid;
    int pid_return;
    PyObject* infoTuple; 
    PyObject* ppid;
    PyObject* arglist;
    PyObject* name;

    SetSeDebug();

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


