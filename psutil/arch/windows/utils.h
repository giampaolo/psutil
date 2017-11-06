#if !defined(__PSUTILS_ARCH_WINDOWS_UTILS_H)
#define __PSUTILS_ARCH_WINDOWS_UTILS_H

#include <Python.h>
#include <windows.h>

#ifdef PSUTIL_WINDOWS
#include <tchar.h>
#elif defined(PSUTIL_CYGWIN)
#define _tcscmp strcmp
#define _stprintf_s snprintf
#define _countof sizeof
#endif

PyObject* psutil_win32_QueryDosDevice(PyObject *self, PyObject *args);

#endif
