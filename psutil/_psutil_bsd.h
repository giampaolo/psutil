/*
 * $Id$
 *
 * BSD platform-specific module methods for _psutil_bsd
 */

#include <Python.h>

static int pid_exists(long pid);
static PyObject* get_pid_list(PyObject* self, PyObject* args);
static PyObject* get_process_info(PyObject* self, PyObject* args);
static PyObject* get_cpu_times(PyObject* self, PyObject* args);
static PyObject* get_process_create_time(PyObject* self, PyObject* args);
static PyObject* get_num_cpus(PyObject* self, PyObject* args);