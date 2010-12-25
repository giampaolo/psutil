/*
 * $Id: _psutil_bsd.h 847 2010-12-10 22:06:32Z g.rodola $
 *
 * BSD platform-specific module methods for _psutil_bsd
 */

#include <Python.h>

static PyObject* posix_getpriority(PyObject* self, PyObject* args);
static PyObject* posix_setpriority(PyObject* self, PyObject* args);

