#include <Python.h>
#include <windows.h>
#include <Psapi.h>
#include <tlhelp32.h>

/* 
 * Code taken from 
 *     http://wj32.wordpress.com/2009/01/24/howto-get-the-command-line-of-processes/
 *
 * typedefs needed to compile against ntdll functions not exposted in the API
 */
typedef LONG NTSTATUS;

typedef NTSTATUS (NTAPI *_NtQueryInformationProcess)(
    HANDLE ProcessHandle,
    DWORD ProcessInformationClass,
    PVOID ProcessInformation,
    DWORD ProcessInformationLength,
    PDWORD ReturnLength
    );

typedef struct _UNICODE_STRING
{
    USHORT Length;
    USHORT MaximumLength;
    PWSTR Buffer;
} UNICODE_STRING, *PUNICODE_STRING;

typedef struct _PROCESS_BASIC_INFORMATION
{
    DWORD ExitStatus;
    PVOID PebBaseAddress;
    DWORD AffinityMask;
    DWORD BasePriority;
    DWORD UniqueProcessId;
    DWORD ParentProcessId;
} PROCESS_BASIC_INFORMATION, *PPROCESS_BASIC_INFORMATION;

//fetch the PEB base address from NtQueryInformationProcess()
PVOID GetPebAddress(HANDLE ProcessHandle)
{
    _NtQueryInformationProcess NtQueryInformationProcess =
        (_NtQueryInformationProcess)GetProcAddress(
        GetModuleHandleA("ntdll.dll"), "NtQueryInformationProcess");
    PROCESS_BASIC_INFORMATION pbi;

    NtQueryInformationProcess(ProcessHandle, 0, &pbi, sizeof(pbi), NULL);
    return pbi.PebBaseAddress;
}


static PyObject* get_ppid(long pid)
{
    PyObject *ppid = Py_BuildValue("");
	HANDLE h = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
	PROCESSENTRY32 pe = { 0 };
	pe.dwSize = sizeof(PROCESSENTRY32);    

	if( Process32First(h, &pe)) {
	    do {
			if (pe.th32ProcessID == pid) {
				//printf("PID: %i; PPID: %i\n", pid, pe.th32ParentProcessID);
                ppid = Py_BuildValue("l", pe.th32ParentProcessID);
			}
		} while( Process32Next(h, &pe));
	}

    return ppid;
}


static PyObject* get_arg_list(long pid)
{
    int nArgs, i;
    LPWSTR *szArglist;
    HANDLE processHandle;
    PVOID pebAddress;
    PVOID rtlUserProcParamsAddress;
    UNICODE_STRING commandLine;
    WCHAR *commandLineContents;
    PyObject *argList = Py_BuildValue("[]");

    if ((processHandle = OpenProcess(
        PROCESS_QUERY_INFORMATION | /* required for NtQueryInformationProcess */
        PROCESS_VM_READ, /* required for ReadProcessMemory */
        FALSE, pid)) == 0)
    {
        //printf("Could not open process!\n");
        return argList;
    }

    pebAddress = GetPebAddress(processHandle);

    /* get the address of ProcessParameters */
    if (!ReadProcessMemory(processHandle, (PCHAR)pebAddress + 0x10,
        &rtlUserProcParamsAddress, sizeof(PVOID), NULL))
    {
        //printf("Could not read the address of ProcessParameters!\n");
        return argList;
    }

    /* read the CommandLine UNICODE_STRING structure */
    if (!ReadProcessMemory(processHandle, (PCHAR)rtlUserProcParamsAddress + 0x40,
        &commandLine, sizeof(commandLine), NULL))
    {
        //printf("Could not read CommandLine!\n");
        return argList;
    }

    /* allocate memory to hold the command line */
    commandLineContents = (WCHAR *)malloc(commandLine.Length+1);

    /* read the command line */
    if (!ReadProcessMemory(processHandle, commandLine.Buffer,
        commandLineContents, commandLine.Length, NULL))
    {
        //printf("Could not read the command line string!\n");
        return argList;
    }

    /* print the commandline */
    //printf("%.*S\n", commandLine.Length / 2, commandLineContents);

    //null-terminate the string to prevent wcslen from returning incorrect length
    //the length specifier is in characters, but commandLine.Length is in bytes
    commandLineContents[(commandLine.Length/sizeof(WCHAR))] = NULL;
   
    //attemempt tp parse the command line using Win32 API, fall back on string
    //cmdline version otherwise
    szArglist = CommandLineToArgvW(commandLineContents, &nArgs);
    if (NULL == szArglist) {
        //failed to parse arglist
        //encode as a UTF8 Python string object from WCHAR string
        argList = Py_BuildValue("N", PyUnicode_AsUTF8String(PyUnicode_FromWideChar(commandLineContents, commandLine.Length/2)));
    } 
    
    else {
        //arglist parsed as array of UNICODE_STRING, so convert each to Python
        //string object and add to arg list
        argList = Py_BuildValue("[]");
        for( i=0; i<nArgs; i++) {
            //printf("%d: %.*S (%d characters)\n", i, wcslen(szArglist[i]), szArglist[i], wcslen(szArglist[i]));
            PyList_Append(argList, Py_BuildValue("N", PyUnicode_AsUTF8String(PyUnicode_FromWideChar(szArglist[i], wcslen(szArglist[i])))));
        }
    } 
    
    LocalFree(szArglist);
    CloseHandle(processHandle);
    free(commandLineContents);

    return argList;
}



static BOOL SetPrivilege(HANDLE hToken, LPCTSTR Privilege, BOOL bEnablePrivilege)
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

static int SetSeDebug() 
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


static int UnsetSeDebug()
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
