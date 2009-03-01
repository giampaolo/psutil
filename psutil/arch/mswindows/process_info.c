/* 
 * $Id$
 *
 * Helper functions related to fetching process information. Used by _psutil_mswindows 
 * module methods.
 */

#include <Python.h>
#include <windows.h>
#include <Psapi.h>
#include <tlhelp32.h>

#include "process_info.h"


/* 
 * NtQueryInformationProcess code taken from 
 *
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


/* 
 * returns a Python list representing the arguments for the process 
 * with given pid or NULL on error.
 */
PyObject* get_arg_list(long pid)
{
    int nArgs, i;
    LPWSTR *szArglist;
    HANDLE processHandle;
    PVOID pebAddress;
    PVOID rtlUserProcParamsAddress;
    UNICODE_STRING commandLine;
    WCHAR *commandLineContents;
    PyObject *arg = NULL;
    PyObject *arg_from_wchar = NULL;
    PyObject *argList = NULL;


    processHandle = handle_from_pid(pid);
    if(NULL == processHandle) {
        //printf("Could not open process!\n");
        return argList;
    }

    pebAddress = GetPebAddress(processHandle);

    /* get the address of ProcessParameters */
    if (!ReadProcessMemory(processHandle, (PCHAR)pebAddress + 0x10,
        &rtlUserProcParamsAddress, sizeof(PVOID), NULL))
    {
        //printf("Could not read the address of ProcessParameters!\n");
        CloseHandle(processHandle);
        return argList;
    }

    /* read the CommandLine UNICODE_STRING structure */
    if (!ReadProcessMemory(processHandle, (PCHAR)rtlUserProcParamsAddress + 0x40,
        &commandLine, sizeof(commandLine), NULL))
    {
        //printf("Could not read CommandLine!\n");
        CloseHandle(processHandle);
        return argList;
    }


    /* allocate memory to hold the command line */
    commandLineContents = (WCHAR *)malloc(commandLine.Length+1);

    /* read the command line */
    if (!ReadProcessMemory(processHandle, commandLine.Buffer,
        commandLineContents, commandLine.Length, NULL))
    {
        //printf("Could not read the command line string!\n");
        CloseHandle(processHandle);
        free(commandLineContents);
        return argList;
    }

    /* print the commandline */
    //printf("%.*S\n", commandLine.Length / 2, commandLineContents);

    //null-terminate the string to prevent wcslen from returning incorrect length
    //the length specifier is in characters, but commandLine.Length is in bytes
    commandLineContents[(commandLine.Length/sizeof(WCHAR))] = '\0';
   
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
            arg_from_wchar = PyUnicode_FromWideChar(szArglist[i], wcslen(szArglist[i]));
            arg = PyUnicode_AsUTF8String(arg_from_wchar);
            Py_XDECREF(arg_from_wchar);
            PyList_Append(argList, arg);
            Py_XDECREF(arg);
        }
    } 
   
    LocalFree(szArglist);
    free(commandLineContents);
    CloseHandle(processHandle);
    return argList;
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


int pid_is_running(DWORD pid)
{
    HANDLE hProcess;
    DWORD exitCode;
    
    //Special case for PID 0 System Idle Process
    if (pid == 0) {
        return 1;
    }

    if (pid < 0) {
        return 0;
    }

    hProcess = handle_from_pid(pid);
    if (NULL == hProcess) {
        if (GetLastError() == ERROR_INVALID_PARAMETER) { //invalid parameter is no such process
            return 0; 
        }
        PyErr_SetFromWindowsErr(0);
        return -1;
    }

    if (GetExitCodeProcess(hProcess, &exitCode)) {
        return (exitCode == STILL_ACTIVE);
    }

    PyErr_SetFromWindowsErr(0);
    return -1;
}


int pid_in_proclist(DWORD pid)
{
    DWORD *proclist = NULL;
    DWORD numberOfReturnedPIDs;
    DWORD i;
    
    proclist = get_pids(&numberOfReturnedPIDs);
    if (NULL == proclist) {
		PyErr_SetString(PyExc_RuntimeError, "get_pids() failed for pid_in_proclist()");
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


//Get a process handle from a pid with PROCESS_QUERY_INFORMATION rights
HANDLE handle_from_pid(DWORD pid)
{
    return OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid);
}


//Check exit code from a process handle. Return FALSE on an error also
BOOL is_running(HANDLE hProcess) 
{
    DWORD dwCode;

    if (NULL == hProcess) {
        return FALSE;
    }

    if (GetExitCodeProcess(hProcess, &dwCode)) {
        return (dwCode == STILL_ACTIVE);
    }
    return FALSE;
}


//Return None to represent NoSuchProcess, else return NULL for 
//other exception or the name as a Python string
PyObject* get_name(long pid) 
{
    HANDLE hProcess;
    HMODULE hMod;
    DWORD eaccess_cnt;
    DWORD cbNeeded;
    DWORD last_err;
    BOOL enum_mod_retval;
	TCHAR processName[MAX_PATH] = TEXT("<unknown>");
    
    hProcess = handle_from_pid(pid);
    if (NULL == hProcess) {
        PyErr_SetFromWindowsErr(0);
        return NULL;
    }

	//Get the process module list so we can get the process name
    //NOTE: sometimes EnumProcessModules fails with a err 299 
    //"Only part of a ReadProcessMemory or WriteProcessMemory request was completed"
    //if that happens try again until we can get the data
    eaccess_cnt = 0; //keep track of access denied errors 
    enum_mod_retval = EnumProcessModules( hProcess, &hMod, sizeof(hMod), &cbNeeded); 
    last_err = GetLastError();
    if (! enum_mod_retval) {
        while ( (0 == enum_mod_retval) && (! eaccess_cnt ) ) {
            if (last_err == ERROR_PARTIAL_COPY) {
                enum_mod_retval = EnumProcessModules( hProcess, &hMod, sizeof(hMod), &cbNeeded); 
                last_err = GetLastError();
                continue;
            }

            /*
             * ACCESS_DENIED can be returned if the process has died. If we
             * see ERROR_ACCESS_DENIED, check the exit code of the process 
             * to see if it is still running and if not, throw NoSuchProcess.
             */
            if (last_err == ERROR_ACCESS_DENIED) {
                //potentially swallows an error from GetExitCodePRocess
                if (! is_running(hProcess)) { 
                    CloseHandle(hProcess);
                    CloseHandle(hMod);
                    //special case, return NONE if NoSuchProcess
                    return Py_BuildValue("");
                }
            }
            
            PyErr_SetFromWindowsErr(last_err);
            CloseHandle(hMod);
            CloseHandle(hProcess);
            return NULL;
        }
    }
   
    //EnumProcessModules succeeded, move on to get the process name
    if (! GetModuleBaseName( hProcess, hMod, processName, sizeof(processName)/sizeof(TCHAR) ) ) {
        PyErr_SetFromWindowsErr(0);
        CloseHandle(hMod);
        CloseHandle(hProcess);
        return NULL;
    }

    return Py_BuildValue("s", processName);
}




/* returns parent pid (as a Python int) for given pid or None on failure */
PyObject* get_ppid(long pid)
{
	HANDLE h = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
	PROCESSENTRY32 pe = { 0 };
	pe.dwSize = sizeof(PROCESSENTRY32);    

	if( Process32First(h, &pe)) {
	    do {
			if (pe.th32ProcessID == pid) {
				//printf("PID: %i; PPID: %i\n", pid, pe.th32ParentProcessID);
                CloseHandle(h);
                return Py_BuildValue("l", pe.th32ParentProcessID);
			}
		} while( Process32Next(h, &pe));
	}
    
    CloseHandle(h);
    return NULL;
}

