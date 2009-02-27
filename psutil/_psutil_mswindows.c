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


DWORD* get_pids(DWORD *numberOfReturnedPIDs){
	int procArraySz = 1024;

	/* Win32 SDK says the only way to know if our process array
	 * wasn't large enough is to check the returned size and make
	 * sure that it doesn't match the size of the array.
	 * If it does we allocate a larger array and try again*/

	/* Stores the actual array */
	DWORD *procArray = NULL;
	DWORD procArrayByteSz;
	
    /* Stores the byte size of the returned array from enumprocesses */
	DWORD enumReturnSz = 0;
	
	do {
		free(procArray);

        procArrayByteSz = procArraySz * sizeof(DWORD);
		procArray = malloc(procArrayByteSz);


		if (! EnumProcesses(procArray, procArrayByteSz, &enumReturnSz))
		{
			free(procArray);
			/* Throw exception to python */
			PyErr_SetString(PyExc_RuntimeError, "EnumProcesses failed");
			return NULL;
		}
		else if (enumReturnSz == procArrayByteSz)
		{
			/* Process list was too large.  Allocate more space*/
			procArraySz += 1024;
		}

		/* else we have a good list */

	} while(enumReturnSz == procArraySz * sizeof(DWORD));

	/* The number of elements is the returned size / size of each element */
    *numberOfReturnedPIDs = enumReturnSz / sizeof(DWORD);

    return procArray;
}


int is_running(DWORD pid)
{
    DWORD *proclist = NULL;
    DWORD numberOfReturnedPIDs;
    DWORD i;
    
    proclist = get_pids(&numberOfReturnedPIDs);
    if (NULL == proclist) {
		PyErr_SetString(PyExc_RuntimeError, "get_pids() failed for is_running()");
        return -1;
    }

    for (i = 0; i < numberOfReturnedPIDs; i++) {
        if (pid == proclist[i]) {
            free(proclist);
            return 1;
        }
    }

    free(proclist);
    return 0;
}


static PyObject* pid_exists(PyObject* self, PyObject* args)
{
    long pid;
    int status;

	if (! PyArg_ParseTuple(args, "l", &pid)) {
        return PyErr_Format(PyExc_RuntimeError, "Invalid argument - no PID provided.");
	}

    status = is_running(pid);
    if (-1 == status) {
        return NULL; //exception raised in is_running()
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

    pid_return = is_running(pid);
    if (pid_return == 0) {
        return PyErr_Format(NoSuchProcessException, "No process found with pid %lu", pid); 
    } 

    if (pid_return == -1) {
        return NULL; //exception raised from within is_running()
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



static PyObject* get_process_info(PyObject* self, PyObject* args)
{
	//the argument passed should be a process id
	long pid;
    int pid_return;
    HANDLE hProcess;
    HMODULE hMod;
    DWORD cbNeeded;
    DWORD last_err;
    PyObject* infoTuple; 
    PyObject* ppid;
    PyObject* arglist;
    BOOL enum_mod_retval;
	TCHAR processName[MAX_PATH] = TEXT("<unknown>");

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

	//get the process information that we need
	//(name, path, arguments)

    pid_return = is_running(pid);
    if (pid_return == 0) {
        return PyErr_Format(NoSuchProcessException, "No process found with pid %lu", pid); 
    } 

    else if (pid_return == -1) {
        return NULL; //exception raised from within is_running()
    }

	//get a handle to the process or throw an exception
	hProcess = OpenProcess( PROCESS_QUERY_INFORMATION | 
        PROCESS_VM_READ, 
        FALSE, 
        pid 
    );

    if (NULL == hProcess) {
        PyErr_SetFromWindowsErr(0);
        return NULL;
    }

	//Get the process module list so we can get the process name
    //NOTE: sometimes EnumProcessModules fails with a err 299 
    //"Only part of a ReadProcessMemory or WriteProcessMemory request was completed"
    //if that happens try again until we can get the data
    enum_mod_retval = EnumProcessModules( hProcess, &hMod, sizeof(hMod), &cbNeeded); 
    last_err = GetLastError();
    if (! enum_mod_retval) {
        while (0 == enum_mod_retval) {
            if (last_err == ERROR_PARTIAL_COPY) {
                enum_mod_retval = EnumProcessModules( hProcess, &hMod, sizeof(hMod), &cbNeeded); 
                continue;
            }
            
            else {
                PyErr_SetFromWindowsErr(last_err);
                CloseHandle(hMod);
                CloseHandle(hProcess);
                return NULL;
            }
            last_err = GetLastError();
        }
    }
   
    //EnumProcessModules succeeded, move on to get the process name
    if (! GetModuleBaseName( hProcess, hMod, processName, sizeof(processName)/sizeof(TCHAR) ) ) {
        PyErr_SetFromWindowsErr(0);
        CloseHandle(hMod);
        CloseHandle(hProcess);
        return NULL;
    }

    ppid = get_ppid(pid);
    if ( NULL == ppid ) {
        CloseHandle(hMod);
        CloseHandle(hProcess);
        return NULL;  //exception string set in get_ppid()
    }
    
    arglist = get_arg_list(pid);
    if ( NULL == arglist ) {
        // carry on anyway if we couldn't get the arg list
        arglist = Py_BuildValue("[]");
    }

	infoTuple = Py_BuildValue("lNssNll", pid, ppid, processName, "", arglist, -1, -1);

    CloseHandle(hProcess);
    CloseHandle(hMod);
	return infoTuple;
}


