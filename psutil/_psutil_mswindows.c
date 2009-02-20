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


int pid_exists(DWORD pid)
{
    DWORD *proclist = NULL;
    DWORD numberOfReturnedPIDs;
    DWORD i;
    
    proclist = get_pids(&numberOfReturnedPIDs);
    if (NULL == proclist) {
		PyErr_SetString(PyExc_RuntimeError, "get_pids() failed for pid_exists()");
        return -1;
    }

    for (i = 0; i < numberOfReturnedPIDs; i++) {
        if (pid == proclist[i]) {
            return 1;
        }
    }

    return 0;
}


static PyObject* get_pid_list(PyObject* self, PyObject* args)
{
    DWORD *proclist = NULL;
    DWORD numberOfReturnedPIDs;
    DWORD i;
	PyObject* retlist = PyList_New(0);
    
    proclist = get_pids(&numberOfReturnedPIDs);
    if (NULL == proclist) {
		PyErr_SetString(PyExc_RuntimeError, "get_pids() failed in get_pid_list()");
        return NULL;
    }

    for (i = 0; i < numberOfReturnedPIDs; i++) {
        PyList_Append(retlist, Py_BuildValue("i", proclist[i]) );
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
        UnsetSeDebug();
        return ret;
    }

    pid_return = pid_exists(pid);
    if (pid_return == 0) {
        UnsetSeDebug();
        return PyErr_Format(NoSuchProcessException, "No process found with pid %lu", pid); 
    } 

    if (pid_return == -1) {
        UnsetSeDebug();
        return NULL; //exception raised from within pid_exists()
    }

    if (pid < 0) {
        UnsetSeDebug();
        return ret;
    }

    //get a process handle
    hProcess = OpenProcess(PROCESS_ALL_ACCESS, FALSE, pid);
    if (hProcess == NULL) {
        PyErr_SetFromWindowsErr(0);
        UnsetSeDebug();
        return ret;
    }
    
    //kill the process
    if (! TerminateProcess(hProcess, 0) ){
        PyErr_SetFromWindowsErr(0);
        UnsetSeDebug();
        return ret;
    }
    
    UnsetSeDebug();
    return PyInt_FromLong(1);
}



static PyObject* get_process_info(PyObject* self, PyObject* args)
{
	//the argument passed should be a process id
	long pid;
    int pid_return;
    HANDLE hProcess;
    PyObject* infoTuple; 
	TCHAR processName[MAX_PATH] = TEXT("<unknown>");

    SetSeDebug();

	if (! PyArg_ParseTuple(args, "l", &pid)) {
        UnsetSeDebug();
        return PyErr_Format(PyExc_RuntimeError, "get_process_info(): Invalid argument - no PID provided.");
	}

    //special case for PID 0 (System Idle Process)
    if (0 == pid) {
	    infoTuple = Py_BuildValue("llssNll", pid, 0, "System Idle Process", "<unknown>", Py_BuildValue("[]"), -1, -1);
        UnsetSeDebug();
        return infoTuple;
    }

	//get the process information that we need
	//(name, path, arguments)

    pid_return = pid_exists(pid);
    if (pid_return == 0) {
        UnsetSeDebug();
        return PyErr_Format(NoSuchProcessException, "No process found with pid %lu", pid); 
    } 

    else if (pid_return == -1) {
        UnsetSeDebug();
        return NULL; //exception raised from within pid_exists()
    }

	//get a handle to the process or throw an exception
	hProcess = OpenProcess( PROCESS_QUERY_INFORMATION | 
        PROCESS_VM_READ, 
        FALSE, 
        pid 
    );

    if (NULL == hProcess) {
        PyErr_SetFromWindowsErr(0);
        UnsetSeDebug();
        return NULL;
    }

	//get the process name
    HMODULE hMod;
    DWORD cbNeeded;
    if ( EnumProcessModules( hProcess, &hMod, sizeof(hMod), &cbNeeded) ) {
        GetModuleBaseName( hProcess, hMod, processName,
            sizeof(processName)/sizeof(TCHAR) );
    }

	infoTuple = Py_BuildValue("lNssNll", pid, get_ppid(pid), processName, "<unknown>", get_arg_list(pid), -1, -1);
    UnsetSeDebug();
	return infoTuple;
}


