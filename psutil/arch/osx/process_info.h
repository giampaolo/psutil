/*
 * $Id$
 *
 * Helper functions related to fetching process information. Used by _psutil_osx
 * module methods.
 */

#include <Python.h>

int GetBSDProcessList(kinfo_proc **procList, size_t *procCount);
int getcmdargs(long pid, PyObject **exec_path, PyObject **arglist, PyObject **envdict);
PyObject* get_arg_list(long pid);

