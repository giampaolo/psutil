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
- Most info can be obtained with "sysctl -a | grep machdep.cpu"
*/


#include <Python.h>
#include <sys/sysctl.h>
#include <ctype.h>

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


// Returns a string like this:
// 'fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov ...'
static PyObject *
psutil_cpu_features() {
    size_t len1;
    size_t len2;
    char *buf1 = NULL;
    char *buf2 = NULL;
    char *buf3 = NULL;
    int i;
    PyObject *py_str = NULL;

    // There are standard and extended features (both strings). First,
    // get the size for both.
    if (sysctlbyname("machdep.cpu.features", NULL, &len1, NULL, 0) != 0) {
        psutil_debug("sysctlbyname('machdep.cpu.features') failed (ignored)");
        Py_RETURN_NONE;
    }

    if (sysctlbyname("machdep.cpu.extfeatures", NULL, &len2, NULL, 0) != 0) {
        psutil_debug("sysctlbyname('machdep.cpu.extfeatures') failed (ignored)");
        Py_RETURN_NONE;
    }

    // Now we get the real values; we need 2 mallocs.

    // ...standard
    buf1 = malloc(len1);
    if (buf1 == NULL) {
        PyErr_NoMemory();
        goto error;
    }
    if (sysctlbyname("machdep.cpu.features", buf1, &len1, NULL, 0) != 0) {
        psutil_debug("sysctlbyname('machdep.cpu.features') failed (ignored)");
        goto error;
    }

    // ...extended
    buf2 = malloc(len2);
    if (buf2 == NULL) {
        PyErr_NoMemory();
        goto error;
    }
    if (sysctlbyname("machdep.cpu.extfeatures", buf2, &len2, NULL, 0) != 0) {
        psutil_debug("sysctlbyname('machdep.cpu.extfeatures') failed (ignored)");
        goto error;
    }

    // Lower case both strings (mimic Linux lscpu).
    for (i = 0; buf1[i]; i++)
        buf1[i] = tolower(buf1[i]);
    for (i = 0; buf2[i]; i++)
        buf2[i] = tolower(buf2[i]);

    // Make space for both in a new buffer and join them (+1 is for the
    // null terminator).
    buf3 = malloc(len1 + len2 + 1);
    if (buf3 == NULL) {
        PyErr_NoMemory();
        goto error;
    }
    sprintf(buf3, "%s %s", buf1, buf2);

    // Return.
    py_str = Py_BuildValue("s", buf3);
    free(buf1);
    free(buf2);
    free(buf3);
    return py_str;

error:
    if (buf1 != NULL)
        free(buf1);
    if (buf2 != NULL)
        free(buf2);
    if (buf3 != NULL)
        free(buf3);
    if (PyErr_Occurred())  // malloc failed
        return NULL;
    Py_RETURN_NONE;
}


static PyObject *
psutil_cpu_num_cores_per_socket() {
    int value;
    size_t size = sizeof(value);

    if (sysctlbyname("machdep.cpu.cores_per_package",
                     &value, &size, NULL, 0) != 0) {
        psutil_debug("sysctlbyname('machdep.cpu.cores_per_package') "
                     "failed (ignored)");
        Py_RETURN_NONE;
    }
    return Py_BuildValue("i", value);
}


// "threads_per_core" is how it's being called by lscpu on Linux.
// Here it's "thread_count". Hopefully it's the same thing.
static PyObject *
psutil_cpu_threads_per_core() {
    int value;
    size_t size = sizeof(value);

    if (sysctlbyname("machdep.cpu.thread_count",
                     &value, &size, NULL, 0) != 0) {
        psutil_debug("sysctlbyname('machdep.cpu.thread_count') "
                     "failed (ignored)");
        Py_RETURN_NONE;
    }
    return Py_BuildValue("i", value);
}


// The number of physical CPU sockets.
// It looks like on macOS "sockets" are called "packages".
// Hopefully it's the same thing.
static PyObject *
psutil_cpu_sockets() {
    int value;
    size_t size = sizeof(value);

    if (sysctlbyname("hw.packages", &value, &size, NULL, 2)) {
        psutil_debug("sysctlbyname('hw.packages') failed (ignored)");
        Py_RETURN_NONE;
    }
    return Py_BuildValue("i", value);
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

    // strings
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
