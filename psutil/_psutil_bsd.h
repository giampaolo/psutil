/*
 * $Id$
 *
 * BSD platform-specific module methods for _psutil_bsd
 */

#include <Python.h>

static int pid_exists(long pid);
static PyObject* get_pid_list(PyObject* self, PyObject* args);
static PyObject* get_process_info(PyObject* self, PyObject* args);

