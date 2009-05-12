/*
 * $Id$
 *
 * Helper functions related to fetching process information. Used by _psutil_osx
 * module methods.
 */

#include <Python.h>


typedef struct kinfo_proc kinfo_proc;

int GetBSDProcessList(kinfo_proc **procList, size_t *procCount);
int getcmdargs(long pid, PyObject **exec_path, PyObject **envlist, PyObject **arglist);
PyObject* get_arg_list(long pid);

