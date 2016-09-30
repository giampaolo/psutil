#ifndef __PY_ERROR_H__
#define __PY_ERROR_H__

#include <Python.h>

PyObject *PyErr_SetFromWindowsErr(int);

#endif
