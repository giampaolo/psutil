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
psutil_get_model() {
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
psutil_get_vendor() {
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


/*
 * Retrieve hardware CPU information, similarly to lscpu on Linux.
 */
PyObject *
psutil_cpu_info(PyObject *self, PyObject *args) {
    PyObject *py_retdict = PyDict_New();

    if (py_retdict == NULL)
        return NULL;
    if (psutil_add_to_dict(py_retdict, "model", psutil_get_model()) == 1)
        goto error;
    if (psutil_add_to_dict(py_retdict, "vendor", psutil_get_vendor()) == 1)
        goto error;
    return py_retdict;

error:
    Py_DECREF(py_retdict);
    return NULL;
}
