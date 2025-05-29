/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Windows platform-specific module methods for _psutil_windows.
 *
 * List of undocumented Windows NT APIs which are used in here and in
 * other modules:
 * - NtQuerySystemInformation
 * - NtQueryInformationProcess
 * - NtQueryObject
 * - NtSuspendProcess
 * - NtResumeProcess
 */

#include <Python.h>
#include <windows.h>

#include "arch/all/init.h"
#include "arch/windows/cpu.h"
#include "arch/windows/disk.h"
#include "arch/windows/init.h"
#include "arch/windows/mem.h"
#include "arch/windows/net.h"
#include "arch/windows/proc.h"
#include "arch/windows/proc_handles.h"
#include "arch/windows/proc_info.h"
#include "arch/windows/proc_utils.h"
#include "arch/windows/security.h"
#include "arch/windows/sensors.h"
#include "arch/windows/services.h"
#include "arch/windows/socks.h"
#include "arch/windows/sys.h"
#include "arch/windows/wmi.h"


#define GETSTATE(m) ((struct module_state*)PyModule_GetState(m))


// ------------------------ Python init ---------------------------

static PyMethodDef
PsutilMethods[] = {
    // --- per-process functions
    {"proc_cmdline", (PyCFunction)(void(*)(void))psutil_proc_cmdline,
     METH_VARARGS | METH_KEYWORDS},
    {"proc_cpu_affinity_get", psutil_proc_cpu_affinity_get, METH_VARARGS},
    {"proc_cpu_affinity_set", psutil_proc_cpu_affinity_set, METH_VARARGS},
    {"proc_cwd", psutil_proc_cwd, METH_VARARGS},
    {"proc_environ", psutil_proc_environ, METH_VARARGS},
    {"proc_exe", psutil_proc_exe, METH_VARARGS},
    {"proc_io_counters", psutil_proc_io_counters, METH_VARARGS},
    {"proc_io_priority_get", psutil_proc_io_priority_get, METH_VARARGS},
    {"proc_io_priority_set", psutil_proc_io_priority_set, METH_VARARGS},
    {"proc_is_suspended", psutil_proc_is_suspended, METH_VARARGS},
    {"proc_kill", psutil_proc_kill, METH_VARARGS},
    {"proc_memory_info", psutil_proc_memory_info, METH_VARARGS},
    {"proc_memory_maps", psutil_proc_memory_maps, METH_VARARGS},
    {"proc_memory_uss", psutil_proc_memory_uss, METH_VARARGS},
    {"proc_num_handles", psutil_proc_num_handles, METH_VARARGS},
    {"proc_open_files", psutil_proc_open_files, METH_VARARGS},
    {"proc_priority_get", psutil_proc_priority_get, METH_VARARGS},
    {"proc_priority_set", psutil_proc_priority_set, METH_VARARGS},
    {"proc_suspend_or_resume", psutil_proc_suspend_or_resume, METH_VARARGS},
    {"proc_threads", psutil_proc_threads, METH_VARARGS},
    {"proc_times", psutil_proc_times, METH_VARARGS},
    {"proc_username", psutil_proc_username, METH_VARARGS},
    {"proc_wait", psutil_proc_wait, METH_VARARGS},

    // --- alternative pinfo interface
    {"proc_info", psutil_proc_info, METH_VARARGS},

    // --- system-related functions
    {"uptime", psutil_uptime, METH_VARARGS},
    {"cpu_count_cores", psutil_cpu_count_cores, METH_VARARGS},
    {"cpu_count_logical", psutil_cpu_count_logical, METH_VARARGS},
    {"cpu_freq", psutil_cpu_freq, METH_VARARGS},
    {"cpu_stats", psutil_cpu_stats, METH_VARARGS},
    {"cpu_times", psutil_cpu_times, METH_VARARGS},
    {"disk_io_counters", psutil_disk_io_counters, METH_VARARGS},
    {"disk_partitions", psutil_disk_partitions, METH_VARARGS},
    {"disk_usage", psutil_disk_usage, METH_VARARGS},
    {"getloadavg", (PyCFunction)psutil_get_loadavg, METH_VARARGS},
    {"getpagesize", psutil_getpagesize, METH_VARARGS},
    {"swap_percent", psutil_swap_percent, METH_VARARGS},
    {"init_loadavg_counter", (PyCFunction)psutil_init_loadavg_counter, METH_VARARGS},
    {"net_connections", psutil_net_connections, METH_VARARGS},
    {"net_if_addrs", psutil_net_if_addrs, METH_VARARGS},
    {"net_if_stats", psutil_net_if_stats, METH_VARARGS},
    {"net_io_counters", psutil_net_io_counters, METH_VARARGS},
    {"per_cpu_times", psutil_per_cpu_times, METH_VARARGS},
    {"pid_exists", psutil_pid_exists, METH_VARARGS},
    {"pids", psutil_pids, METH_VARARGS},
    {"ppid_map", psutil_ppid_map, METH_VARARGS},
    {"sensors_battery", psutil_sensors_battery, METH_VARARGS},
    {"users", psutil_users, METH_VARARGS},
    {"virtual_mem", psutil_virtual_mem, METH_VARARGS},

    // --- windows services
    {"winservice_enumerate", psutil_winservice_enumerate, METH_VARARGS},
    {"winservice_query_config", psutil_winservice_query_config, METH_VARARGS},
    {"winservice_query_descr", psutil_winservice_query_descr, METH_VARARGS},
    {"winservice_query_status", psutil_winservice_query_status, METH_VARARGS},
    {"winservice_start", psutil_winservice_start, METH_VARARGS},
    {"winservice_stop", psutil_winservice_stop, METH_VARARGS},

    // --- windows API bindings
    {"QueryDosDevice", psutil_QueryDosDevice, METH_VARARGS},

    // --- others
    {"check_pid_range", psutil_check_pid_range, METH_VARARGS},
    {"set_debug", psutil_set_debug, METH_VARARGS},

    {NULL, NULL, 0, NULL}
};


struct module_state {
    PyObject *error;
};


static int
psutil_windows_traverse(PyObject *m, visitproc visit, void *arg) {
    Py_VISIT(GETSTATE(m)->error);
    return 0;
}

static int
psutil_windows_clear(PyObject *m) {
    Py_CLEAR(GETSTATE(m)->error);
    return 0;
}

static int module_loaded = 0;

static int
_psutil_windows_exec(PyObject *mod) {
    // https://docs.python.org/3/howto/isolating-extensions.html#opt-out-limiting-to-one-module-object-per-process
    if (module_loaded) {
        PyErr_SetString(PyExc_ImportError,
                        "cannot load module more than once per process");
        return -1;
    }
    module_loaded = 1;

    if (psutil_setup() != 0)
        return -1;
    if (psutil_setup_windows() != 0)
        return -1;
    if (psutil_set_se_debug() != 0)
        return -1;

    // Exceptions
    TimeoutExpired = PyErr_NewException(
        "_psutil_windows.TimeoutExpired", NULL, NULL);
    if (TimeoutExpired == NULL)
        return -1;
    Py_INCREF(TimeoutExpired);
    if (PyModule_AddObject(mod, "TimeoutExpired", TimeoutExpired))
        return -1;

    TimeoutAbandoned = PyErr_NewException(
        "_psutil_windows.TimeoutAbandoned", NULL, NULL);
    if (TimeoutAbandoned == NULL)
        return -1;
    Py_INCREF(TimeoutAbandoned);
    if (PyModule_AddObject(mod, "TimeoutAbandoned", TimeoutAbandoned))
        return -1;

    // version constant
    if (PyModule_AddIntConstant(mod, "version", PSUTIL_VERSION))
        return -1;

    // process status constants
    // http://msdn.microsoft.com/en-us/library/ms683211(v=vs.85).aspx
    if (PyModule_AddIntConstant(mod, "ABOVE_NORMAL_PRIORITY_CLASS", ABOVE_NORMAL_PRIORITY_CLASS))
        return -1;
    if (PyModule_AddIntConstant(mod, "BELOW_NORMAL_PRIORITY_CLASS", BELOW_NORMAL_PRIORITY_CLASS))
        return -1;
    if (PyModule_AddIntConstant(mod, "HIGH_PRIORITY_CLASS", HIGH_PRIORITY_CLASS))
        return -1;
    if (PyModule_AddIntConstant(mod, "IDLE_PRIORITY_CLASS", IDLE_PRIORITY_CLASS))
        return -1;
    if (PyModule_AddIntConstant(mod, "NORMAL_PRIORITY_CLASS", NORMAL_PRIORITY_CLASS))
        return -1;
    if (PyModule_AddIntConstant(mod, "REALTIME_PRIORITY_CLASS", REALTIME_PRIORITY_CLASS))
        return -1;

    // connection status constants
    // http://msdn.microsoft.com/en-us/library/cc669305.aspx
    if (PyModule_AddIntConstant(mod, "MIB_TCP_STATE_CLOSED", MIB_TCP_STATE_CLOSED))
        return -1;
    if (PyModule_AddIntConstant(mod, "MIB_TCP_STATE_CLOSING", MIB_TCP_STATE_CLOSING))
        return -1;
    if (PyModule_AddIntConstant(mod, "MIB_TCP_STATE_CLOSE_WAIT", MIB_TCP_STATE_CLOSE_WAIT))
        return -1;
    if (PyModule_AddIntConstant(mod, "MIB_TCP_STATE_LISTEN", MIB_TCP_STATE_LISTEN))
        return -1;
    if (PyModule_AddIntConstant(mod, "MIB_TCP_STATE_ESTAB", MIB_TCP_STATE_ESTAB))
        return -1;
    if (PyModule_AddIntConstant(mod, "MIB_TCP_STATE_SYN_SENT", MIB_TCP_STATE_SYN_SENT))
        return -1;
    if (PyModule_AddIntConstant(mod, "MIB_TCP_STATE_SYN_RCVD", MIB_TCP_STATE_SYN_RCVD))
        return -1;
    if (PyModule_AddIntConstant(mod, "MIB_TCP_STATE_FIN_WAIT1", MIB_TCP_STATE_FIN_WAIT1))
        return -1;
    if (PyModule_AddIntConstant(mod, "MIB_TCP_STATE_FIN_WAIT2", MIB_TCP_STATE_FIN_WAIT2))
        return -1;
    if (PyModule_AddIntConstant(mod, "MIB_TCP_STATE_LAST_ACK", MIB_TCP_STATE_LAST_ACK))
        return -1;
    if (PyModule_AddIntConstant(mod, "MIB_TCP_STATE_TIME_WAIT", MIB_TCP_STATE_TIME_WAIT))
        return -1;
    if (PyModule_AddIntConstant(mod, "MIB_TCP_STATE_TIME_WAIT", MIB_TCP_STATE_TIME_WAIT))
        return -1;
    if (PyModule_AddIntConstant(mod, "MIB_TCP_STATE_DELETE_TCB", MIB_TCP_STATE_DELETE_TCB))
        return -1;
    if (PyModule_AddIntConstant(mod, "PSUTIL_CONN_NONE", PSUTIL_CONN_NONE))
        return -1;

    // ...for internal use in _psutil_windows.py
    if (PyModule_AddIntConstant(mod, "INFINITE", INFINITE))
        return -1;
    if (PyModule_AddIntConstant(mod, "ERROR_ACCESS_DENIED", ERROR_ACCESS_DENIED))
        return -1;
    if (PyModule_AddIntConstant(mod, "ERROR_INVALID_NAME", ERROR_INVALID_NAME))
        return -1;
    if (PyModule_AddIntConstant(mod, "ERROR_SERVICE_DOES_NOT_EXIST", ERROR_SERVICE_DOES_NOT_EXIST))
        return -1;
    if (PyModule_AddIntConstant(mod, "ERROR_PRIVILEGE_NOT_HELD", ERROR_PRIVILEGE_NOT_HELD))
        return -1;
    if (PyModule_AddIntConstant(mod, "WINVER", PSUTIL_WINVER))
        return -1;
    if (PyModule_AddIntConstant(mod, "WINDOWS_VISTA", PSUTIL_WINDOWS_VISTA))
        return -1;
    if (PyModule_AddIntConstant(mod, "WINDOWS_7", PSUTIL_WINDOWS_7))
        return -1;
    if (PyModule_AddIntConstant(mod, "WINDOWS_8", PSUTIL_WINDOWS_8))
        return -1;
    if (PyModule_AddIntConstant(mod, "WINDOWS_8_1", PSUTIL_WINDOWS_8_1))
        return -1;
    if (PyModule_AddIntConstant(mod, "WINDOWS_10", PSUTIL_WINDOWS_10))
        return -1;

    return 0;
}

static struct PyModuleDef_Slot _psutil_windows_slots[] = {
    {Py_mod_exec, _psutil_windows_exec},
#ifdef Py_mod_multiple_interpreters  // Python 3.12+
    {Py_mod_multiple_interpreters, Py_MOD_MULTIPLE_INTERPRETERS_NOT_SUPPORTED},
#endif
#ifdef Py_mod_gil  // Python 3.13+
    // signal that this module supports running without an active GIL
    {Py_mod_gil, Py_MOD_GIL_NOT_USED},
#endif
    {0, NULL},
};

static struct PyModuleDef module_def = {
    .m_base = PyModuleDef_HEAD_INIT,
    .m_name = "_psutil_windows",
    .m_size = sizeof(struct module_state),
    .m_methods = mod_methods,
    .m_slots = _psutil_windows_slots,
    .m_traverse = psutil_windows_traverse,
    .m_clear = psutil_windows_clear,
};

PyMODINIT_FUNC
PyInit__psutil_windows(void) {
    return PyModuleDef_Init(&module_def);
}
