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
int pid_in_proclist(long pid);
DWORD* get_pids(DWORD *numberOfReturnedPIDs);
