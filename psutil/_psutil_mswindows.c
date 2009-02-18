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


static PyObject* get_pid_list(PyObject* self, PyObject* args)
{
	PyObject* retlist = PyList_New(0);
	int procArraySz = 1024;
	DWORD i;

	/* Win32 SDK says the only way to know if our process array
	 * wasn't large enough is to check the returned size and make
	 * sure that it doesn't match the size of the array.
	 * If it does we allocate a larger array and try again*/

	/* Stores the actual array */
	DWORD* procArray = NULL;
	DWORD procArrayByteSz;
	
    /* Stores the byte size of the returned array from enumprocesses */
	DWORD enumReturnSz = 0;
	
    DWORD numberOfReturnedPIDs;

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
    numberOfReturnedPIDs = enumReturnSz / sizeof(DWORD);

    retlist = PyList_New(0);
    for (i = 0; i < numberOfReturnedPIDs; i++) {
        PyList_Append(retlist, Py_BuildValue("i", procArray[i]) );
    }

    //free C array
    free(procArray);

    return retlist;
}


static PyObject* kill_process(PyObject* self, PyObject* args)
{
    HANDLE hProcess;
    long pid;
    PyObject* ret;
    ret = PyInt_FromLong(0);
    SetSeDebug();
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        PyErr_SetString(PyExc_RuntimeError, "Invalid argument");
        UnsetSeDebug();
        return ret;
    }

    if (pid < 0) {
        UnsetSeDebug();
        return ret;
    }

    //get a process handle
    hProcess = OpenProcess(PROCESS_ALL_ACCESS, FALSE, pid);
    if(hProcess == NULL){
        UnsetSeDebug();
        return ret;
    }
    
    //kill the process
    if(!TerminateProcess(hProcess, 0)){
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
    HANDLE hProcess;
    PyObject* infoTuple; 
	TCHAR processName[MAX_PATH] = TEXT("<unknown>");

    SetSeDebug();

	if (! PyArg_ParseTuple(args, "l", &pid)) {
		PyErr_SetString(PyExc_RuntimeError, "Invalid argument");
	}

	//get the process information that we need
	//(name, path, arguments)

	// Get a handle to the process.
	hProcess = OpenProcess( PROCESS_QUERY_INFORMATION | 
        PROCESS_VM_READ, 
        FALSE, 
        pid 
    );

	// Get the process name.
	if (NULL != hProcess ) {
		HMODULE hMod;
		DWORD cbNeeded;
		if ( EnumProcessModules( hProcess, &hMod, sizeof(hMod), &cbNeeded) ) {
		    GetModuleBaseName( hProcess, hMod, processName,
                sizeof(processName)/sizeof(TCHAR) );
		}
	}

	infoTuple = Py_BuildValue("lNssNll", pid, get_ppid(pid), processName, "<unknown>", get_arg_list(pid), -1, -1);
	return infoTuple;
}

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

PyMODINIT_FUNC

init_psutil_mswindows(void)
{
     (void) Py_InitModule("_psutil_mswindows", PsutilMethods);
}
