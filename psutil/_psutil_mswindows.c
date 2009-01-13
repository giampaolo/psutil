#include <Python.h>
#include <windows.h>
#include <Psapi.h>

BOOL SetPrivilege(HANDLE hToken, LPCTSTR Privilege, BOOL bEnablePrivilege)
{
    TOKEN_PRIVILEGES tp;
    LUID luid;
    TOKEN_PRIVILEGES tpPrevious;
    DWORD cbPrevious=sizeof(TOKEN_PRIVILEGES);

    if(!LookupPrivilegeValue( NULL, Privilege, &luid )) return FALSE;

    //
    // first pass.  get current privilege setting
    //
    tp.PrivilegeCount = 1;
    tp.Privileges[0].Luid = luid;
    tp.Privileges[0].Attributes = 0;

    AdjustTokenPrivileges(
        hToken,
        FALSE,
        &tp,
        sizeof(TOKEN_PRIVILEGES),
        &tpPrevious,
        &cbPrevious
    );

    if (GetLastError() != ERROR_SUCCESS) return FALSE;

    // 
    // second pass. set privilege based on previous setting
    //
    tpPrevious.PrivilegeCount = 1;
    tpPrevious.Privileges[0].Luid = luid;

    if(bEnablePrivilege) {
        tpPrevious.Privileges[0].Attributes |= (SE_PRIVILEGE_ENABLED);
    }
    
    else {
        tpPrevious.Privileges[0].Attributes ^= (SE_PRIVILEGE_ENABLED &
                tpPrevious.Privileges[0].Attributes);
    }

    AdjustTokenPrivileges(
        hToken,
        FALSE,
        &tpPrevious,
        cbPrevious,
        NULL,
        NULL
    );

    if (GetLastError() != ERROR_SUCCESS) return FALSE;

    return TRUE;
}

int SetSeDebug() 
{ 
    HANDLE hToken;
    if(!OpenThreadToken(GetCurrentThread(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, FALSE, &hToken)){
        if (GetLastError() == ERROR_NO_TOKEN){
            if (!ImpersonateSelf(SecurityImpersonation)){
                //Log2File("Error setting impersonation [SetSeDebug()]", L_DEBUG);
                return 0;
            }
            if(!OpenThreadToken(GetCurrentThread(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, FALSE, &hToken)){
                //Log2File("Error Opening Thread Token", L_DEBUG);
                return 0;
            }
        }
    }

    // enable SeDebugPrivilege (open any process)
    if(!SetPrivilege(hToken, SE_DEBUG_NAME, TRUE)){
        //Log2File("Error setting SeDebug Privilege [SetPrivilege()]", L_WARN);
        return 0;
    }

    CloseHandle(hToken);
    return 1;
}


int UnsetSeDebug()
{
    HANDLE hToken;
    if(!OpenThreadToken(GetCurrentThread(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, FALSE, &hToken)){
        if(GetLastError() == ERROR_NO_TOKEN){
            if(!ImpersonateSelf(SecurityImpersonation)){
                //Log2File("Error setting impersonation! [UnsetSeDebug()]", L_DEBUG);
                return 0;
            }

            if(!OpenThreadToken(GetCurrentThread(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, FALSE, &hToken)){
                //Log2File("Error Opening Thread Token! [UnsetSeDebug()]", L_DEBUG);
                return 0;
            }
        }
    }

    //now disable SeDebug
    if(!SetPrivilege(hToken, SE_DEBUG_NAME, FALSE)){
        //Log2File("Error unsetting SeDebug Privilege [SetPrivilege()]", L_WARN);
        return 0;
    }

    CloseHandle(hToken);
    return 1;
}


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


static PyObject* kill_process(PyObject* self, PyObject* args)
{
    HANDLE hProcess;
    long pid;
    int ret = Py_BuildValue("i", ret);
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
    return Py_BuildValue("i", 1);
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
     {"kill_process", kill_process, METH_VARARGS,
         "Kill the process identified by the given PID"},
     {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC

init_psutil_mswindows(void)
{
     (void) Py_InitModule("_psutil_mswindows", PsutilMethods);
}
