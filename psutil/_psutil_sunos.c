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
#include <sys/sysinfo.h>
#include <sys/mntent.h>  // for MNTTAB
#include <sys/mnttab.h>
#include <fcntl.h>
#include <procfs.h>
#include <utmpx.h>
#include <kstat.h>

// #include "_psutil_bsd.h"  TODO fix warnings


#define TV2DOUBLE(t)   (((t).tv_nsec * 0.000000001) + (t).tv_sec)


/*
 * Read a file content and fills a C structure with it.
 */
int
_fill_struct_from_file(char *path, void *fstruct, size_t size)
{
    int fd;
    size_t nbytes;
	fd = open(path, O_RDONLY);
	if (fd == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
	}
	nbytes = read(fd, fstruct, size);
	if (nbytes == 1) {
    	close(fd);
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
	}
	if (nbytes != size) {
    	close(fd);
        PyErr_SetString(PyExc_RuntimeError, "structure size mismatch");
        return NULL;
	}
	close(fd);
    return nbytes;
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
 * Return process uids/gids as a Python tuple.
 */
static PyObject*
get_process_cred(PyObject* self, PyObject* args)
{
	int pid;
	char path[100];
	prcred_t info;

    if (! PyArg_ParseTuple(args, "i", &pid)) {
        return NULL;
    }
    sprintf(path, "/proc/%i/cred", pid);
    if (! _fill_struct_from_file(path, (void *)&info, sizeof(info))) {
        return NULL;
    }

    return Py_BuildValue("iiiiii", info.pr_ruid, info.pr_euid, info.pr_suid,
                                   info.pr_rgid, info.pr_egid, info.pr_sgid);
}


/*
 * Return information about a given process thread.
 */
static PyObject*
query_process_thread(PyObject* self, PyObject* args)
{
	int tid;
	char path[100];
	lwpstatus_t info;

    if (! PyArg_ParseTuple(args, "i", &tid)) {
        return NULL;
    }
    sprintf(path, "/proc/%i/lwp/1/lwpstatus", tid);
    if (! _fill_struct_from_file(path, (void *)&info, sizeof(info))) {
        return NULL;
    }

    return Py_BuildValue("dd", TV2DOUBLE(info.pr_utime),
                               TV2DOUBLE(info.pr_stime));
}


/*
 * Return information about system virtual memory.
 * XXX - not sure how to test this; "swap -s" shows different values.
 */
static PyObject*
get_system_virtmem(PyObject* self, PyObject* args)
{
    kstat_ctl_t *kc;
    kstat_t *ksp;
    vminfo_t vm;
    uint64_t free, used;

    free = 0; used = 0;
    kc = kstat_open();
    if (kc == NULL) {
        return PyErr_SetFromErrno(PyExc_OSError);;
    }

    ksp = kc->kc_chain;
    while (ksp != NULL) {
        if (ksp->ks_type == KSTAT_TYPE_RAW) {
            if (strcmp(ksp->ks_class, "vm") == 0) {
                if (kstat_read(kc, ksp, &vm) == -1) {
                    kstat_close(kc);
                    return PyErr_SetFromErrno(PyExc_OSError);;
                }
                free += vm.swap_free;
                used += (vm.swap_alloc + vm.swap_resv);
            }
        }
        ksp = ksp->ks_next;
    }
    kstat_close(kc);
    return Py_BuildValue("KK", free, used);
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
 * Return system-wide CPU times.
 */
static PyObject*
get_system_per_cpu_times(PyObject* self, PyObject* args)
{
    kstat_ctl_t *kc;
    kstat_t *ksp;
    cpu_stat_t cs;
    int numcpus;
    int i;
    PyObject* py_retlist = PyList_New(0);
    PyObject* py_cputime;

    kc = kstat_open();
    if (kc == NULL) {
        return PyErr_SetFromErrno(PyExc_OSError);;
    }

    numcpus = sysconf(_SC_NPROCESSORS_ONLN) - 1;
    for (i=0; i<=numcpus; i++) {
        ksp = kstat_lookup(kc, "cpu_stat", i, NULL);
        if (ksp == NULL) {
            kstat_close(kc);
            return PyErr_SetFromErrno(PyExc_OSError);;
        }
	    if (kstat_read(kc, ksp, &cs) == -1) {
		    kstat_close(kc);
            return PyErr_SetFromErrno(PyExc_OSError);;
	    }
        py_cputime = Py_BuildValue("IIII",
                                   cs.cpu_sysinfo.cpu[CPU_USER],
                                   cs.cpu_sysinfo.cpu[CPU_KERNEL],
                                   cs.cpu_sysinfo.cpu[CPU_IDLE],
                                   cs.cpu_sysinfo.cpu[CPU_WAIT]);
        PyList_Append(py_retlist, py_cputime);
        Py_XDECREF(py_cputime);
    }

    kstat_close(kc);
    return py_retlist;
}


/*
 * Return disk IO statistics.
 */
static PyObject*
get_disk_io_counters(PyObject* self, PyObject* args)
{
    kstat_ctl_t *kc;
    kstat_t *ksp;
    kstat_io_t kio;
    PyObject* py_retdict = PyDict_New();
    PyObject* py_disk_info;

    kc = kstat_open();
    if (kc == NULL) {
        return PyErr_SetFromErrno(PyExc_OSError);;
    }
    ksp = kc->kc_chain;
    while (ksp != NULL) {
        if (ksp->ks_type == KSTAT_TYPE_IO) {
            if (strcmp(ksp->ks_class, "disk") == 0) {
                if (kstat_read(kc, ksp, &kio) == -1) {
                    kstat_close(kc);
                    return PyErr_SetFromErrno(PyExc_OSError);;
                }
                py_disk_info = Py_BuildValue("(IIKKLL)",
                                             kio.reads,
                                             kio.writes,
                                             kio.nread,
                                             kio.nwritten,
                                             kio.rtime,  // XXX are these ms?
                                             kio.wtime   // XXX are these ms?
                                             );
                PyDict_SetItemString(py_retdict, ksp->ks_name, py_disk_info);
                Py_XDECREF(py_disk_info);
            }
        }
        ksp = ksp->ks_next;
    }
    kstat_close(kc);

    return py_retdict;
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
     {"get_process_cred", get_process_cred, METH_VARARGS,
        "Return process uids/gids."},
     {"query_process_thread", query_process_thread, METH_VARARGS,
        "Return info about a process thread"},

     // --- system-related functions

     {"get_system_virtmem", get_system_virtmem, METH_VARARGS,
        "Return information about system virtual memory."},
     {"get_system_users", get_system_users, METH_VARARGS,
        "Return currently connected users."},
     {"get_disk_partitions", get_disk_partitions, METH_VARARGS,
        "Return disk partitions."},
     {"get_system_per_cpu_times", get_system_per_cpu_times, METH_VARARGS,
        "Return system per-CPU times."},
     {"get_disk_io_counters", get_disk_io_counters, METH_VARARGS,
        "Return a Python dict of tuples for disk I/O statistics."},

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
