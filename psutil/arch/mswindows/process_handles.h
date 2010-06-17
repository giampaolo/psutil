#include <Python.h>
#include <windows.h>

PyObject* get_open_files(long pid, HANDLE processHandle);
