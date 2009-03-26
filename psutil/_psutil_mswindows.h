/*
 * $Id$
 *
 * Windows platform-specific module methods for _psutil_mswindows
 *
 */

#include <Python.h>

static PyObject* get_pid_list(PyObject* self, PyObject* args);
static PyObject* kill_process(PyObject* self, PyObject* args);
static PyObject* get_process_info(PyObject* self, PyObject* args);
static PyObject* pid_exists(PyObject* self, PyObject* args);
static PyObject* get_process_cpu_times(PyObject* self, PyObject* args);
static PyObject* get_process_create_time(PyObject* self, PyObject* args);
static PyObject* get_num_cpus(PyObject* self, PyObject* args);
static PyObject* get_system_uptime(PyObject* self, PyObject* args);
static PyObject* get_memory_info(PyObject* self, PyObject* args);
static PyObject* get_total_phymem(PyObject* self, PyObject* args);
static PyObject* get_total_virtmem(PyObject* self, PyObject* args);
static PyObject* get_used_phymem(PyObject* self, PyObject* args);
static PyObject* get_used_virtmem(PyObject* self, PyObject* args);

