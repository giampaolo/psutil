/*
 * Copyright (c) 2009, Giampaolo Rodola'
 * Copyright (c) 2017, Arnon Yaari
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

/*
 * AIX support is experimental at this time.
 * The following functions and methods are unsupported on the AIX platform:
 * - psutil.Process.memory_maps
 *
 * Known limitations:
 * - psutil.Process.io_counters read count is always 0
 * - psutil.Process.threads may not be available on older AIX versions
 * - reading basic process info may fail or return incorrect values when
 *   process is starting (see IBM APAR IV58499 - fixed in newer AIX versions)
 * - sockets and pipes may not be counted in num_fds (fixed in newer AIX
 *    versions)
 *
 * Useful resources:
 * - proc filesystem: http://www-01.ibm.com/support/knowledgecenter/
 *       ssw_aix_61/com.ibm.aix.files/proc.htm
 * - libperfstat: http://www-01.ibm.com/support/knowledgecenter/
 *       ssw_aix_61/com.ibm.aix.files/libperfstat.h.htm
 */

#include <Python.h>

#include <sys/types.h>
#include <sys/stat.h>
#include <sys/proc.h>
#include <sys/sysinfo.h>
#include <sys/procfs.h>
#include <sys/socket.h>
#include <sys/thread.h>
#include <fcntl.h>
#include <utmp.h>
#include <utmpx.h>
#include <mntent.h>
#include <sys/ioctl.h>
#include <sys/tihdr.h>
#include <stropts.h>
#include <netinet/tcp_fsm.h>
#include <arpa/inet.h>
#include <net/if.h>
#include <procinfo.h>
#include <sys/types.h>
#include <sys/core.h>
#include <unistd.h>

#include "_psutil_common.h"
#include "_psutil_posix.h"


#define TV2DOUBLE(t)   (((t).tv_nsec * 0.000000001) + (t).tv_sec)


struct procentry64 *
psutil_get_proc(struct procentry64* dest, int pid) {
    int pid_in_table = pid;
    int rtv = getprocs64(dest, 
                        sizeof(struct procentry64),
                        NULL,
                        0,
                        &pid_in_table,
                        1);
    if( 0 >= rtv ||dest->pi_pid != pid) {
        printf("process %d is gone\n", pid);
        errno = ENOENT;
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    return dest;
}


struct procentry64 *
psutil_read_process_table_i(int * num) {
    size_t msz;
    pid32_t pid = 0;
    int procinfo_incr = 256;
    struct procentry64 *processes = (struct procentry64 *)NULL;
    struct procentry64 *p;
    int Np = 0;          /* number of processes allocated in 'processes' */
    int np = 0;          /* number of processes read into 'processes' */
    int i;               /* number of processes read in current iteration */

    msz = (size_t)(sizeof(struct procentry64) * 256);
    processes = (struct procentry64 *)malloc(msz);
    if (!processes) {
        PyErr_NoMemory();
        return NULL;
    }
    Np = 256;
    p = processes;
    while ((i = getprocs64(p, sizeof(struct procentry64), (struct fdsinfo64 *)NULL, 0, &pid,
                 procinfo_incr))
    == procinfo_incr) {
        np += procinfo_incr;
        if (np >= Np) {
            msz = (size_t)(sizeof(struct procentry64) * (Np + procinfo_incr));
            processes = (struct procentry64 *)realloc((char *)processes, msz);
            if (!processes) {
                PyErr_NoMemory();
                return NULL;
            }
            Np += procinfo_incr;
        }
        p = (struct procentry64 *)((char *)processes + (np * sizeof(struct procentry64)));
    }

    /* add the number of processes read in the last iteration */
    if (i > 0)
        np += i;

    *num = np;
    return processes;
}

/*
 * Read a file content and fills a C structure with it.
 */
int
psutil_file_to_struct(char *path, void *fstruct, size_t size) {
    int fd;
    size_t nbytes;
    fd = open(path, O_RDONLY);
    if (fd == -1) {
        PyErr_SetFromErrnoWithFilename(PyExc_OSError, path);
        return 0;
    }
    nbytes = read(fd, fstruct, size);
    if (nbytes <= 0) {
        close(fd);
        PyErr_SetFromErrno(PyExc_OSError);
        return 0;
    }
    if (nbytes != size) {
        close(fd);
        PyErr_SetString(PyExc_RuntimeError, "structure size mismatch");
        return 0;
    }
    close(fd);
    return nbytes;
}


/*
 * Return process ppid, rss, vms, ctime, nice, nthreads, status and tty
 * as a Python tuple.
 */
static PyObject *
psutil_proc_basic_info(PyObject *self, PyObject *args) {

    int pid;
    psinfo_t info;

    if (! PyArg_ParseTuple(args, "i", &pid))
        return NULL;
    struct procentry64 proc_info;
    if(NULL == psutil_get_proc(&proc_info, pid)) {
        return NULL;
    }
    return Py_BuildValue("KKKdiiiK",
        (unsigned long long) proc_info.pi_ppid, // parent pid
        (unsigned long long) proc_info.pi_drss + proc_info.pi_trss, // rss
        (unsigned long long) proc_info.pi_dvm,  // vms
        (double)proc_info.pi_start, // create time
        (int) proc_info.pi_nice,                // nice
        (int) proc_info.pi_thcount,             // no. of threads
        (int) proc_info.pi_state,                                // status code TODO
        (unsigned long long)info.pr_ttydev      // tty nr (always zero for some reason, should investigate)
        );
}


/*
 * Return process name and args as a Python tuple.
 */
static PyObject *
psutil_proc_name_and_args(PyObject *self, PyObject *args) {
    int pid;
    char path[100];
    psinfo_t info;
    PyObject *py_name = NULL;
    PyObject *py_args = NULL;
    if (! PyArg_ParseTuple(args, "i", &pid))
        return NULL;
    struct procentry64 proc_info;
    if(NULL == psutil_get_proc(&proc_info, pid)) {
        return NULL;
    }
    char arglist[1028*4];

    int rc = getargs(&proc_info,
                     sizeof(struct procentry64),
                    &arglist,
                    sizeof(arglist) );
    if(rc != 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    PyObject *py_retlist = PyList_New(0);
    char* cur = arglist;
    int len = 0;
    while(0 != (len = strlen(cur))) {
        PyList_Append(py_retlist, Py_BuildValue("s", cur));
        cur += (1+len);
    }
    return py_retlist;
}


/*
 * Retrieves all threads used by process returning a list of tuples
 * including thread id, user time and system time.
 */
static PyObject *
psutil_proc_threads(PyObject *self, PyObject *args) {
    long pid;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;

    if (py_retlist == NULL)
        return NULL;
    if (! PyArg_ParseTuple(args, "l", &pid))
        return NULL;
    struct thrdentry64 thd_buf[1024];
    tid64_t start = 0;
    int thread_count = getthrds64(   pid,
                            &thd_buf,
                            sizeof(struct thrdentry64),
                            &start,
                            102
    );
    if (thread_count <= 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    for (int i = 0; i < thread_count; i++) {
        py_tuple = Py_BuildValue("Idd",
                                 thd_buf[i].ti_tid,
                                 thd_buf[i].ti_cpu,
                                 0);
        PyList_Append(py_retlist, py_tuple);
        Py_DECREF(py_tuple);
    }

    return py_retlist;
}

/*
 * Return process user and system CPU times as a Python tuple.
 */
static PyObject *
psutil_proc_cpu_times(PyObject *self, PyObject *args) {
    int pid;
    char path[100];
    pstatus_t info;

    if (! PyArg_ParseTuple(args, "i", &pid))
        return NULL;
    memset(&info, 0x00, sizeof(pstatus_t)); // TODO
    return Py_BuildValue("dddd",
                         TV2DOUBLE(info.pr_utime),
                         TV2DOUBLE(info.pr_stime),
                         TV2DOUBLE(info.pr_cutime),
                         TV2DOUBLE(info.pr_cstime));
}


/*
 * Return process uids/gids as a Python tuple.
 */
static PyObject *
psutil_proc_cred(PyObject *self, PyObject *args) {
    int pid;
    char path[100];
    prcred_t info;

    if (! PyArg_ParseTuple(args, "i", &pid))
        return NULL;
    struct procentry64 proc_info;
    if(NULL == psutil_get_proc(&proc_info, pid)) {
        return NULL;
    }
    return Py_BuildValue("iiiiii",
                         proc_info.pi_uid, proc_info.pi_uid, proc_info.pi_suid,
                        0,0,0);
}


/*
 * Return process voluntary and involuntary context switches as a Python tuple.
 */
static PyObject *
psutil_proc_num_ctx_switches(PyObject *self, PyObject *args) {
    PyObject *py_tuple = NULL;
    pid32_t requested_pid;
    pid32_t pid = 0;
    int np = 0;
    struct procentry64 *processes = (struct procentry64 *)NULL;
    struct procentry64 *p;

    if (! PyArg_ParseTuple(args, "i", &requested_pid))
        return NULL;

    processes = psutil_read_process_table_i(&np);
    if (!processes)
        return NULL;

    /* Loop through processes */
    for (p = processes; np > 0; np--, p++) {
        pid = p->pi_pid;
        if (requested_pid != pid)
            continue;
        py_tuple = Py_BuildValue("LL",
            (long long) p->pi_ru.ru_nvcsw,    /* voluntary context switches */
            (long long) p->pi_ru.ru_nivcsw);  /* involuntary */
        free(processes);
        return py_tuple;
    }

    /* finished iteration without finding requested pid */
    free(processes);
    return NoSuchProcess("");
}

/*
 * Return disk mounted partitions as a list of tuples including device,
 * mount point and filesystem type.
 */
static PyObject *
psutil_disk_partitions(PyObject *self, PyObject *args) {
    FILE *file = NULL;
    struct mntent * mt = NULL;
    PyObject *py_dev = NULL;
    PyObject *py_mountp = NULL;
    PyObject *py_tuple = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;

    file = setmntent(MNTTAB, "rb");
    if (file == NULL) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }
    mt = getmntent(file);
    while (mt != NULL) {
        py_dev = PyUnicode_DecodeFSDefault(mt->mnt_fsname);
        if (! py_dev)
            goto error;
        py_mountp = PyUnicode_DecodeFSDefault(mt->mnt_dir);
        if (! py_mountp)
            goto error;
        py_tuple = Py_BuildValue(
            "(OOss)",
            py_dev,         // device
            py_mountp,      // mount point
            mt->mnt_type,   // fs type
            mt->mnt_opts);  // options
        if (py_tuple == NULL)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_DECREF(py_dev);
        Py_DECREF(py_mountp);
        Py_DECREF(py_tuple);
        mt = getmntent(file);
    }
    endmntent(file);
    return py_retlist;

error:
    Py_XDECREF(py_dev);
    Py_XDECREF(py_mountp);
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    if (file != NULL)
        endmntent(file);
    return NULL;
}

/*
 * Return a list of process identifiers
 */
static PyObject *
psutil_list_pids(PyObject *self, PyObject *args) {
    PyObject *py_retdict = PyTuple_New(0);
    struct procentry64 proc_info[128];
    int rtv = 0;
    pid_t pid_idx = 0;
    int tuple_idx = 0;
    while(0 < (rtv = getprocs64(&proc_info, sizeof(struct procentry64), NULL, 0,&pid_idx, 128))) {
        _PyTuple_Resize(&py_retdict, PyTuple_Size(py_retdict)+rtv);
        for(int i = 0; i < rtv; i++) {
            pid_t cur_pid = proc_info[i].pi_pid;
            pid_idx = 1 + cur_pid;
            PyTuple_SetItem(py_retdict, tuple_idx++, Py_BuildValue("K",cur_pid));
        }
    }
    return py_retdict;
}
/*
 * Return total number of CPUs
 */
static PyObject *
psutil_cpu_count(PyObject *self, PyObject *args) {
    return Py_BuildValue("i",sysconf(_SC_NPROCESSORS_CONF));
}
/*
 * Return number of current CPUs online
 */
static PyObject *
psutil_cpu_count_online(PyObject *self, PyObject *args) {
    return Py_BuildValue("i",sysconf(_SC_NPROCESSORS_ONLN));
}

/*
 * define the psutil C module methods and initialize the module.
 */
static PyMethodDef
PsutilMethods[] =
{
    // --- process-related functions
    {"proc_basic_info", psutil_proc_basic_info, METH_VARARGS,
     "Return process ppid, rss, vms, ctime, nice, nthreads, status and tty"},
    {"proc_name_and_args", psutil_proc_name_and_args, METH_VARARGS,
     "Return process name and args."},
    {"proc_cpu_times", psutil_proc_cpu_times, METH_VARARGS,
     "Return process user and system CPU times."},
    {"proc_cred", psutil_proc_cred, METH_VARARGS,
     "Return process uids/gids."}, 
    {"proc_threads", psutil_proc_threads, METH_VARARGS,
     "Return process threads"},
    {"proc_num_ctx_switches", psutil_proc_num_ctx_switches, METH_VARARGS,
     "Get process I/O counters."},

    // --- system-related functions
    {"disk_partitions", psutil_disk_partitions, METH_VARARGS,
     "Return disk partitions."},
    {"list_pids", psutil_list_pids, METH_NOARGS,
    "Get a tuple of all running process identifiers"},
    {"cpu_count", psutil_cpu_count, METH_NOARGS,
    "Get a count of total CPUs"},
    {"cpu_count_online", psutil_cpu_count, METH_NOARGS,
    "Get a count of the number of online CPUs"},
    // --- others
    {"set_testing", psutil_set_testing, METH_NOARGS,
     "Set psutil in testing mode"},
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

#ifdef __cplusplus
extern "C" {
#endif

#if PY_MAJOR_VERSION >= 3

static int
psutil_aix_traverse(PyObject *m, visitproc visit, void *arg) {
    Py_VISIT(GETSTATE(m)->error);
    return 0;
}

static int
psutil_aix_clear(PyObject *m) {
    Py_CLEAR(GETSTATE(m)->error);
    return 0;
}

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "psutil_ibmi",
    NULL,
    sizeof(struct module_state),
    PsutilMethods,
    NULL,
    psutil_aix_traverse,
    psutil_aix_clear,
    NULL
};

#define INITERROR return NULL

PyMODINIT_FUNC PyInit__psutil_ibmi(void)

#else
#define INITERROR return

void init_psutil_ibmi(void)
#endif
{
#if PY_MAJOR_VERSION >= 3
    PyObject *module = PyModule_Create(&moduledef);
#else
    PyObject *module = Py_InitModule("_psutil_ibmi", PsutilMethods);
#endif
    PyModule_AddIntConstant(module, "version", PSUTIL_VERSION);

    PyModule_AddIntConstant(module, "SIDL", SIDL);
    PyModule_AddIntConstant(module, "SZOMB", SZOMB);
    PyModule_AddIntConstant(module, "SACTIVE", SACTIVE);
    PyModule_AddIntConstant(module, "SSWAP", SSWAP);
    PyModule_AddIntConstant(module, "SSTOP", SSTOP);

    PyModule_AddIntConstant(module, "TCPS_CLOSED", TCPS_CLOSED);
    PyModule_AddIntConstant(module, "TCPS_CLOSING", TCPS_CLOSING);
    PyModule_AddIntConstant(module, "TCPS_CLOSE_WAIT", TCPS_CLOSE_WAIT);
    PyModule_AddIntConstant(module, "TCPS_LISTEN", TCPS_LISTEN);
    PyModule_AddIntConstant(module, "TCPS_ESTABLISHED", TCPS_ESTABLISHED);
    PyModule_AddIntConstant(module, "TCPS_SYN_SENT", TCPS_SYN_SENT);
    PyModule_AddIntConstant(module, "TCPS_SYN_RCVD", TCPS_SYN_RECEIVED);
    PyModule_AddIntConstant(module, "TCPS_FIN_WAIT_1", TCPS_FIN_WAIT_1);
    PyModule_AddIntConstant(module, "TCPS_FIN_WAIT_2", TCPS_FIN_WAIT_2);
    PyModule_AddIntConstant(module, "TCPS_LAST_ACK", TCPS_LAST_ACK);
    PyModule_AddIntConstant(module, "TCPS_TIME_WAIT", TCPS_TIME_WAIT);
    PyModule_AddIntConstant(module, "PSUTIL_CONN_NONE", PSUTIL_CONN_NONE);

    psutil_setup();

    if (module == NULL)
        INITERROR;
#if PY_MAJOR_VERSION >= 3
    return module;
#endif
}

#ifdef __cplusplus
}
#endif
