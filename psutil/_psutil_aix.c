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
 * - psutil.Process.io_counters may not be available on older AIX versions
 * - psutil.Process.threads may not be available on older AIX versions
 # - psutil.net_io_counters may not be available on older AIX versions
 * - reading basic process info may fail or return incorrect values when
 *   process is starting (see IBM APAR IV58499 - fixed in newer AIX versions)
 * - sockets and pipes may not be counted in num_fds (fixed in newer AIX
 *    versions)
 *
 * Useful resources:
 * - proc filesystem: http://www-01.ibm.com/support/knowledgecenter/
 *       ssw_aix_72/com.ibm.aix.files/proc.htm
 * - libperfstat: http://www-01.ibm.com/support/knowledgecenter/
 *       ssw_aix_72/com.ibm.aix.files/libperfstat.h.htm
 */

#include <Python.h>

#include <sys/limits.h>
#include <sys/proc.h>
#include <sys/procfs.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/sysinfo.h>
#include <sys/thread.h>
#include <sys/types.h>
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
#include <libperfstat.h>
#include <unistd.h>

#include "arch/aix/ifaddrs.h"
#include "arch/aix/net_connections.h"
#include "arch/aix/common.h"
#include "_psutil_common.h"
#include "_psutil_posix.h"


#define TV2DOUBLE(t)   (((t).tv_nsec * 0.000000001) + (t).tv_sec)

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
    char path[100];
    psinfo_t info;
    pstatus_t status;
    const char *procfs_path;

    if (! PyArg_ParseTuple(args, "is", &pid, &procfs_path))
        return NULL;

    sprintf(path, "%s/%i/psinfo", procfs_path, pid);
    if (! psutil_file_to_struct(path, (void *)&info, sizeof(info)))
        return NULL;

    if (info.pr_nlwp == 0 && info.pr_lwp.pr_lwpid == 0) {
        // From the /proc docs: "If the process is a zombie, the pr_nlwp
        // and pr_lwp.pr_lwpid flags are zero."
        status.pr_stat = SZOMB;
    } else if (info.pr_flag & SEXIT) {
        // "exiting" processes don't have /proc/<pid>/status
        // There are other "exiting" processes that 'ps' shows as "active"
        status.pr_stat = SACTIVE;
    } else {
        sprintf(path, "%s/%i/status", procfs_path, pid);
        if (! psutil_file_to_struct(path, (void *)&status, sizeof(status)))
            return NULL;
    }

    return Py_BuildValue("KKKdiiiK",
        (unsigned long long) info.pr_ppid,      // parent pid
        (unsigned long long) info.pr_rssize,    // rss
        (unsigned long long) info.pr_size,      // vms
        TV2DOUBLE(info.pr_start),               // create time
        (int) info.pr_lwp.pr_nice,              // nice
        (int) info.pr_nlwp,                     // no. of threads
        (int) status.pr_stat,                   // status code
        (unsigned long long)info.pr_ttydev      // tty nr
        );
}


/*
 * Return process name as a Python string.
 */
static PyObject *
psutil_proc_name(PyObject *self, PyObject *args) {
    int pid;
    char path[100];
    psinfo_t info;
    const char *procfs_path;

    if (! PyArg_ParseTuple(args, "is", &pid, &procfs_path))
        return NULL;
    sprintf(path, "%s/%i/psinfo", procfs_path, pid);
    if (! psutil_file_to_struct(path, (void *)&info, sizeof(info)))
        return NULL;

    return PyUnicode_DecodeFSDefaultAndSize(info.pr_fname, PRFNSZ);
}


/*
 * Return process command line arguments as a Python list
 */
static PyObject *
psutil_proc_args(PyObject *self, PyObject *args) {
    int pid;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_arg = NULL;
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
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }

    curarg = argbuf;
    /* getargs will always append an extra NULL to end the arg list,
     * even if the buffer is not big enough (even though it is supposed
     * to be) so the following 'while' is safe */
    while (*curarg != '\0') {
        py_arg = PyUnicode_DecodeFSDefault(curarg);
        if (!py_arg)
            goto error;
        if (PyList_Append(py_retlist, py_arg))
            goto error;
        Py_DECREF(py_arg);
        curarg = strchr(curarg, '\0') + 1;
    }

    free(argbuf);

    return py_retlist;

error:
    if (argbuf != NULL)
        free(argbuf);
    Py_XDECREF(py_retlist);
    Py_XDECREF(py_arg);
    return NULL;
}


/*
 * Return process environment variables as a Python dict
 */
static PyObject *
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
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }

    curvar = envbuf;
    /* getevars will always append an extra NULL to end the arg list,
     * even if the buffer is not big enough (even though it is supposed
     * to be) so the following 'while' is safe */
    while (*curvar != '\0') {
        separator = strchr(curvar, '=');
        if (separator != NULL) {
            py_key = PyUnicode_DecodeFSDefaultAndSize(
                curvar,
                (Py_ssize_t)(separator - curvar)
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

/*
 * Retrieves all threads used by process returning a list of tuples
 * including thread id, user time and system time.
 */
static PyObject *
psutil_proc_threads(PyObject *self, PyObject *args) {
    long pid;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;
    perfstat_thread_t *threadt = NULL;
    perfstat_id_t id;
    int i, rc, thread_count;

    if (py_retlist == NULL)
        return NULL;
    if (! PyArg_ParseTuple(args, "l", &pid))
        goto error;

    /* Get the count of threads */
    thread_count = perfstat_thread(NULL, NULL, sizeof(perfstat_thread_t), 0);
    if (thread_count <= 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }

    /* Allocate enough memory */
    threadt = (perfstat_thread_t *)calloc(thread_count,
        sizeof(perfstat_thread_t));
    if (threadt == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    strcpy(id.name, "");
    rc = perfstat_thread(&id, threadt, sizeof(perfstat_thread_t),
        thread_count);
    if (rc <= 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }

    for (i = 0; i < thread_count; i++) {
        if (threadt[i].pid != pid)
            continue;

        py_tuple = Py_BuildValue("Idd",
                                 threadt[i].tid,
                                 threadt[i].ucpu_time,
                                 threadt[i].scpu_time);
        if (py_tuple == NULL)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_DECREF(py_tuple);
    }
    free(threadt);
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    if (threadt != NULL)
        free(threadt);
    return NULL;
}

#endif


#ifdef CURR_VERSION_PROCESS

static PyObject *
psutil_proc_io_counters(PyObject *self, PyObject *args) {
    long pid;
    int rc;
    perfstat_process_t procinfo;
    perfstat_id_t id;
    if (! PyArg_ParseTuple(args, "l", &pid))
        return NULL;

    snprintf(id.name, sizeof(id.name), "%ld", pid);
    rc = perfstat_process(&id, &procinfo, sizeof(perfstat_process_t), 1);
    if (rc <= 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }

    return Py_BuildValue("(KKKK)",
                         procinfo.inOps,      // XXX always 0
                         procinfo.outOps,
                         procinfo.inBytes,    // XXX always 0
                         procinfo.outBytes);
}

#endif


/*
 * Return process user and system CPU times as a Python tuple.
 */
static PyObject *
psutil_proc_cpu_times(PyObject *self, PyObject *args) {
    int pid;
    char path[100];
    pstatus_t info;
    const char *procfs_path;

    if (! PyArg_ParseTuple(args, "is", &pid, &procfs_path))
        return NULL;
    sprintf(path, "%s/%i/status", procfs_path, pid);
    if (! psutil_file_to_struct(path, (void *)&info, sizeof(info)))
        return NULL;
    // results are more precise than os.times()
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
    PyObject *py_tuple = NULL;
    pid32_t requested_pid;
    pid32_t pid = 0;
    int np = 0;
    struct procentry64 *processes = (struct procentry64 *)NULL;
    struct procentry64 *p;

    if (! PyArg_ParseTuple(args, "i", &requested_pid))
        return NULL;

    processes = psutil_read_process_table(&np);
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
 * Return users currently connected on the system.
 */
static PyObject *
psutil_users(PyObject *self, PyObject *args) {
    struct utmpx *ut;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;
    PyObject *py_username = NULL;
    PyObject *py_tty = NULL;
    PyObject *py_hostname = NULL;
    PyObject *py_user_proc = NULL;

    if (py_retlist == NULL)
        return NULL;

    setutxent();
    while (NULL != (ut = getutxent())) {
        if (ut->ut_type == USER_PROCESS)
            py_user_proc = Py_True;
        else
            py_user_proc = Py_False;
        py_username = PyUnicode_DecodeFSDefault(ut->ut_user);
        if (! py_username)
            goto error;
        py_tty = PyUnicode_DecodeFSDefault(ut->ut_line);
        if (! py_tty)
            goto error;
        py_hostname = PyUnicode_DecodeFSDefault(ut->ut_host);
        if (! py_hostname)
            goto error;
        py_tuple = Py_BuildValue(
            "(OOOfOi)",
            py_username,              // username
            py_tty,                   // tty
            py_hostname,              // hostname
            (float)ut->ut_tv.tv_sec,  // tstamp
            py_user_proc,             // (bool) user process
            ut->ut_pid                // process id
        );
        if (py_tuple == NULL)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_CLEAR(py_username);
        Py_CLEAR(py_tty);
        Py_CLEAR(py_hostname);
        Py_CLEAR(py_tuple);
    }
    endutxent();

    return py_retlist;

error:
    Py_XDECREF(py_username);
    Py_XDECREF(py_tty);
    Py_XDECREF(py_hostname);
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    if (ut != NULL)
        endutxent();
    return NULL;
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
        Py_CLEAR(py_dev);
        Py_CLEAR(py_mountp);
        Py_CLEAR(py_tuple);
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


#if defined(CURR_VERSION_NETINTERFACE) && CURR_VERSION_NETINTERFACE >= 3

/*
 * Return a list of tuples for network I/O statistics.
 */
static PyObject *
psutil_net_io_counters(PyObject *self, PyObject *args) {
    perfstat_netinterface_t *statp = NULL;
    int tot, i;
    perfstat_id_t first;

    PyObject *py_retdict = PyDict_New();
    PyObject *py_ifc_info = NULL;

    if (py_retdict == NULL)
        return NULL;

    /* check how many perfstat_netinterface_t structures are available */
    tot = perfstat_netinterface(
        NULL, NULL, sizeof(perfstat_netinterface_t), 0);
    if (tot == 0) {
        // no network interfaces - return empty dict
        return py_retdict;
    }
    if (tot < 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }
    statp = (perfstat_netinterface_t *)
        malloc(tot * sizeof(perfstat_netinterface_t));
    if (statp == NULL) {
        PyErr_NoMemory();
        goto error;
    }
    strcpy(first.name, FIRST_NETINTERFACE);
    tot = perfstat_netinterface(&first, statp,
        sizeof(perfstat_netinterface_t), tot);
    if (tot < 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }

    for (i = 0; i < tot; i++) {
        py_ifc_info = Py_BuildValue("(KKKKKKKK)",
            statp[i].obytes,      /* number of bytes sent on interface */
            statp[i].ibytes,      /* number of bytes received on interface */
            statp[i].opackets,    /* number of packets sent on interface */
            statp[i].ipackets,    /* number of packets received on interface */
            statp[i].ierrors,     /* number of input errors on interface */
            statp[i].oerrors,     /* number of output errors on interface */
            statp[i].if_iqdrops,  /* Dropped on input, this interface */
            statp[i].xmitdrops    /* number of packets not transmitted */
           );
        if (!py_ifc_info)
            goto error;
        if (PyDict_SetItemString(py_retdict, statp[i].name, py_ifc_info))
            goto error;
        Py_DECREF(py_ifc_info);
    }

    free(statp);
    return py_retdict;

error:
    if (statp != NULL)
        free(statp);
    Py_XDECREF(py_ifc_info);
    Py_DECREF(py_retdict);
    return NULL;
}

#endif


static PyObject*
psutil_net_if_stats(PyObject* self, PyObject* args) {
    char *nic_name;
    int sock = 0;
    int ret;
    int mtu;
    struct ifreq ifr;
    PyObject *py_is_up = NULL;
    PyObject *py_retlist = NULL;

    if (! PyArg_ParseTuple(args, "s", &nic_name))
        return NULL;

    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == -1)
        goto error;

    strncpy(ifr.ifr_name, nic_name, sizeof(ifr.ifr_name));

    // is up?
    ret = ioctl(sock, SIOCGIFFLAGS, &ifr);
    if (ret == -1)
        goto error;
    if ((ifr.ifr_flags & IFF_UP) != 0)
        py_is_up = Py_True;
    else
        py_is_up = Py_False;
    Py_INCREF(py_is_up);

    // MTU
    ret = ioctl(sock, SIOCGIFMTU, &ifr);
    if (ret == -1)
        goto error;
    mtu = ifr.ifr_mtu;

    close(sock);
    py_retlist = Py_BuildValue("[Oi]", py_is_up, mtu);
    if (!py_retlist)
        goto error;
    Py_DECREF(py_is_up);
    return py_retlist;

error:
    Py_XDECREF(py_is_up);
    if (sock != 0)
        close(sock);
    PyErr_SetFromErrno(PyExc_OSError);
    return NULL;
}


static PyObject *
psutil_boot_time(PyObject *self, PyObject *args) {
    float boot_time = 0.0;
    struct utmpx *ut;

    setutxent();
    while (NULL != (ut = getutxent())) {
        if (ut->ut_type == BOOT_TIME) {
            boot_time = (float)ut->ut_tv.tv_sec;
            break;
        }
    }
    endutxent();
    if (boot_time == 0.0) {
        /* could not find BOOT_TIME in getutxent loop */
        PyErr_SetString(PyExc_RuntimeError, "can't determine boot time");
        return NULL;
    }
    return Py_BuildValue("f", boot_time);
}


/*
 * Return a Python list of tuple representing per-cpu times
 */
static PyObject *
psutil_per_cpu_times(PyObject *self, PyObject *args) {
    int ncpu, rc, i;
    long ticks;
    perfstat_cpu_t *cpu = NULL;
    perfstat_id_t id;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_cputime = NULL;

    if (py_retlist == NULL)
        return NULL;

    /* get the number of ticks per second */
    ticks = sysconf(_SC_CLK_TCK);
    if (ticks < 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }

    /* get the number of cpus in ncpu */
    ncpu = perfstat_cpu(NULL, NULL, sizeof(perfstat_cpu_t), 0);
    if (ncpu <= 0){
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }

    /* allocate enough memory to hold the ncpu structures */
    cpu = (perfstat_cpu_t *) malloc(ncpu * sizeof(perfstat_cpu_t));
    if (cpu == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    strcpy(id.name, "");
    rc = perfstat_cpu(&id, cpu, sizeof(perfstat_cpu_t), ncpu);

    if (rc <= 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }

    for (i = 0; i < ncpu; i++) {
        py_cputime = Py_BuildValue(
            "(dddd)",
            (double)cpu[i].user / ticks,
            (double)cpu[i].sys / ticks,
            (double)cpu[i].idle / ticks,
            (double)cpu[i].wait / ticks);
        if (!py_cputime)
            goto error;
        if (PyList_Append(py_retlist, py_cputime))
            goto error;
        Py_DECREF(py_cputime);
    }
    free(cpu);
    return py_retlist;

error:
    Py_XDECREF(py_cputime);
    Py_DECREF(py_retlist);
    if (cpu != NULL)
        free(cpu);
    return NULL;
}


/*
 * Return disk IO statistics.
 */
static PyObject *
psutil_disk_io_counters(PyObject *self, PyObject *args) {
    PyObject *py_retdict = PyDict_New();
    PyObject *py_disk_info = NULL;
    perfstat_disk_t *diskt = NULL;
    perfstat_id_t id;
    int i, rc, disk_count;

    if (py_retdict == NULL)
        return NULL;

    /* Get the count of disks */
    disk_count = perfstat_disk(NULL, NULL, sizeof(perfstat_disk_t), 0);
    if (disk_count <= 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }

    /* Allocate enough memory */
    diskt = (perfstat_disk_t *)calloc(disk_count,
        sizeof(perfstat_disk_t));
    if (diskt == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    strcpy(id.name, FIRST_DISK);
    rc = perfstat_disk(&id, diskt, sizeof(perfstat_disk_t),
        disk_count);
    if (rc <= 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }

    for (i = 0; i < disk_count; i++) {
        py_disk_info = Py_BuildValue(
            "KKKKKK",
            diskt[i].__rxfers,
            diskt[i].xfers - diskt[i].__rxfers,
            diskt[i].rblks * diskt[i].bsize,
            diskt[i].wblks * diskt[i].bsize,
            diskt[i].rserv / 1000 / 1000,  // from nano to milli secs
            diskt[i].wserv / 1000 / 1000   // from nano to milli secs
        );
        if (py_disk_info == NULL)
            goto error;
        if (PyDict_SetItemString(py_retdict, diskt[i].name,
                                 py_disk_info))
            goto error;
        Py_DECREF(py_disk_info);
    }
    free(diskt);
    return py_retdict;

error:
    Py_XDECREF(py_disk_info);
    Py_DECREF(py_retdict);
    if (diskt != NULL)
        free(diskt);
    return NULL;
}


/*
 * Return virtual memory usage statistics.
 */
static PyObject *
psutil_virtual_mem(PyObject *self, PyObject *args) {
    int rc;
    int pagesize = getpagesize();
    perfstat_memory_total_t memory;

    rc = perfstat_memory_total(
        NULL, &memory, sizeof(perfstat_memory_total_t), 1);
    if (rc <= 0){
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }

    return Py_BuildValue("KKKKK",
        (unsigned long long) memory.real_total * pagesize,
        (unsigned long long) memory.real_avail * pagesize,
        (unsigned long long) memory.real_free * pagesize,
        (unsigned long long) memory.real_pinned * pagesize,
        (unsigned long long) memory.real_inuse * pagesize
    );
}


/*
 * Return stats about swap memory.
 */
static PyObject *
psutil_swap_mem(PyObject *self, PyObject *args) {
    int rc;
    int pagesize = getpagesize();
    perfstat_memory_total_t memory;

    rc = perfstat_memory_total(
        NULL, &memory, sizeof(perfstat_memory_total_t), 1);
    if (rc <= 0){
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }

    return Py_BuildValue("KKKK",
        (unsigned long long) memory.pgsp_total * pagesize,
        (unsigned long long) memory.pgsp_free * pagesize,
        (unsigned long long) memory.pgins * pagesize,
        (unsigned long long) memory.pgouts * pagesize
    );
}


/*
 * Return CPU statistics.
 */
static PyObject *
psutil_cpu_stats(PyObject *self, PyObject *args) {
    int ncpu, rc, i;
    // perfstat_cpu_total_t doesn't have invol/vol cswitch, only pswitch
    // which is apparently something else. We have to sum over all cpus
    perfstat_cpu_t *cpu = NULL;
    perfstat_id_t id;
    u_longlong_t cswitches = 0;
    u_longlong_t devintrs = 0;
    u_longlong_t softintrs = 0;
    u_longlong_t syscall = 0;

    /* get the number of cpus in ncpu */
    ncpu = perfstat_cpu(NULL, NULL, sizeof(perfstat_cpu_t), 0);
    if (ncpu <= 0){
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }

    /* allocate enough memory to hold the ncpu structures */
    cpu = (perfstat_cpu_t *) malloc(ncpu * sizeof(perfstat_cpu_t));
    if (cpu == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    strcpy(id.name, "");
    rc = perfstat_cpu(&id, cpu, sizeof(perfstat_cpu_t), ncpu);

    if (rc <= 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }

    for (i = 0; i < ncpu; i++) {
        cswitches += cpu[i].invol_cswitch + cpu[i].vol_cswitch;
        devintrs += cpu[i].devintrs;
        softintrs += cpu[i].softintrs;
        syscall += cpu[i].syscall;
    }

    free(cpu);

    return Py_BuildValue(
        "KKKK",
        cswitches,
        devintrs,
        softintrs,
        syscall
    );

error:
    if (cpu != NULL)
        free(cpu);
    return NULL;
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
    {"proc_name", psutil_proc_name, METH_VARARGS,
     "Return process name."},
    {"proc_args", psutil_proc_args, METH_VARARGS,
     "Return process command line arguments."},
    {"proc_environ", psutil_proc_environ, METH_VARARGS,
     "Return process environment variables."},
    {"proc_cpu_times", psutil_proc_cpu_times, METH_VARARGS,
     "Return process user and system CPU times."},
    {"proc_cred", psutil_proc_cred, METH_VARARGS,
     "Return process uids/gids."},
#ifdef CURR_VERSION_THREAD
    {"proc_threads", psutil_proc_threads, METH_VARARGS,
     "Return process threads"},
#endif
#ifdef CURR_VERSION_PROCESS
    {"proc_io_counters", psutil_proc_io_counters, METH_VARARGS,
     "Get process I/O counters."},
#endif
    {"proc_num_ctx_switches", psutil_proc_num_ctx_switches, METH_VARARGS,
     "Get process I/O counters."},

    // --- system-related functions
    {"users", psutil_users, METH_VARARGS,
     "Return currently connected users."},
    {"disk_partitions", psutil_disk_partitions, METH_VARARGS,
     "Return disk partitions."},
    {"boot_time", psutil_boot_time, METH_VARARGS,
     "Return system boot time in seconds since the EPOCH."},
    {"per_cpu_times", psutil_per_cpu_times, METH_VARARGS,
     "Return system per-cpu times as a list of tuples"},
    {"disk_io_counters", psutil_disk_io_counters, METH_VARARGS,
     "Return a Python dict of tuples for disk I/O statistics."},
    {"virtual_mem", psutil_virtual_mem, METH_VARARGS,
     "Return system virtual memory usage statistics"},
    {"swap_mem", psutil_swap_mem, METH_VARARGS,
     "Return stats about swap memory, in bytes"},
#if defined(CURR_VERSION_NETINTERFACE) && CURR_VERSION_NETINTERFACE >= 3
    {"net_io_counters", psutil_net_io_counters, METH_VARARGS,
     "Return a Python dict of tuples for network I/O statistics."},
#endif
    {"net_connections", psutil_net_connections, METH_VARARGS,
     "Return system-wide connections"},
    {"net_if_stats", psutil_net_if_stats, METH_VARARGS,
     "Return NIC stats (isup, mtu)"},
    {"cpu_stats", psutil_cpu_stats, METH_VARARGS,
     "Return CPU statistics"},

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
    "psutil_aix",
    NULL,
    sizeof(struct module_state),
    PsutilMethods,
    NULL,
    psutil_aix_traverse,
    psutil_aix_clear,
    NULL
};

#define INITERROR return NULL

PyMODINIT_FUNC PyInit__psutil_aix(void)

#else
#define INITERROR return

void init_psutil_aix(void)
#endif
{
#if PY_MAJOR_VERSION >= 3
    PyObject *module = PyModule_Create(&moduledef);
#else
    PyObject *module = Py_InitModule("_psutil_aix", PsutilMethods);
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
