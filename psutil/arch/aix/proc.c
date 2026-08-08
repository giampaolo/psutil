/*
 * Copyright (c) 2009, Giampaolo Rodola'
 * Copyright (c) 2017, Arnon Yaari
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <fcntl.h>
#include <procinfo.h>
#include <stdlib.h>
#include <sys/limits.h>
#include <sys/proc.h>
#include <sys/procfs.h>
#include <libperfstat.h>
#include <unistd.h>

#include "../../arch/all/init.h"
#include "init.h"


#define TV2DOUBLE(t) (((t).tv_nsec * 0.000000001) + (t).tv_sec)

// Read a file content and fills a C structure with it.
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
        psutil_oserror();
        return 0;
    }
    if (nbytes != size) {
        close(fd);
        psutil_runtime_error("psutil_file_to_struct() size mismatch");
        return 0;
    }
    close(fd);
    return nbytes;
}


struct procentry64 *
psutil_read_process_table(int *num) {
    size_t msz;
    pid32_t pid = 0;
    struct procentry64 *processes = (struct procentry64 *)NULL;
    struct procentry64 *p;
    int Np = 0;  // number of processes allocated in 'processes'
    int np = 0;  // number of processes read into 'processes'
    int i;  // number of processes read in current iteration

    msz = (size_t)(PROCSIZE * PROCINFO_INCR);
    processes = (struct procentry64 *)malloc(msz);
    if (!processes) {
        PyErr_NoMemory();
        return NULL;
    }
    Np = PROCINFO_INCR;
    p = processes;
    for (;;) {
        Py_BEGIN_ALLOW_THREADS
        i = getprocs64(
            p, PROCSIZE, (struct fdsinfo64 *)NULL, 0, &pid, PROCINFO_INCR
        );
        Py_END_ALLOW_THREADS
        if (i != PROCINFO_INCR)
            break;
        np += PROCINFO_INCR;
        if (np >= Np) {
            msz = (size_t)(PROCSIZE * (Np + PROCINFO_INCR));
            processes = (struct procentry64 *)realloc((char *)processes, msz);
            if (!processes) {
                PyErr_NoMemory();
                return NULL;
            }
            Np += PROCINFO_INCR;
        }
        p = (struct procentry64 *)((char *)processes + (np * PROCSIZE));
    }

    // add the number of processes read in the last iteration
    if (i > 0)
        np += i;

    *num = np;
    return processes;
}


// Return process ppid, rss, vms, ctime, nice, nthreads, status and tty
// as a Python tuple.
PyObject *
psutil_proc_oneshot(PyObject *self, PyObject *args) {
    int pid;
    char path[100];
    psinfo_t info;
    pstatus_t status;
    const char *procfs_path;

    if (!PyArg_ParseTuple(args, "is", &pid, &procfs_path))
        return NULL;

    str_format(path, sizeof(path), "%s/%i/psinfo", procfs_path, pid);
    if (!psutil_file_to_struct(path, (void *)&info, sizeof(info)))
        return NULL;

    if (info.pr_nlwp == 0 && info.pr_lwp.pr_lwpid == 0) {
        // From the /proc docs: "If the process is a zombie, the pr_nlwp
        // and pr_lwp.pr_lwpid flags are zero."
        status.pr_stat = SZOMB;
    }
    else if (info.pr_flag & SEXIT) {
        // "exiting" processes don't have /proc/<pid>/status
        // There are other "exiting" processes that 'ps' shows as "active"
        status.pr_stat = SACTIVE;
    }
    else {
        str_format(path, sizeof(path), "%s/%i/status", procfs_path, pid);
        if (!psutil_file_to_struct(path, (void *)&status, sizeof(status)))
            return NULL;
    }

    return Py_BuildValue(
        "KKKdiiiK",
        (unsigned long long)info.pr_ppid,  // parent pid
        (unsigned long long)info.pr_rssize,  // rss
        (unsigned long long)info.pr_size,  // vms
        TV2DOUBLE(info.pr_start),  // create time
        (int)info.pr_lwp.pr_nice,  // nice
        (int)info.pr_nlwp,  // no. of threads
        (int)status.pr_stat,  // status code
        (unsigned long long)info.pr_ttydev  // tty nr
    );
}


PyObject *
psutil_proc_name(PyObject *self, PyObject *args) {
    int pid;
    char path[100];
    psinfo_t info;
    const char *procfs_path;

    if (!PyArg_ParseTuple(args, "is", &pid, &procfs_path))
        return NULL;
    str_format(path, sizeof(path), "%s/%i/psinfo", procfs_path, pid);
    if (!psutil_file_to_struct(path, (void *)&info, sizeof(info)))
        return NULL;

    return PyUnicode_DecodeFSDefaultAndSize(info.pr_fname, PRFNSZ);
}


// Return process command line arguments as a Python list
PyObject *
psutil_proc_args(PyObject *self, PyObject *args) {
    int pid;
    PyObject *py_retlist = PyList_New(0);
    struct procsinfo procbuf;
    long arg_max;
    char *argbuf = NULL;
    char *curarg = NULL;
    int ret;

    if (py_retlist == NULL)
        return NULL;
    if (!PyArg_ParseTuple(args, "i", &pid))
        goto error;
    arg_max = sysconf(_SC_ARG_MAX);
    argbuf = malloc(arg_max);
    if (argbuf == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    procbuf.pi_pid = pid;
    ret = getargs(&procbuf, sizeof(procbuf), argbuf, ARG_MAX);
    if (ret == -1) {
        psutil_oserror();
        goto error;
    }

    curarg = argbuf;
    // getargs will always append an extra NULL to end the arg list,
    // even if the buffer is not big enough (even though it is supposed
    // to be) so the following 'while' is safe
    while (*curarg != '\0') {
        if (!pylist_append_obj(py_retlist, PyUnicode_DecodeFSDefault(curarg)))
            goto error;
        curarg = strchr(curarg, '\0') + 1;
    }

    free(argbuf);

    return py_retlist;

error:
    if (argbuf != NULL)
        free(argbuf);
    Py_XDECREF(py_retlist);
    return NULL;
}


PyObject *
psutil_proc_environ(PyObject *self, PyObject *args) {
    int pid;
    PyObject *py_retdict = PyDict_New();
    PyObject *py_key = NULL;
    PyObject *py_val = NULL;
    struct procsinfo procbuf;
    long env_max;
    char *envbuf = NULL;
    char *curvar = NULL;
    char *separator = NULL;
    int ret;

    if (py_retdict == NULL)
        return NULL;
    if (!PyArg_ParseTuple(args, "i", &pid))
        goto error;
    env_max = sysconf(_SC_ARG_MAX);
    envbuf = malloc(env_max);
    if (envbuf == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    procbuf.pi_pid = pid;
    ret = getevars(&procbuf, sizeof(procbuf), envbuf, ARG_MAX);
    if (ret == -1) {
        psutil_oserror();
        goto error;
    }

    curvar = envbuf;
    // getevars will always append an extra NULL to end the arg list,
    // even if the buffer is not big enough (even though it is supposed
    // to be) so the following 'while' is safe
    while (*curvar != '\0') {
        separator = strchr(curvar, '=');
        if (separator != NULL) {
            py_key = PyUnicode_DecodeFSDefaultAndSize(
                curvar, (Py_ssize_t)(separator - curvar)
            );
            if (!py_key)
                goto error;
            py_val = PyUnicode_DecodeFSDefault(separator + 1);
            if (!py_val)
                goto error;
            if (PyDict_SetItem(py_retdict, py_key, py_val))
                goto error;
            Py_CLEAR(py_key);
            Py_CLEAR(py_val);
        }
        curvar = strchr(curvar, '\0') + 1;
    }

    free(envbuf);

    return py_retdict;

error:
    if (envbuf != NULL)
        free(envbuf);
    Py_XDECREF(py_retdict);
    Py_XDECREF(py_key);
    Py_XDECREF(py_val);
    return NULL;
}


#ifdef CURR_VERSION_THREAD
PyObject *
psutil_proc_threads(PyObject *self, PyObject *args) {
    long pid;
    PyObject *py_retlist = PyList_New(0);
    perfstat_thread_t *threadt = NULL;
    perfstat_id_t id;
    int i, rc, thread_count;

    if (py_retlist == NULL)
        return NULL;
    if (!PyArg_ParseTuple(args, "l", &pid))
        goto error;

    // Get the count of threads
    thread_count = perfstat_thread(NULL, NULL, sizeof(perfstat_thread_t), 0);
    if (thread_count <= 0) {
        psutil_oserror();
        goto error;
    }

    // Allocate enough memory
    threadt = (perfstat_thread_t *)calloc(
        thread_count, sizeof(perfstat_thread_t)
    );
    if (threadt == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    strcpy(id.name, "");
    rc = perfstat_thread(
        &id, threadt, sizeof(perfstat_thread_t), thread_count
    );
    if (rc <= 0) {
        psutil_oserror();
        goto error;
    }

    for (i = 0; i < thread_count; i++) {
        if (threadt[i].pid != pid)
            continue;

        if (!pylist_append_fmt(
                py_retlist,
                "Idd",
                threadt[i].tid,
                threadt[i].ucpu_time,
                threadt[i].scpu_time
            ))
        {
            goto error;
        }
    }
    free(threadt);
    return py_retlist;

error:
    Py_DECREF(py_retlist);
    if (threadt != NULL)
        free(threadt);
    return NULL;
}
#endif  // CURR_VERSION_THREAD


#ifdef CURR_VERSION_PROCESS
PyObject *
psutil_proc_io_counters(PyObject *self, PyObject *args) {
    long pid;
    int rc;
    perfstat_process_t procinfo;
    perfstat_id_t id;
    if (!PyArg_ParseTuple(args, "l", &pid))
        return NULL;

    snprintf(id.name, sizeof(id.name), "%ld", pid);
    rc = perfstat_process(&id, &procinfo, sizeof(perfstat_process_t), 1);
    if (rc <= 0) {
        psutil_oserror();
        return NULL;
    }

    return Py_BuildValue(
        "(KKKK)",
        procinfo.inOps,  // XXX always 0
        procinfo.outOps,
        procinfo.inBytes,  // XXX always 0
        procinfo.outBytes
    );
}
#endif  // CURR_VERSION_PROCESS


PyObject *
psutil_proc_cpu_times(PyObject *self, PyObject *args) {
    int pid;
    char path[100];
    pstatus_t info;
    const char *procfs_path;

    if (!PyArg_ParseTuple(args, "is", &pid, &procfs_path))
        return NULL;
    str_format(path, sizeof(path), "%s/%i/status", procfs_path, pid);
    if (!psutil_file_to_struct(path, (void *)&info, sizeof(info)))
        return NULL;
    // results are more precise than os.times()
    return Py_BuildValue(
        "dddd",
        TV2DOUBLE(info.pr_utime),
        TV2DOUBLE(info.pr_stime),
        TV2DOUBLE(info.pr_cutime),
        TV2DOUBLE(info.pr_cstime)
    );
}


// Return process uids/gids as a Python tuple.
PyObject *
psutil_proc_cred(PyObject *self, PyObject *args) {
    int pid;
    char path[100];
    prcred_t info;
    const char *procfs_path;

    if (!PyArg_ParseTuple(args, "is", &pid, &procfs_path))
        return NULL;
    str_format(path, sizeof(path), "%s/%i/cred", procfs_path, pid);
    if (!psutil_file_to_struct(path, (void *)&info, sizeof(info)))
        return NULL;
    return Py_BuildValue(
        "iiiiii",
        info.pr_ruid,
        info.pr_euid,
        info.pr_suid,
        info.pr_rgid,
        info.pr_egid,
        info.pr_sgid
    );
}


PyObject *
psutil_proc_num_ctx_switches(PyObject *self, PyObject *args) {
    PyObject *py_tuple = NULL;
    pid32_t requested_pid;
    pid32_t pid = 0;
    int np = 0;
    struct procentry64 *processes = (struct procentry64 *)NULL;
    struct procentry64 *p;

    if (!PyArg_ParseTuple(args, "i", &requested_pid))
        return NULL;

    processes = psutil_read_process_table(&np);
    if (!processes)
        return NULL;

    // Loop through processes
    for (p = processes; np > 0; np--, p++) {
        pid = p->pi_pid;
        if (requested_pid != pid)
            continue;
        py_tuple = Py_BuildValue(
            "LL",
            (long long)p->pi_ru.ru_nvcsw,  // voluntary
            (long long)p->pi_ru.ru_nivcsw  // involuntary
        );
        free(processes);
        return py_tuple;
    }

    // finished iteration without finding requested pid
    free(processes);
    return psutil_oserror_nsp("psutil_read_process_table (no PID found)");
}
