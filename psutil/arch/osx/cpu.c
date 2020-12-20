/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

/*
Notes:

- https://opensource.apple.com/source/xnu/xnu-1456.1.26/bsd/sys/sysctl.h.auto.html
- sysctl C types: https://ss64.com/osx/sysctl.html
- https://apple.stackexchange.com/questions/238777
- it looks like CPU "sockets" on macOS are called "packages"
- it looks like macOS does not support NUMA nodes:
  https://apple.stackexchange.com/questions/36465/do-mac-pros-use-numa
*/


#include <Python.h>
#include <sys/sysctl.h>

#include "../../_psutil_common.h"
#include "../../_psutil_posix.h"


// Add a new python object to an existing dict, DECREFing that object and
// setting it to NULL both in case of success or failure.
static int
psutil_add_to_dict(PyObject *py_dict, char *keyname, PyObject *py_obj) {
    if (!py_obj)
        return 1;
    if (PyDict_SetItemString(py_dict, keyname, py_obj)) {
        Py_CLEAR(py_obj);
        return 1;
    }
    Py_CLEAR(py_obj);
    return 0;
}


static PyObject *
psutil_cpu_model() {
    size_t len;
    char *buffer;
    PyObject *py_str = NULL;

    if (sysctlbyname("machdep.cpu.brand_string", NULL, &len, NULL, 0) != 0) {
        psutil_debug("sysctlbyname('machdep.cpu.brand_string') "
                     "failed (ignored)");
        Py_RETURN_NONE;
    }

    buffer = malloc(len);
    if (sysctlbyname("machdep.cpu.brand_string", buffer, &len, NULL, 0) != 0) {
        free(buffer);
        psutil_debug("sysctlbyname('machdep.cpu.brand_string') "
                     "failed (ignored)");
        Py_RETURN_NONE;
    }

    py_str = Py_BuildValue("s", buffer);
    free(buffer);
    return py_str;
}


static PyObject *
psutil_cpu_vendor() {
    size_t len;
    char *buffer;
    PyObject *py_str = NULL;

    if (sysctlbyname("machdep.cpu.vendor", NULL, &len, NULL, 0) != 0) {
        psutil_debug("sysctlbyname('machdep.cpu.vendor') failed (ignored)");
        Py_RETURN_NONE;
    }

    buffer = malloc(len);
    if (sysctlbyname("machdep.cpu.vendor", buffer, &len, NULL, 0) != 0) {
        free(buffer);
        psutil_debug("sysctlbyname('machdep.cpu.vendor') failed (ignored)");
        Py_RETURN_NONE;
    }

    py_str = Py_BuildValue("s", buffer);
    free(buffer);
    return py_str;
}


static PyObject *
psutil_cpu_features() {
    size_t len;
    char *buffer;
    PyObject *py_str = NULL;

    if (sysctlbyname("machdep.cpu.features", NULL, &len, NULL, 0) != 0) {
        psutil_debug("sysctlbyname('machdep.cpu.features') failed (ignored)");
        Py_RETURN_NONE;
    }

    buffer = malloc(len);
    if (sysctlbyname("machdep.cpu.features", buffer, &len, NULL, 0) != 0) {
        free(buffer);
        psutil_debug("sysctlbyname('machdep.cpu.features') failed (ignored)");
        Py_RETURN_NONE;
    }

    py_str = Py_BuildValue("s", buffer);
    free(buffer);
    return py_str;
}


static PyObject *
psutil_cpu_num_cores_per_socket() {
    unsigned int value;
    size_t size = sizeof(value);

    if (sysctlbyname("machdep.cpu.cores_per_package",
                     &value, &size, NULL, 0) != 0) {
        psutil_debug("sysctlbyname('machdep.cpu.cores_per_package') "
                     "failed (ignored)");
        Py_RETURN_NONE;
    }
    return Py_BuildValue("I", value);
}


// "threads_per_core" is how it's being called by lscpu on Linux.
// Here it's "thread_count". Hopefully it's the same thing.
static PyObject *
psutil_cpu_threads_per_core() {
    unsigned int value;
    size_t size = sizeof(value);

    if (sysctlbyname("machdep.cpu.thread_count",
                     &value, &size, NULL, 0) != 0) {
        psutil_debug("sysctlbyname('machdep.cpu.thread_count') "
                     "failed (ignored)");
        Py_RETURN_NONE;
    }
    return Py_BuildValue("I", value);
}


// The number of physical CPU sockets.
// It looks like on macOS "sockets" are called "packages".
// Hopefully it's the same thing.
static PyObject *
psutil_cpu_sockets() {
    unsigned int value;
    size_t size = sizeof(value);

    if (sysctlbyname("hw.packages", &value, &size, NULL, 2)) {
        psutil_debug("sysctlbyname('hw.packages') failed (ignored)");
        Py_RETURN_NONE;
    }
    return Py_BuildValue("I", value);
}


// also available as sysctlbyname("hw.l1icachesize") but it returns 1
static PyObject *
psutil_cpu_l1i_cache() {
    int value;
    size_t len = sizeof(value);
    int mib[2] = { CTL_HW, HW_L1ICACHESIZE };

    if (sysctl(mib, 2, &value, &len, NULL, 0) < 0) {
        psutil_debug("sysctl(HW_L1ICACHESIZE) failed (ignored)");
        Py_RETURN_NONE;
    }
    return Py_BuildValue("i", value);
}


// also available as sysctlbyname("hw.l1dcachesize") but it returns 1
static PyObject *
psutil_cpu_l1d_cache() {
    int value;
    size_t len = sizeof(value);
    int mib[2] = { CTL_HW, HW_L1DCACHESIZE };

    if (sysctl(mib, 2, &value, &len, NULL, 0) < 0) {
        psutil_debug("sysctl(HW_L1DCACHESIZE) failed (ignored)");
        Py_RETURN_NONE;
    }
    return Py_BuildValue("i", value);
}


// also available as sysctlbyname("hw.l2cachesize") but it returns 1
static PyObject *
psutil_cpu_l2_cache() {
    int value;
    size_t len = sizeof(value);
    int mib[2] = { CTL_HW, HW_L2CACHESIZE };

    if (sysctl(mib, 2, &value, &len, NULL, 0) < 0) {
        psutil_debug("sysctl(HW_L2CACHESIZE) failed (ignored)");
        Py_RETURN_NONE;
    }
    return Py_BuildValue("i", value);
}


// also available as sysctlbyname("hw.l3cachesize") but it returns 1
static PyObject *
psutil_cpu_l3_cache() {
    int value;
    size_t len = sizeof(value);
    int mib[2] = { CTL_HW, HW_L3CACHESIZE };

    if (sysctl(mib, 2, &value, &len, NULL, 0) < 0) {
        psutil_debug("sysctl(HW_L3CACHESIZE) failed (ignored)");
        Py_RETURN_NONE;
    }
    return Py_BuildValue("i", value);
}


// Retrieve multiple hardware CPU information, similarly to lscpu on Linux.
PyObject *
psutil_cpu_info(PyObject *self, PyObject *args) {
    PyObject *py_retdict = PyDict_New();

    if (py_retdict == NULL) {
        return NULL;
    }
    if (psutil_add_to_dict(py_retdict, "model",
                           psutil_cpu_model()) == 1) {
        goto error;
    }
    if (psutil_add_to_dict(py_retdict, "vendor",
                           psutil_cpu_vendor()) == 1) {
        goto error;
    }
    if (psutil_add_to_dict(py_retdict, "features",
                               psutil_cpu_features()) == 1) {
        goto error;
    }
    // various kinds of CPU counts
    if (psutil_add_to_dict(py_retdict, "threads_per_core",
                           psutil_cpu_threads_per_core()) == 1) {
        goto error;
    }
    if (psutil_add_to_dict(py_retdict, "cores_per_socket",
                           psutil_cpu_num_cores_per_socket()) == 1) {
        goto error;
    }
    if (psutil_add_to_dict(py_retdict, "sockets",
                           psutil_cpu_sockets()) == 1) {
        goto error;
    }
    // L* caches
    if (psutil_add_to_dict(py_retdict, "l1d_cache",
                           psutil_cpu_l1d_cache()) == 1) {
        goto error;
    }
    if (psutil_add_to_dict(py_retdict, "l1i_cache",
                           psutil_cpu_l1i_cache()) == 1) {
        goto error;
    }
    if (psutil_add_to_dict(py_retdict, "l2_cache",
                           psutil_cpu_l2_cache()) == 1) {
        goto error;
    }
    if (psutil_add_to_dict(py_retdict, "l3_cache",
                           psutil_cpu_l3_cache()) == 1) {
        goto error;
    }

    return py_retdict;

error:
    Py_DECREF(py_retdict);
    return NULL;
}
