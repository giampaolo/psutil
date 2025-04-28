/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

#include <fcntl.h>
#include <libproc.h>

#include "../../arch/all/init.h"
#include "proc.h"
#include "environ.h"


// Read a file content and fills a C structure with it.
int
psutil_file_to_struct(char *path, void *fstruct, size_t size) {
    int fd;
    ssize_t nbytes;
    fd = open(path, O_RDONLY);
    if (fd == -1) {
        PyErr_SetFromErrnoWithFilename(PyExc_OSError, path);
        return 0;
    }
    nbytes = read(fd, fstruct, size);
    if (nbytes == -1) {
        close(fd);
        PyErr_SetFromErrno(PyExc_OSError);
        return 0;
    }
    if (nbytes != (ssize_t) size) {
        close(fd);
        PyErr_SetString(
            PyExc_RuntimeError, "read() file structure size mismatch");
        return 0;
    }
    close(fd);
    return nbytes;
}


/*
 * Return process ppid, rss, vms, ctime, nice, nthreads, status and tty
 * as a Python tuple.
 */
PyObject *
psutil_proc_basic_info(PyObject *self, PyObject *args) {
    int pid;
    char path[1000];
    psinfo_t info;
    const char *procfs_path;

    if (! PyArg_ParseTuple(args, "is", &pid, &procfs_path))
        return NULL;

    sprintf(path, "%s/%i/psinfo", procfs_path, pid);
    if (! psutil_file_to_struct(path, (void *)&info, sizeof(info)))
        return NULL;
    return Py_BuildValue(
        "ikkdiiikiiii",
        info.pr_ppid,              // parent pid
        info.pr_rssize,            // rss
        info.pr_size,              // vms
        PSUTIL_TV2DOUBLE(info.pr_start),  // create time
        info.pr_lwp.pr_nice,       // nice
        info.pr_nlwp,              // no. of threads
        info.pr_lwp.pr_state,      // status code
        info.pr_ttydev,            // tty nr
        (int)info.pr_uid,          // real user id
        (int)info.pr_euid,         // effective user id
        (int)info.pr_gid,          // real group id
        (int)info.pr_egid          // effective group id
        );
}


/*
 * Join array of C strings to C string with delimiter dm.
 * Omit empty records.
 */
static int
cstrings_array_to_string(char **joined, char ** array, size_t count, char dm) {
    size_t i;
    size_t total_length = 0;
    size_t item_length = 0;
    char *result = NULL;
    char *last = NULL;

    if (!array || !joined)
        return 0;

    for (i=0; i<count; i++) {
        if (!array[i])
            continue;

        item_length = strlen(array[i]) + 1;
        total_length += item_length;
    }

    if (!total_length) {
        return 0;
    }

    result = malloc(total_length);
    if (!result) {
        PyErr_NoMemory();
        return -1;
    }

    result[0] = '\0';
    last = result;

    for (i=0; i<count; i++) {
        if (!array[i])
            continue;

        item_length = strlen(array[i]);
        memcpy(last, array[i], item_length);
        last[item_length] = dm;

        last += item_length + 1;
    }

    result[total_length-1] = '\0';
    *joined = result;

    return total_length;
}

/*
 * Return process name and args as a Python tuple.
 */
PyObject *
psutil_proc_name_and_args(PyObject *self, PyObject *args) {
    int pid;
    char path[1000];
    psinfo_t info;
    size_t argc;
    int joined;
    char **argv;
    char *argv_plain;
    const char *procfs_path;
    PyObject *py_name = NULL;
    PyObject *py_args = NULL;
    PyObject *py_retlist = NULL;

    if (! PyArg_ParseTuple(args, "is", &pid, &procfs_path))
        return NULL;
    sprintf(path, "%s/%i/psinfo", procfs_path, pid);
    if (! psutil_file_to_struct(path, (void *)&info, sizeof(info)))
        return NULL;

    py_name = PyUnicode_DecodeFSDefault(info.pr_fname);
    if (!py_name)
        goto error;

    /* SunOS truncates arguments to length PRARGSZ, very likely args are truncated.
     * The only way to retrieve full command line is to parse process memory */
    if (info.pr_argc && strlen(info.pr_psargs) == PRARGSZ-1) {
        argv = psutil_read_raw_args(info, procfs_path, &argc);
        if (argv) {
            joined = cstrings_array_to_string(&argv_plain, argv, argc, ' ');
            if (joined > 0) {
                py_args = PyUnicode_DecodeFSDefault(argv_plain);
                free(argv_plain);
            } else if (joined < 0) {
                goto error;
            }

            psutil_free_cstrings_array(argv, argc);
        }
    }

    /* If we can't read process memory or can't decode the result
     * then return args from /proc. */
    if (!py_args) {
        PyErr_Clear();
        py_args = PyUnicode_DecodeFSDefault(info.pr_psargs);
    }

    /* Both methods has been failed. */
    if (!py_args)
        goto error;

    py_retlist = Py_BuildValue("OO", py_name, py_args);
    if (!py_retlist)
        goto error;

    Py_DECREF(py_name);
    Py_DECREF(py_args);
    return py_retlist;

error:
    Py_XDECREF(py_name);
    Py_XDECREF(py_args);
    Py_XDECREF(py_retlist);
    return NULL;
}


/*
 * Return process environ block.
 */
PyObject *
psutil_proc_environ(PyObject *self, PyObject *args) {
    int pid;
    char path[1000];
    psinfo_t info;
    const char *procfs_path;
    char **env = NULL;
    ssize_t env_count = -1;
    char *dm;
    int i = 0;
    PyObject *py_envname = NULL;
    PyObject *py_envval = NULL;
    PyObject *py_retdict = PyDict_New();

    if (! py_retdict)
        return PyErr_NoMemory();

    if (! PyArg_ParseTuple(args, "is", &pid, &procfs_path))
        return NULL;

    sprintf(path, "%s/%i/psinfo", procfs_path, pid);
    if (! psutil_file_to_struct(path, (void *)&info, sizeof(info)))
        goto error;

    if (! info.pr_envp) {
        AccessDenied("/proc/pid/psinfo struct not set");
        goto error;
    }

    env = psutil_read_raw_env(info, procfs_path, &env_count);
    if (! env && env_count != 0)
        goto error;

    for (i=0; i<env_count; i++) {
        if (! env[i])
            break;

        dm = strchr(env[i], '=');
        if (! dm)
            continue;

        *dm = '\0';

        py_envname = PyUnicode_DecodeFSDefault(env[i]);
        if (! py_envname)
            goto error;

        py_envval = PyUnicode_DecodeFSDefault(dm+1);
        if (! py_envname)
            goto error;

        if (PyDict_SetItem(py_retdict, py_envname, py_envval) < 0)
            goto error;

        Py_CLEAR(py_envname);
        Py_CLEAR(py_envval);
    }

    psutil_free_cstrings_array(env, env_count);
    return py_retdict;

 error:
    if (env && env_count >= 0)
        psutil_free_cstrings_array(env, env_count);

    Py_XDECREF(py_envname);
    Py_XDECREF(py_envval);
    Py_XDECREF(py_retdict);
    return NULL;
}


/*
 * Return process user and system CPU times as a Python tuple.
 */
PyObject *
psutil_proc_cpu_times(PyObject *self, PyObject *args) {
    int pid;
    char path[1000];
    pstatus_t info;
    const char *procfs_path;

    if (! PyArg_ParseTuple(args, "is", &pid, &procfs_path))
        return NULL;
    sprintf(path, "%s/%i/status", procfs_path, pid);
    if (! psutil_file_to_struct(path, (void *)&info, sizeof(info)))
        return NULL;
    // results are more precise than os.times()
    return Py_BuildValue(
        "(dddd)",
         PSUTIL_TV2DOUBLE(info.pr_utime),
         PSUTIL_TV2DOUBLE(info.pr_stime),
         PSUTIL_TV2DOUBLE(info.pr_cutime),
         PSUTIL_TV2DOUBLE(info.pr_cstime)
    );
}


/*
 * Return what CPU the process is running on.
 */
PyObject *
psutil_proc_cpu_num(PyObject *self, PyObject *args) {
    int fd = -1;
    int pid;
    char path[1000];
    struct prheader header;
    struct lwpsinfo *lwp = NULL;
    int nent;
    int size;
    int proc_num;
    ssize_t nbytes;
    const char *procfs_path;

    if (! PyArg_ParseTuple(args, "is", &pid, &procfs_path))
        return NULL;

    sprintf(path, "%s/%i/lpsinfo", procfs_path, pid);
    fd = open(path, O_RDONLY);
    if (fd == -1) {
        PyErr_SetFromErrnoWithFilename(PyExc_OSError, path);
        return NULL;
    }

    // read header
    nbytes = pread(fd, &header, sizeof(header), 0);
    if (nbytes == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }
    if (nbytes != sizeof(header)) {
        PyErr_SetString(
            PyExc_RuntimeError, "read() file structure size mismatch");
        goto error;
    }

    // malloc
    nent = header.pr_nent;
    size = header.pr_entsize * nent;
    lwp = malloc(size);
    if (lwp == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    // read the rest
    nbytes = pread(fd, lwp, size, sizeof(header));
    if (nbytes == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }
    if (nbytes != size) {
        PyErr_SetString(
            PyExc_RuntimeError, "read() file structure size mismatch");
        goto error;
    }

    // done
    proc_num = lwp->pr_onpro;
    close(fd);
    free(lwp);
    return Py_BuildValue("i", proc_num);

error:
    if (fd != -1)
        close(fd);
    free(lwp);
    return NULL;
}


/*
 * Return process uids/gids as a Python tuple.
 */
PyObject *
psutil_proc_cred(PyObject *self, PyObject *args) {
    int pid;
    char path[1000];
    prcred_t info;
    const char *procfs_path;

    if (! PyArg_ParseTuple(args, "is", &pid, &procfs_path))
        return NULL;
    sprintf(path, "%s/%i/cred", procfs_path, pid);
    if (! psutil_file_to_struct(path, (void *)&info, sizeof(info)))
        return NULL;
    return Py_BuildValue("iiiiii",
                         info.pr_ruid, info.pr_euid, info.pr_suid,
                         info.pr_rgid, info.pr_egid, info.pr_sgid);
}


/*
 * Return process voluntary and involuntary context switches as a Python tuple.
 */
PyObject *
psutil_proc_num_ctx_switches(PyObject *self, PyObject *args) {
    int pid;
    char path[1000];
    prusage_t info;
    const char *procfs_path;

    if (! PyArg_ParseTuple(args, "is", &pid, &procfs_path))
        return NULL;
    sprintf(path, "%s/%i/usage", procfs_path, pid);
    if (! psutil_file_to_struct(path, (void *)&info, sizeof(info)))
        return NULL;
    return Py_BuildValue("kk", info.pr_vctx, info.pr_ictx);
}
