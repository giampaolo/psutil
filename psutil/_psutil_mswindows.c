#include <Python.h>
#include <windows.h>
#include <Psapi.h>

static PyObject* get_pid_list(PyObject* self, PyObject* args)
{
	int procArraySz = 1024;

	/* Win32 SDK says the only way to know if our process array
	 * wasn't large enough is to check the returned size and make
	 * sure that it doesn't match the size of the array.
	 * If it does we allocate a larger array and try again*/

	/* Stores the actual array */
	DWORD* procArray = NULL;
	/* Stores the byte size of the returned array from enumprocesses */
	DWORD enumReturnSz = 0;

	do {
		free(procArray);

		DWORD procArrayByteSz = procArraySz * sizeof(DWORD);
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
	DWORD numberOfReturnedPIDs = enumReturnSz / sizeof(DWORD);

	PyObject* retlist = PyList_New(0);
	int i;
    for (i = 0; i < numberOfReturnedPIDs; i++) {
        PyList_Append(retlist, Py_BuildValue("i", procArray[i]) );
    }

    //free C array
    free(procArray);

    return retlist;
}

static PyObject* get_process_info(PyObject* self, PyObject* args)
{
	//the argument passed should be a process id
	long pid;
	if (! PyArg_ParseTuple(args, "l", &pid)) {
		PyErr_SetString(PyExc_RuntimeError, "Invalid argument");
	}

	//get the process information that we need
	//(name, path, arguments)
	TCHAR processName[MAX_PATH] = TEXT("<unknown>");

	// Get a handle to the process.
	HANDLE hProcess = OpenProcess( PROCESS_QUERY_INFORMATION |
								   PROCESS_VM_READ,
								   FALSE, pid );

	// Get the process name.
	if (NULL != hProcess ) {
		HMODULE hMod;
		DWORD cbNeeded;

		if ( EnumProcessModules( hProcess, &hMod, sizeof(hMod), &cbNeeded) ) {
			GetModuleBaseName( hProcess, hMod, processName,
							   sizeof(processName)/sizeof(TCHAR) );
		}
	}

	PyObject* infoTuple = Py_BuildValue("ls", pid, processName);
	return infoTuple;
}

static PyMethodDef PsutilMethods[] =
{
     {"get_pid_list", get_pid_list, METH_VARARGS,
     	"Returns a python list of PIDs currently running on the host system"},
     {"get_process_info", get_process_info, METH_VARARGS,
       	"Returns a psutil.ProcessInfo object for the given PID"},
     {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC

init_psutil_mswindows(void)
{
     (void) Py_InitModule("_psutil_mswindows", PsutilMethods);
}
