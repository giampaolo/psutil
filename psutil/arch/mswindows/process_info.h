/* 
 * $Id$
 *
 * Helper functions related to fetching process information. Used by _psutil_mswindows 
 * module methods.
 */

#include <Python.h>
#include <windows.h>


PVOID GetPebAddress(HANDLE ProcessHandle);
HANDLE handle_from_pid(long pid);
BOOL is_running(HANDLE hProcess);
PyObject* get_arg_list(long pid);
PyObject* get_ppid(long pid);
PyObject* get_name(long pid);

