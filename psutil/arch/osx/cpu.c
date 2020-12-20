/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
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
        psutil_debug("sysctlbyname('machdep.cpu.brand_string'), get len");
        Py_RETURN_NONE;
    }

    buffer = malloc(len);
    if (sysctlbyname("machdep.cpu.brand_string", buffer, &len, NULL, 0) != 0) {
        free(buffer);
        psutil_debug("sysctlbyname('machdep.cpu.brand_string'), get buf");
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
        psutil_debug("sysctlbyname('machdep.cpu.vendor'), get len");
        Py_RETURN_NONE;
    }

    buffer = malloc(len);
    if (sysctlbyname("machdep.cpu.vendor", buffer, &len, NULL, 0) != 0) {
        free(buffer);
        psutil_debug("sysctlbyname('machdep.cpu.vendor'), get buf");
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
        psutil_debug("sysctlbyname('machdep.cpu.features'), get len");
        Py_RETURN_NONE;
    }

    buffer = malloc(len);
    if (sysctlbyname("machdep.cpu.features", buffer, &len, NULL, 0) != 0) {
        free(buffer);
        psutil_debug("sysctlbyname('machdep.cpu.features'), get buf");
        Py_RETURN_NONE;
    }

    py_str = Py_BuildValue("s", buffer);
    free(buffer);
    return py_str;
}


// It looks like CPU "cores" on macOS are called "packages".
// In sys/sysctl.h we also have:
// <<hw.packages - Gives the number of processor packages>>
// https://opensource.apple.com/source/xnu/xnu-1456.1.26/bsd/
//     sys/sysctl.h.auto.html
static PyObject *
psutil_cpu_cores_per_socket() {
    unsigned int value;
    size_t size = sizeof(value);

    if (sysctlbyname("machdep.cpu.cores_per_package",
                     &value, &size, NULL, 0) != 0) {
        psutil_debug("sysct('machdep.cpu.cores_per_package')");
        Py_RETURN_NONE;
    }
    return Py_BuildValue("I", value);
}


// "threads_per_core" is how it's called by lscpu on Linux.
// Here it's "thread_count". Hopefully it's the same thing.
static PyObject *
psutil_cpu_threads_per_core() {
    unsigned int value;
    size_t size = sizeof(value);

    if (sysctlbyname("machdep.cpu.thread_count",
                     &value, &size, NULL, 0) != 0) {
        psutil_debug("sysct('machdep.cpu.thread_count')");
        Py_RETURN_NONE;
    }
    return Py_BuildValue("I", value);
}


// It looks like CPU "cores" on macOS are called "packages".
// https://opensource.apple.com/source/xnu/xnu-1456.1.26/bsd/
//     sys/sysctl.h.auto.html
// Hopefully it's the same thing.
static PyObject *
psutil_cpu_sockets() {
    unsigned int value;
    size_t size = sizeof(value);

    if (sysctlbyname("hw.packages", &value, &size, NULL, 2))
        Py_RETURN_NONE;  // mimic os.cpu_count()
    else
        return Py_BuildValue("I", value);
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
    if (psutil_add_to_dict(py_retdict, "num_cores_per_socket",
                           psutil_cpu_cores_per_socket()) == 1) {
        goto error;
    }
    if (psutil_add_to_dict(py_retdict, "num_threads_per_core",
                           psutil_cpu_threads_per_core()) == 1) {
        goto error;
    }
    if (psutil_add_to_dict(py_retdict, "num_sockets",
                           psutil_cpu_sockets()) == 1) {
        goto error;
    }
    return py_retdict;

error:
    Py_DECREF(py_retdict);
    return NULL;
}
