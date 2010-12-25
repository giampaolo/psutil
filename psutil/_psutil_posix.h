/*
 * $Id$
 *
 * POSIX specific module methods for _psutil_posix
 */

#include <Python.h>

static PyObject* posix_getpriority(PyObject* self, PyObject* args);
static PyObject* posix_setpriority(PyObject* self, PyObject* args);

