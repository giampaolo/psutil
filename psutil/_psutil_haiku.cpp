/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * macOS platform-specific module methods.
 */

#include <Python.h>
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
#include <arpa/inet.h>
#include <net/if_dl.h>
#include <pwd.h>

#include <fs_info.h>
#include <image.h>
#include <Directory.h>
#include <OS.h>
#include <Path.h>
#include <String.h>
#include <Volume.h>

extern "C" {

#include "_psutil_common.h"
#include "_psutil_posix.h"
//#include "arch/haiku/process_info.h"

}

static PyObject *ZombieProcessError;


/*
 * Return a Python list of all the PIDs running on the system.
 */
static PyObject *
psutil_pids(PyObject *self, PyObject *args) {
    int32 cookie = 0;
    team_info info;
    PyObject *py_pid = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;

    while (get_next_team_info(&cookie, &info) == B_OK) {
        /* quite wasteful: we have all team infos already */
        py_pid = PyLong_FromPid(info.team);
        if (! py_pid)
            goto error;
        if (PyList_Append(py_retlist, py_pid))
            goto error;
        Py_CLEAR(py_pid);
    }

    return py_retlist;

error:
    Py_XDECREF(py_pid);
    Py_DECREF(py_retlist);
    return NULL;
}


/*
 * Return multiple process info as a Python tuple in one shot by
 * using get_team_info() and filling up a team_info struct.
 */
static PyObject *
psutil_proc_team_info_oneshot(PyObject *self, PyObject *args) {
    pid_t pid;
    team_info info;
    PyObject *py_name;
    PyObject *py_retlist;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (get_team_info(pid, &info) != B_OK)
        return NULL;

    py_name = PyUnicode_DecodeFSDefault(info.args);
    if (! py_name) {
        // Likely a decoding error. We don't want to fail the whole
        // operation. The python module may retry with proc_name().
        PyErr_Clear();
        py_name = Py_None;
    }

    py_retlist = Py_BuildValue(
        "lllllO",
        (long)info.thread_count,                   // (long) thread_count
        (long)info.image_count,                    // (long) image_count
        (long)info.area_count,                     // (long) area_count
        (long)info.uid,                            // (long) uid
        (long)info.gid,                            // (long) gid
        py_name                                    // (pystr) name
    );

    if (py_retlist != NULL) {
        // XXX shall we decref() also in case of Py_BuildValue() error?
        Py_DECREF(py_name);
    }
    return py_retlist;
}


/*
 * Return multiple process info as a Python tuple in one shot by
 * using get_team_usage_info() and filling up a team_usage_info struct.
 */
static PyObject *
psutil_proc_team_usage_info_oneshot(PyObject *self, PyObject *args) {
    pid_t pid;
    team_usage_info info;
    PyObject *py_retlist;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (get_team_usage_info(pid, B_TEAM_USAGE_SELF, &info) != B_OK)
        return NULL;

    py_retlist = Py_BuildValue(
        "KK",
        (unsigned long long)info.user_time,
        (unsigned long long)info.kernel_time
    );

    return py_retlist;
}


/*
 * Return process name from kinfo_proc as a Python string.
 */
static PyObject *
psutil_proc_name(PyObject *self, PyObject *args) {
    pid_t pid;
    team_info info;
    PyObject *py_name;
    PyObject *py_retlist;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (get_team_info(pid, &info) != B_OK)
        return NULL;

    return PyUnicode_DecodeFSDefault(info.args);
}


/*
 * Return process current working directory.
 * Raises NSP in case of zombie process.
 */
static PyObject *
psutil_proc_cwd(PyObject *self, PyObject *args) {
    /* TODO */
    return NULL;
}


/*
 * Return path of the process executable.
 */
static PyObject *
psutil_proc_exe(PyObject *self, PyObject *args) {
    pid_t pid;
    image_info info;
    int32 cookie = 0;
    PyObject *py_name;
    PyObject *py_retlist;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    while (get_next_image_info(pid, &cookie, &info) == B_OK) {
        if (info.type != B_APP_IMAGE)
            continue;
        return PyUnicode_DecodeFSDefault(info.name);
    }
    return NULL;
}


/*
 * Return process cmdline as a Python list of cmdline arguments.
 */
static PyObject *
psutil_proc_cmdline(PyObject *self, PyObject *args) {
    return Py_BuildValue("[]");
    /* TODO! */
    pid_t pid;
    team_info info;
    PyObject *py_arg;
    PyObject *py_retlist = NULL;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (get_team_info(pid, &info) != B_OK)
        return NULL;

    py_retlist = PyList_New(0);
    if (py_retlist == NULL)
        return NULL;

    /* TODO: we can't really differentiate args as we have a single string */
    /* TODO: try to split? */
    py_arg = PyUnicode_DecodeFSDefault(info.args);
    if (!py_arg)
        goto error;
    if (PyList_Append(py_retlist, py_arg))
        goto error;

    return Py_BuildValue("N", py_retlist);

error:
    Py_XDECREF(py_arg);
    Py_DECREF(py_retlist);
    return NULL;
}


/*
 * Return process environment as a Python string.
 */
static PyObject *
psutil_proc_environ(PyObject *self, PyObject *args) {
    /* TODO: likely impossible */
    return NULL;
}


/*
 * Return the number of logical CPUs in the system.
 */
static PyObject *
psutil_cpu_count_logical(PyObject *self, PyObject *args) {
    /* TODO:get_cpu_topology_info */
    return NULL;
}


/*
 * Return the number of physical CPUs in the system.
 */
static PyObject *
psutil_cpu_count_phys(PyObject *self, PyObject *args) {
    /* TODO:get_cpu_topology_info */
    return NULL;
}


/*
 * Returns the USS (unique set size) of the process. Reference:
 * https://dxr.mozilla.org/mozilla-central/source/xpcom/base/
 *     nsMemoryReporterManager.cpp
 */
static PyObject *
psutil_proc_memory_uss(PyObject *self, PyObject *args) {
    /* TODO */
    return NULL;
}


/*
 * Return system virtual memory stats.
 * See:
 * https://opensource.apple.com/source/system_cmds/system_cmds-790/
 *     vm_stat.tproj/vm_stat.c.auto.html
 */
static PyObject *
psutil_virtual_mem(PyObject *self, PyObject *args) {
    system_info info;
    status_t ret;
    int pagesize = getpagesize();

    
    ret = get_system_info(&info);
    if (ret != B_OK) {
        PyErr_Format(
            PyExc_RuntimeError, "get_system_info() syscall failed: %s",
            strerror(ret));
        return NULL;
    }

    return Py_BuildValue(
        "KKKKKKK",
        (unsigned long long) info.max_pages * pagesize,  // total
        (unsigned long long) info.used_pages * pagesize,  // used
        (unsigned long long) info.cached_pages * pagesize,  // cached
        (unsigned long long) info.block_cache_pages * pagesize,  // buffers
        (unsigned long long) info.ignored_pages * pagesize,  // ignored
        (unsigned long long) info.needed_memory,  // needed
        (unsigned long long) info.free_memory  // available
    );
}


/*
 * Return stats about swap memory.
 */
static PyObject *
psutil_swap_mem(PyObject *self, PyObject *args) {
    system_info info;
    status_t ret;
    int pagesize = getpagesize();

    
    ret = get_system_info(&info);
    if (ret != B_OK) {
        PyErr_Format(
            PyExc_RuntimeError, "get_system_info() syscall failed: %s",
            strerror(ret));
        return NULL;
    }

    return Py_BuildValue(
        "KK",
        (unsigned long long) info.max_swap_pages * pagesize,
        (unsigned long long) info.free_swap_pages * pagesize);
        /* XXX: .page_faults? */
}


/*
 * Return a Python tuple representing user, kernel and idle CPU times
 */
static PyObject *
psutil_cpu_times(PyObject *self, PyObject *args) {
    system_info info;
    status_t ret;
    int pagesize = getpagesize();

    ret = get_system_info(&info);
    if (ret != B_OK) {
        PyErr_Format(
            PyExc_RuntimeError, "get_system_info() syscall failed: %s",
            strerror(ret));
        return NULL;
    }

    cpu_info cpus[info.cpu_count];

    ret = get_cpu_info(0, info.cpu_count, cpus);
    if (ret != B_OK) {
        PyErr_Format(
            PyExc_RuntimeError, "get_cpu_info() syscall failed: %s",
            strerror(ret));
        return NULL;
    }

    /* TODO */
    return Py_BuildValue(
        "(dddd)",
        (double)0.0,
        (double)0.0,
        (double)0.0,
        (double)0.0
    );
}


/*
 * Return a Python list of tuple representing per-cpu times
 */
static PyObject *
psutil_per_cpu_times(PyObject *self, PyObject *args) {
    system_info info;
    status_t ret;
    uint32 i, pagesize = getpagesize();
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_cputime = NULL;

    ret = get_system_info(&info);
    if (ret != B_OK) {
        PyErr_Format(
            PyExc_RuntimeError, "get_system_info() syscall failed: %s",
            strerror(ret));
        return NULL;
    }

    cpu_info cpus[info.cpu_count];

    ret = get_cpu_info(0, info.cpu_count, cpus);
    if (ret != B_OK) {
        PyErr_Format(
            PyExc_RuntimeError, "get_cpu_info() syscall failed: %s",
            strerror(ret));
        return NULL;
    }

    /* TODO: check idle thread times? */

    for (i = 0; i < info.cpu_count; i++) {
        py_cputime = Py_BuildValue(
            "(dddd)",
            (double)0.0,
            (double)0.0,
            (double)0.0,
            (double)0.0
        );
        if (!py_cputime)
            goto error;
        if (PyList_Append(py_retlist, py_cputime))
            goto error;
        Py_CLEAR(py_cputime);
    }
    return py_retlist;

error:
    Py_XDECREF(py_cputime);
    Py_DECREF(py_retlist);
    return NULL;
}


/*
 * Retrieve CPU frequency.
 */
static PyObject *
psutil_cpu_freq(PyObject *self, PyObject *args) {
    status_t ret;
	uint32 i, topologyNodeCount = 0;
	ret = get_cpu_topology_info(NULL, &topologyNodeCount);
	if (ret != B_OK || topologyNodeCount == 0)
	    return NULL;
    cpu_topology_node_info topology[topologyNodeCount];
	ret = get_cpu_topology_info(topology, &topologyNodeCount);

	for (i = 0; i < topologyNodeCount; i++) {
	    if (topology[i].type == B_TOPOLOGY_CORE)
            /* TODO: find min / max? */
            return Py_BuildValue(
                "KKK",
                topology[i].data.core.default_frequency,
                topology[i].data.core.default_frequency,
                topology[i].data.core.default_frequency);
	}

    return NULL;
}


/*
 * Return a Python float indicating the system boot time expressed in
 * seconds since the epoch.
 */
static PyObject *
psutil_boot_time(PyObject *self, PyObject *args) {
    system_info info;
    status_t ret;
    int pagesize = getpagesize();

    ret = get_system_info(&info);
    if (ret != B_OK) {
        PyErr_Format(
            PyExc_RuntimeError, "get_system_info() syscall failed: %s",
            strerror(ret));
        return NULL;
    }

    return Py_BuildValue("f", (float)info.boot_time / 1000000.0);
}


/*
 * Return a list of tuples including device, mount point and fs type
 * for all partitions mounted on the system.
 */
static PyObject *
psutil_disk_partitions(PyObject *self, PyObject *args) {
    int32 cookie = 0;
    dev_t dev;
    fs_info info;
    uint32 flags;
    BString opts;
    PyObject *py_dev = NULL;
    PyObject *py_mountp = NULL;
    PyObject *py_tuple = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;

    while ((dev = next_dev(&cookie)) >= 0) {
        opts = "";
        if (fs_stat_dev(dev, &info) != B_OK)
            continue;
        flags = info.flags;

        // see fs_info.h
        if (flags & B_FS_IS_READONLY)
            opts << "ro";
        else
            opts << "rw";
        // TODO
        if (flags & B_FS_IS_REMOVABLE)
            opts << ",removable";
        if (flags & B_FS_IS_PERSISTENT)
            opts << ",persistent";
        if (flags & B_FS_IS_SHARED)
            opts << ",shared";
        if (flags & B_FS_HAS_MIME)
            opts << ",has_mime";
        if (flags & B_FS_HAS_ATTR)
            opts << ",has_attr";
        if (flags & B_FS_HAS_QUERY)
            opts << ",has_query";
        if (flags & B_FS_HAS_SELF_HEALING_LINKS)
            opts << ",has_self_healing_links";
        if (flags & B_FS_HAS_ALIASES)
            opts << ",has_aliases";
        if (flags & B_FS_SUPPORTS_NODE_MONITORING)
            opts << ",has_node_monitoring";
        if (flags & B_FS_SUPPORTS_MONITOR_CHILDREN)
            opts << ",cmdflags";

        py_dev = PyUnicode_DecodeFSDefault(info.device_name);
        if (! py_dev)
            goto error;
        /* for the mountpoint we must use higher-level API */
        BVolume volume(info.dev);
        BDirectory rootDir;
        if (volume.GetRootDirectory(&rootDir) == B_OK) {
            BPath path(&rootDir, NULL);
            if (path.InitCheck() == B_OK) {
                py_mountp = PyUnicode_DecodeFSDefault(path.Path());
                if (! py_mountp)
                    goto error;
            }
        }
        py_tuple = Py_BuildValue(
            "(OOss)",
            py_dev,               // device
            py_mountp,            // mount point
            info.fsh_name,        // fs type
            opts.String());       // options
        if (!py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_CLEAR(py_dev);
        Py_CLEAR(py_mountp);
        Py_CLEAR(py_tuple);
    }

    return py_retlist;

error:
    Py_XDECREF(py_dev);
    Py_XDECREF(py_mountp);
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    return NULL;
}


/*
 * Return process threads
 */
static PyObject *
psutil_proc_threads(PyObject *self, PyObject *args) {
    pid_t pid;
    int32 cookie = 0;
    thread_info info;
    int err, ret;
    PyObject *py_tuple = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;

    while (get_next_thread_info(pid, &cookie, &info) == B_OK) {
        py_tuple = Py_BuildValue(
            "Iffl",
            info.thread,
            (float)info.user_time / 1000000.0,
            (float)info.kernel_time / 1000000.0,
            (long)info.state
            //XXX: priority, ?
        );
        if (!py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_CLEAR(py_tuple);
    }

    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    return NULL;
}


/*
 * Return process open files as a Python tuple.
 * References:
 * - lsof source code: http://goo.gl/SYW79 and http://goo.gl/m78fd
 * - /usr/include/sys/proc_info.h
 */
static PyObject *
psutil_proc_open_files(PyObject *self, PyObject *args) {
    /* TODO */
    return NULL;
}


/*
 * Return process TCP and UDP connections as a list of tuples.
 * Raises NSP in case of zombie process.
 * References:
 * - lsof source code: http://goo.gl/SYW79 and http://goo.gl/wNrC0
 * - /usr/include/sys/proc_info.h
 */
static PyObject *
psutil_proc_connections(PyObject *self, PyObject *args) {
    /* TODO */
    return NULL;
}


/*
 * Return number of file descriptors opened by process.
 * Raises NSP in case of zombie process.
 */
static PyObject *
psutil_proc_num_fds(PyObject *self, PyObject *args) {
    /* TODO */
    return NULL;
}


/*
 * Return a Python list of named tuples with overall network I/O information
 */
static PyObject *
psutil_net_io_counters(PyObject *self, PyObject *args) {
    PyObject *py_retdict = PyDict_New();

    if (py_retdict == NULL)
        return NULL;


    /* TODO */
    return py_retdict;
}


/*
 * Return a Python dict of tuples for disk I/O information
 */
static PyObject *
psutil_disk_io_counters(PyObject *self, PyObject *args) {
    /* TODO */
    return NULL;
}


/*
 * Return currently connected users as a list of tuples.
 */
static PyObject *
psutil_users(PyObject *self, PyObject *args) {
    /* TODO */
    return NULL;
}


/*
 * Return CPU statistics.
 */
static PyObject *
psutil_cpu_stats(PyObject *self, PyObject *args) {
    /* TODO */
    return NULL;
}


/*
 * Return battery information.
 */
static PyObject *
psutil_sensors_battery(PyObject *self, PyObject *args) {
    /* TODO */
    return NULL;
}


/*
 * define the psutil C module methods and initialize the module.
 */
static PyMethodDef mod_methods[] = {
    // --- per-process functions

    {"proc_team_info_oneshot", psutil_proc_team_info_oneshot, METH_VARARGS,
     "Return multiple process info."},
    {"proc_team_usage_info_oneshot", psutil_proc_team_usage_info_oneshot, METH_VARARGS,
     "Return multiple process info."},
    {"proc_name", psutil_proc_name, METH_VARARGS,
     "Return process name"},
    {"proc_cmdline", psutil_proc_cmdline, METH_VARARGS,
     "Return process cmdline as a list of cmdline arguments"},
    {"proc_environ", psutil_proc_environ, METH_VARARGS,
     "Return process environment data"},
    {"proc_exe", psutil_proc_exe, METH_VARARGS,
     "Return path of the process executable"},
    {"proc_cwd", psutil_proc_cwd, METH_VARARGS,
     "Return process current working directory."},
    {"proc_memory_uss", psutil_proc_memory_uss, METH_VARARGS,
     "Return process USS memory"},
    {"proc_threads", psutil_proc_threads, METH_VARARGS,
     "Return process threads as a list of tuples"},
    {"proc_open_files", psutil_proc_open_files, METH_VARARGS,
     "Return files opened by process as a list of tuples"},
    {"proc_num_fds", psutil_proc_num_fds, METH_VARARGS,
     "Return the number of fds opened by process."},
    {"proc_connections", psutil_proc_connections, METH_VARARGS,
     "Get process TCP and UDP connections as a list of tuples"},

    // --- system-related functions

    {"pids", psutil_pids, METH_VARARGS,
     "Returns a list of PIDs currently running on the system"},
    {"cpu_count_logical", psutil_cpu_count_logical, METH_VARARGS,
     "Return number of logical CPUs on the system"},
    {"cpu_count_phys", psutil_cpu_count_phys, METH_VARARGS,
     "Return number of physical CPUs on the system"},
    {"virtual_mem", psutil_virtual_mem, METH_VARARGS,
     "Return system virtual memory stats"},
    {"swap_mem", psutil_swap_mem, METH_VARARGS,
     "Return stats about swap memory, in bytes"},
    {"cpu_times", psutil_cpu_times, METH_VARARGS,
     "Return system cpu times as a tuple (user, system, nice, idle, irc)"},
    {"per_cpu_times", psutil_per_cpu_times, METH_VARARGS,
     "Return system per-cpu times as a list of tuples"},
    {"cpu_freq", psutil_cpu_freq, METH_VARARGS,
     "Return cpu current frequency"},
    {"boot_time", psutil_boot_time, METH_VARARGS,
     "Return the system boot time expressed in seconds since the epoch."},
    {"disk_partitions", psutil_disk_partitions, METH_VARARGS,
     "Return a list of tuples including device, mount point and "
     "fs type for all partitions mounted on the system."},
    {"net_io_counters", psutil_net_io_counters, METH_VARARGS,
     "Return dict of tuples of networks I/O information."},
    /*{"disk_io_counters", psutil_disk_io_counters, METH_VARARGS,
     "Return dict of tuples of disks I/O information."},*/
    {"users", psutil_users, METH_VARARGS,
     "Return currently connected users as a list of tuples"},
    {"cpu_stats", psutil_cpu_stats, METH_VARARGS,
     "Return CPU statistics"},
    {"sensors_battery", psutil_sensors_battery, METH_VARARGS,
     "Return battery information."},

    // --- others
    {"set_testing", psutil_set_testing, METH_NOARGS,
     "Set psutil in testing mode"},

    {NULL, NULL, 0, NULL}
};


#if PY_MAJOR_VERSION >= 3
    #define INITERR return NULL

    static struct PyModuleDef moduledef = {
        PyModuleDef_HEAD_INIT,
        "_psutil_haiku",
        NULL,
        -1,
        mod_methods,
        NULL,
        NULL,
        NULL,
        NULL
    };

extern "C" PyObject *PyInit__psutil_haiku(void);

    PyObject *PyInit__psutil_haiku(void)
#else  /* PY_MAJOR_VERSION */
    #define INITERR return

extern "C" void init_psutil_haiku(void);

    void init_psutil_haiku(void)
#endif  /* PY_MAJOR_VERSION */
{
#if PY_MAJOR_VERSION >= 3
    PyObject *mod = PyModule_Create(&moduledef);
#else
    PyObject *mod = Py_InitModule("_psutil_haiku", mod_methods);
#endif
    if (mod == NULL)
        INITERR;

    if (psutil_setup() != 0)
        INITERR;

    if (PyModule_AddIntConstant(mod, "version", PSUTIL_VERSION))
        INITERR;
    // process status constants, defined in:
    // headers/os/kernel/OS.h
    if (PyModule_AddIntConstant(mod, "B_THREAD_RUNNING", B_THREAD_RUNNING))
        INITERR;
    if (PyModule_AddIntConstant(mod, "B_THREAD_READY", B_THREAD_READY))
        INITERR;
    if (PyModule_AddIntConstant(mod, "B_THREAD_RECEIVING", B_THREAD_RECEIVING))
        INITERR;
    if (PyModule_AddIntConstant(mod, "B_THREAD_ASLEEP", B_THREAD_ASLEEP))
        INITERR;
    if (PyModule_AddIntConstant(mod, "B_THREAD_SUSPENDED", B_THREAD_SUSPENDED))
        INITERR;
    if (PyModule_AddIntConstant(mod, "B_THREAD_WAITING", B_THREAD_WAITING))
        INITERR;
    // connection status constants
/*XXX:
    if (PyModule_AddIntConstant(mod, "TCPS_CLOSED", TCPS_CLOSED))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_CLOSING", TCPS_CLOSING))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_CLOSE_WAIT", TCPS_CLOSE_WAIT))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_LISTEN", TCPS_LISTEN))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_ESTABLISHED", TCPS_ESTABLISHED))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_SYN_SENT", TCPS_SYN_SENT))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_SYN_RECEIVED", TCPS_SYN_RECEIVED))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_FIN_WAIT_1", TCPS_FIN_WAIT_1))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_FIN_WAIT_2", TCPS_FIN_WAIT_2))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_LAST_ACK", TCPS_LAST_ACK))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_TIME_WAIT", TCPS_TIME_WAIT))
        INITERR;
*/
    if (PyModule_AddIntConstant(mod, "PSUTIL_CONN_NONE", PSUTIL_CONN_NONE))
        INITERR;

    if (mod == NULL)
        INITERR;
#if PY_MAJOR_VERSION >= 3
    return mod;
#endif
}
