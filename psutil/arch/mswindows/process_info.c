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
 * with given pid 
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
            PyList_Append(argList, Py_BuildValue("N", PyUnicode_AsUTF8String(PyUnicode_FromWideChar(szArglist[i], wcslen(szArglist[i])))));
        }
    } 
    
    LocalFree(szArglist);
    CloseHandle(processHandle);
    free(commandLineContents);

    return argList;
}


/* returns parent pid (as a Python int) for given pid or None on failure */
PyObject* get_ppid(long pid)
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

