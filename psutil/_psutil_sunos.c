/*
 * $Id$
 *
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Functions specific to Sun OS Solaris platforms.
 */

#include <Python.h>

// fix for "Cannot use procfs in the large file compilation environment"
// error, see:
// http://sourceware.org/ml/gdb-patches/2010-11/msg00336.html
#undef _FILE_OFFSET_BITS

#include <sys/types.h>
#include <sys/stat.h>
#include <sys/proc.h>
#include <sys/mntent.h>  // for MNTTAB
#include <sys/mnttab.h>
#include <fcntl.h>
#include <procfs.h>
#include <utmpx.h>


#define TV2DOUBLE(t)   (((t).tv_nsec * 0.000000001) + (t).tv_sec)


/*
 * Read a file content and fills a C structure with it.
 */
int
_fill_struct_from_file(char *path, void *fstruct, size_t size)
{
	int fd, ret;
	fd = open(path, O_RDONLY);
	if (fd == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        return 0;
	}
	ret = read(fd, fstruct, size);
	if (ret == 1) {
        PyErr_SetFromErrno(PyExc_OSError);
        return 0;
	}
	close(fd);
    return 1;
}


/*
 * Return process ppid, rss, vms, ctime, nice, nthreads, status and tty
 * as a Python tuple.
 */
static PyObject*
get_process_basic_info(PyObject* self, PyObject* args)
{
	int pid;
	char path[100];
	psinfo_t info;

    if (! PyArg_ParseTuple(args, "i", &pid)) {
        return NULL;
    }
    sprintf(path, "/proc/%i/psinfo", pid);
    if (! _fill_struct_from_file(path, (void *)&info, sizeof(info))) {
        return NULL;
    }
    return Py_BuildValue("ikkdiiik",
                         info.pr_ppid,              // parent pid
                         info.pr_rssize,            // rss
                         info.pr_size,              // vms
                         TV2DOUBLE(info.pr_start),  // create time
                         info.pr_lwp.pr_nice,       // nice
                         info.pr_nlwp,              // no. of threads
                         info.pr_lwp.pr_state,      // status code
                         info.pr_ttydev             // tty nr
                         );
}


/*
 * Return process name and args as a Python tuple.
 */
static PyObject*
get_process_name_and_args(PyObject* self, PyObject* args)
{
	int pid;
	char path[100];
	psinfo_t info;

    if (! PyArg_ParseTuple(args, "i", &pid)) {
        return NULL;
    }
    sprintf(path, "/proc/%i/psinfo", pid);
    if (! _fill_struct_from_file(path, (void *)&info, sizeof(info))) {
        return NULL;
    }
    return Py_BuildValue("ss", info.pr_fname,
                               info.pr_psargs);
}


/*
 * Return process user and system CPU times as a Python tuple.
 */
static PyObject*
get_process_cpu_times(PyObject* self, PyObject* args)
{
	int pid;
	char path[100];
	pstatus_t info;

    if (! PyArg_ParseTuple(args, "i", &pid)) {
        return NULL;
    }
    sprintf(path, "/proc/%i/status", pid);
    if (! _fill_struct_from_file(path, (void *)&info, sizeof(info))) {
        return NULL;
    }

    // results are more precise than os.times()
    return Py_BuildValue("dd", TV2DOUBLE(info.pr_utime),
                               TV2DOUBLE(info.pr_stime));
}


/*
 * Return users currently connected on the system.
 */
static PyObject*
get_system_users(PyObject* self, PyObject* args)
{
    PyObject *ret_list = PyList_New(0);
    PyObject *tuple = NULL;
    PyObject *user_proc = NULL;
    struct utmpx *ut;
    int ret;

    while (NULL != (ut = getutxent())) {
        if (ut->ut_type == USER_PROCESS)
            user_proc = Py_True;
        else
            user_proc = Py_False;
        tuple = Py_BuildValue("(sssfO)",
            ut->ut_user,              // username
            ut->ut_line,              // tty
            ut->ut_host,              // hostname
            (float)ut->ut_tv.tv_sec,  // tstamp
            user_proc                 // (bool) user process
        );
        PyList_Append(ret_list, tuple);
        Py_DECREF(tuple);
    }
    endutent();

    return ret_list;
}


/*
 * Return disk mounted partitions as a list of tuples including device,
 * mount point and filesystem type.
 */
static PyObject*
get_disk_partitions(PyObject* self, PyObject* args)
{
    FILE *file;
    struct mnttab mt;
    PyObject* py_retlist = PyList_New(0);
    PyObject* py_tuple;

    file = fopen(MNTTAB, "rb");
    if (file == NULL) {
        return PyErr_SetFromErrno(PyExc_OSError);
    }

    while (getmntent(file, &mt) == 0) {
        py_tuple = Py_BuildValue("(ssss)", mt.mnt_special,  // device
                                           mt.mnt_mountp,     // mount point
                                           mt.mnt_fstype,    // fs type
                                           mt.mnt_mntopts);   // options
        PyList_Append(py_retlist, py_tuple);
        Py_XDECREF(py_tuple);

    }

    return py_retlist;
}


/*
 * define the psutil C module methods and initialize the module.
 */
static PyMethodDef
PsutilMethods[] =
{
     // --- process-related functions

     {"get_process_basic_info", get_process_basic_info, METH_VARARGS,
        "Return process ppid, rss, vms, ctime, nice, nthreads, status and tty"},
     {"get_process_name_and_args", get_process_name_and_args, METH_VARARGS,
        "Return process name and args."},
     {"get_process_cpu_times", get_process_cpu_times, METH_VARARGS,
        "Return process user and system CPU times."},

     // --- system-related functions

     {"get_system_users", get_system_users, METH_VARARGS,
        "Return currently connected users."},
     {"get_disk_partitions", get_disk_partitions, METH_VARARGS,
        "Return disk partitions."},


     {NULL, NULL, 0, NULL}
};


struct module_state {
    PyObject *error;
};

#if PY_MAJOR_VERSION >= 3
#define GETSTATE(m) ((struct module_state*)PyModule_GetState(m))
#else
#define GETSTATE(m) (&_state)
#endif

#if PY_MAJOR_VERSION >= 3

static int
psutil_sunos_traverse(PyObject *m, visitproc visit, void *arg) {
    Py_VISIT(GETSTATE(m)->error);
    return 0;
}

static int
psutil_sunos_clear(PyObject *m) {
    Py_CLEAR(GETSTATE(m)->error);
    return 0;
}

static struct PyModuleDef
moduledef = {
        PyModuleDef_HEAD_INIT,
        "psutil_sunos",
        NULL,
        sizeof(struct module_state),
        PsutilMethods,
        NULL,
        psutil_sunos_traverse,
        psutil_sunos_clear,
        NULL
};

#define INITERROR return NULL

PyObject *
PyInit__psutil_sunos(void)

#else
#define INITERROR return

void init_psutil_sunos(void)
#endif
{
#if PY_MAJOR_VERSION >= 3
    PyObject *module = PyModule_Create(&moduledef);
#else
    PyObject *module = Py_InitModule("_psutil_sunos", PsutilMethods);
#endif
    PyModule_AddIntConstant(module, "SSLEEP", SSLEEP);
    PyModule_AddIntConstant(module, "SRUN", SRUN);
    PyModule_AddIntConstant(module, "SZOMB", SZOMB);
    PyModule_AddIntConstant(module, "SSTOP", SSTOP);
    PyModule_AddIntConstant(module, "SIDL", SIDL);
    PyModule_AddIntConstant(module, "SONPROC", SONPROC);
    PyModule_AddIntConstant(module, "SWAIT", SWAIT);

    PyModule_AddIntConstant(module, "PRNODEV", PRNODEV);  // for process tty

    if (module == NULL) {
        INITERROR;
    }
#if PY_MAJOR_VERSION >= 3
    return module;
#endif
}
