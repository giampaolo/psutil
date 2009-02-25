/*
 * $Id$
 *
 * Helper functions related to fetching process information. Used by _psutil_bsd
 * module methods.
 */

#include <Python.h>

typedef struct kinfo_proc kinfo_proc;

int get_proc_list();
char *getcmdargs();
char *getcmdpath();
PyObject* get_arg_list(long pid);

