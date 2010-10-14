/*
 * $Id$
 *
 * Windows platform-specific module methods for _psutil_mswindows
 *
 */

#include <Python.h>
#include <windows.h>

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
static PyObject* get_avail_phymem(PyObject* self, PyObject* args);
static PyObject* get_avail_virtmem(PyObject* self, PyObject* args);
static PyObject* get_system_cpu_times(PyObject* self, PyObject* args);
static PyObject* get_process_cwd(PyObject* self, PyObject* args);
static PyObject* suspend_process(PyObject* self, PyObject* args);
static PyObject* resume_process(PyObject* self, PyObject* args);
static PyObject* get_process_open_files(PyObject* self, PyObject* args);
static PyObject* _QueryDosDevice(PyObject* self, PyObject* args);
static PyObject* get_process_username(PyObject* self, PyObject* args);
static PyObject* get_process_connections(PyObject* self, PyObject* args);

int suspend_resume_process(DWORD pid, int suspend);
