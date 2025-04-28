/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Functions specific to Sun OS Solaris platforms.
 *
 * Thanks to Justin Venus who originally wrote a consistent part of
 * this in Cython which I later on translated in C.
 */

/* fix compilation issue on SunOS 5.10, see:
 * https://github.com/giampaolo/psutil/issues/421
 * https://github.com/giampaolo/psutil/issues/1077
*/

#define _STRUCTURED_PROC 1

#include <Python.h>

#if !defined(_LP64) && _FILE_OFFSET_BITS == 64
#  undef _FILE_OFFSET_BITS
#  undef _LARGEFILE64_SOURCE
#endif

#include <sys/types.h>
#include <sys/stat.h>
#include <sys/proc.h>
#include <sys/procfs.h>
#include <fcntl.h>
#include <kstat.h>
#include <sys/ioctl.h>
#include <inet/tcp.h>

#include "_psutil_posix.h"
#include "arch/all/init.h"
#include "arch/sunos/cpu.h"
#include "arch/sunos/disk.h"
#include "arch/sunos/environ.h"
#include "arch/sunos/mem.h"
#include "arch/sunos/net.h"
#include "arch/sunos/proc.h"
#include "arch/sunos/sys.h"


/*
 * Return process user and system CPU times as a Python tuple.
 */
static PyObject *
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
static PyObject *
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
static PyObject *
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
static PyObject *
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


/*
 * Process IO counters.
 *
 * Commented out and left here as a reminder.  Apparently we cannot
 * retrieve process IO stats because:
 * - 'pr_ioch' is a sum of chars read and written, with no distinction
 * - 'pr_inblk' and 'pr_oublk', which should be the number of bytes
 *    read and written, hardly increase and according to:
 *    http://www.brendangregg.com/Solaris/paper_diskubyp1.pdf
 *    ...they should be meaningless anyway.
 *
static PyObject*
proc_io_counters(PyObject* self, PyObject* args) {
    int pid;
    char path[1000];
    prusage_t info;
    const char *procfs_path;

    if (! PyArg_ParseTuple(args, "is", &pid, &procfs_path))
        return NULL;
    sprintf(path, "%s/%i/usage", procfs_path, pid);
    if (! psutil_file_to_struct(path, (void *)&info, sizeof(info)))
        return NULL;

    // On Solaris we only have 'pr_ioch' which accounts for bytes read
    // *and* written.
    // 'pr_inblk' and 'pr_oublk' should be expressed in blocks of
    // 8KB according to:
    // http://www.brendangregg.com/Solaris/paper_diskubyp1.pdf (pag. 8)
    return Py_BuildValue("kkkk",
                         info.pr_ioch,
                         info.pr_ioch,
                         info.pr_inblk,
                         info.pr_oublk);
}
*/


/*
 * Return information about a given process thread.
 */
static PyObject *
psutil_proc_query_thread(PyObject *self, PyObject *args) {
    int pid, tid;
    char path[1000];
    lwpstatus_t info;
    const char *procfs_path;

    if (! PyArg_ParseTuple(args, "iis", &pid, &tid, &procfs_path))
        return NULL;
    sprintf(path, "%s/%i/lwp/%i/lwpstatus", procfs_path, pid, tid);
    if (! psutil_file_to_struct(path, (void *)&info, sizeof(info)))
        return NULL;
    return Py_BuildValue("dd",
                         PSUTIL_TV2DOUBLE(info.pr_utime),
                         PSUTIL_TV2DOUBLE(info.pr_stime));
}


/*
 * Return process memory mappings.
 */
static PyObject *
psutil_proc_memory_maps(PyObject *self, PyObject *args) {
    int pid;
    int fd = -1;
    char path[1000];
    char perms[10];
    const char *name;
    struct stat st;
    pstatus_t status;

    prxmap_t *xmap = NULL, *p;
    off_t size;
    size_t nread;
    int nmap;
    uintptr_t pr_addr_sz;
    uintptr_t stk_base_sz, brk_base_sz;
    const char *procfs_path;

    PyObject *py_tuple = NULL;
    PyObject *py_path = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;
    if (! PyArg_ParseTuple(args, "is", &pid, &procfs_path))
        goto error;

    sprintf(path, "%s/%i/status", procfs_path, pid);
    if (! psutil_file_to_struct(path, (void *)&status, sizeof(status)))
        goto error;

    sprintf(path, "%s/%i/xmap", procfs_path, pid);
    if (stat(path, &st) == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }

    size = st.st_size;

    fd = open(path, O_RDONLY);
    if (fd == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }

    xmap = (prxmap_t *)malloc(size);
    if (xmap == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    nread = pread(fd, xmap, size, 0);
    nmap = nread / sizeof(prxmap_t);
    p = xmap;

    while (nmap) {
        nmap -= 1;
        if (p == NULL) {
            p += 1;
            continue;
        }

        perms[0] = '\0';
        pr_addr_sz = p->pr_vaddr + p->pr_size;

        // perms
        sprintf(perms, "%c%c%c%c", p->pr_mflags & MA_READ ? 'r' : '-',
                p->pr_mflags & MA_WRITE ? 'w' : '-',
                p->pr_mflags & MA_EXEC ? 'x' : '-',
                p->pr_mflags & MA_SHARED ? 's' : '-');

        // name
        if (strlen(p->pr_mapname) > 0) {
            name = p->pr_mapname;
        }
        else {
            if ((p->pr_mflags & MA_ISM) || (p->pr_mflags & MA_SHM)) {
                name = "[shmid]";
            }
            else {
                stk_base_sz = status.pr_stkbase + status.pr_stksize;
                brk_base_sz = status.pr_brkbase + status.pr_brksize;

                if ((pr_addr_sz > status.pr_stkbase) &&
                        (p->pr_vaddr < stk_base_sz)) {
                    name = "[stack]";
                }
                else if ((p->pr_mflags & MA_ANON) && \
                         (pr_addr_sz > status.pr_brkbase) && \
                         (p->pr_vaddr < brk_base_sz)) {
                    name = "[heap]";
                }
                else {
                    name = "[anon]";
                }
            }
        }

        py_path = PyUnicode_DecodeFSDefault(name);
        if (! py_path)
            goto error;
        py_tuple = Py_BuildValue(
            "kksOkkk",
            (unsigned long)p->pr_vaddr,
            (unsigned long)pr_addr_sz,
            perms,
            py_path,
            (unsigned long)p->pr_rss * p->pr_pagesize,
            (unsigned long)p->pr_anon * p->pr_pagesize,
            (unsigned long)p->pr_locked * p->pr_pagesize);
        if (!py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_CLEAR(py_path);
        Py_CLEAR(py_tuple);

        // increment pointer
        p += 1;
    }

    close(fd);
    free(xmap);
    return py_retlist;

error:
    if (fd != -1)
        close(fd);
    Py_XDECREF(py_tuple);
    Py_XDECREF(py_path);
    Py_DECREF(py_retlist);
    if (xmap != NULL)
        free(xmap);
    return NULL;
}


/*
 * define the psutil C module methods and initialize the module.
 */
static PyMethodDef mod_methods[] = {
    // --- process-related functions
    {"proc_basic_info", psutil_proc_basic_info, METH_VARARGS},
    {"proc_cpu_num", psutil_proc_cpu_num, METH_VARARGS},
    {"proc_cpu_times", psutil_proc_cpu_times, METH_VARARGS},
    {"proc_cred", psutil_proc_cred, METH_VARARGS},
    {"proc_environ", psutil_proc_environ, METH_VARARGS},
    {"proc_memory_maps", psutil_proc_memory_maps, METH_VARARGS},
    {"proc_name_and_args", psutil_proc_name_and_args, METH_VARARGS},
    {"proc_num_ctx_switches", psutil_proc_num_ctx_switches, METH_VARARGS},
    {"query_process_thread", psutil_proc_query_thread, METH_VARARGS},

    // --- system-related functions
    {"boot_time", psutil_boot_time, METH_VARARGS},
    {"cpu_count_cores", psutil_cpu_count_cores, METH_VARARGS},
    {"cpu_stats", psutil_cpu_stats, METH_VARARGS},
    {"disk_io_counters", psutil_disk_io_counters, METH_VARARGS},
    {"disk_partitions", psutil_disk_partitions, METH_VARARGS},
    {"net_connections", psutil_net_connections, METH_VARARGS},
    {"net_if_stats", psutil_net_if_stats, METH_VARARGS},
    {"net_io_counters", psutil_net_io_counters, METH_VARARGS},
    {"per_cpu_times", psutil_per_cpu_times, METH_VARARGS},
    {"swap_mem", psutil_swap_mem, METH_VARARGS},
    {"users", psutil_users, METH_VARARGS},

    // --- others
    {"check_pid_range", psutil_check_pid_range, METH_VARARGS},
    {"set_debug", psutil_set_debug, METH_VARARGS},

    {NULL, NULL, 0, NULL}
};


struct module_state {
    PyObject *error;
};


static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "psutil_sunos",
    NULL,
    -1,
    mod_methods,
    NULL,
    NULL,
    NULL,
    NULL
};


PyObject *
PyInit__psutil_sunos(void) {
    PyObject *mod = PyModule_Create(&moduledef);
    if (mod == NULL)
        return NULL;

#ifdef Py_GIL_DISABLED
    if (PyUnstable_Module_SetGIL(mod, Py_MOD_GIL_NOT_USED))
        return NULL;
#endif

    if (psutil_setup() != 0)
        return NULL;

    if (PyModule_AddIntConstant(mod, "version", PSUTIL_VERSION))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SSLEEP", SSLEEP))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SRUN", SRUN))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SZOMB", SZOMB))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SSTOP", SSTOP))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SIDL", SIDL))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SONPROC", SONPROC))
        return NULL;
#ifdef SWAIT
    if (PyModule_AddIntConstant(mod, "SWAIT", SWAIT))
        return NULL;
#else
    /* sys/proc.h started defining SWAIT somewhere
     * after Update 3 and prior to Update 5 included.
     */
    if (PyModule_AddIntConstant(mod, "SWAIT", 0))
        return NULL;
#endif
    // for process tty
    if (PyModule_AddIntConstant(mod, "PRNODEV", PRNODEV))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_CLOSED", TCPS_CLOSED))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_CLOSING", TCPS_CLOSING))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_CLOSE_WAIT", TCPS_CLOSE_WAIT))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_LISTEN", TCPS_LISTEN))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_ESTABLISHED", TCPS_ESTABLISHED))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_SYN_SENT", TCPS_SYN_SENT))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_SYN_RCVD", TCPS_SYN_RCVD))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_FIN_WAIT_1", TCPS_FIN_WAIT_1))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_FIN_WAIT_2", TCPS_FIN_WAIT_2))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_LAST_ACK", TCPS_LAST_ACK))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_TIME_WAIT", TCPS_TIME_WAIT))
        return NULL;
    // sunos specific
    if (PyModule_AddIntConstant(mod, "TCPS_IDLE", TCPS_IDLE))
        return NULL;
    // sunos specific
    if (PyModule_AddIntConstant(mod, "TCPS_BOUND", TCPS_BOUND))
        return NULL;
    if (PyModule_AddIntConstant(mod, "PSUTIL_CONN_NONE", PSUTIL_CONN_NONE))
        return NULL;

    return mod;
}
