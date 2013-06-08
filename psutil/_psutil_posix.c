/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Functions specific to all POSIX compliant platforms.
 */

#include <Python.h>
#include <errno.h>
#include <stdlib.h>
#include <sys/resource.h>

#include "_psutil_posix.h"


/*
 * Given a PID return process priority as a Python integer.
 */
static PyObject*
posix_getpriority(PyObject* self, PyObject* args)
{
    long pid;
    int priority;
    errno = 0;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    priority = getpriority(PRIO_PROCESS, pid);
    if (errno != 0) {
        return PyErr_SetFromErrno(PyExc_OSError);
    }
    return Py_BuildValue("i", priority);
}

/*
 * Given a PID and a value change process priority.
 */
static PyObject*
posix_setpriority(PyObject* self, PyObject* args)
{
    long pid;
    int priority;
    int retval;
    if (! PyArg_ParseTuple(args, "li", &pid, &priority)) {
        return NULL;
    }
    retval = setpriority(PRIO_PROCESS, pid, priority);
    if (retval == -1) {
        return PyErr_SetFromErrno(PyExc_OSError);
    }
    Py_INCREF(Py_None);
    return Py_None;
}


/*
 * define the psutil C module methods and initialize the module.
 */
static PyMethodDef
PsutilMethods[] =
{
     {"getpriority", posix_getpriority, METH_VARARGS,
        "Return process priority"},
     {"setpriority", posix_setpriority, METH_VARARGS,
        "Set process priority"},
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

#if PY_MAJOR_VERSION >= 3

static int
psutil_posix_traverse(PyObject *m, visitproc visit, void *arg) {
    Py_VISIT(GETSTATE(m)->error);
    return 0;
}

static int
psutil_posix_clear(PyObject *m) {
    Py_CLEAR(GETSTATE(m)->error);
    return 0;
}

static struct PyModuleDef
moduledef = {
        PyModuleDef_HEAD_INIT,
        "psutil_posix",
        NULL,
        sizeof(struct module_state),
        PsutilMethods,
        NULL,
        psutil_posix_traverse,
        psutil_posix_clear,
        NULL
};

#define INITERROR return NULL

PyObject *
PyInit__psutil_posix(void)

#else
#define INITERROR return

void init_psutil_posix(void)
#endif
{
#if PY_MAJOR_VERSION >= 3
    PyObject *module = PyModule_Create(&moduledef);
#else
    PyObject *module = Py_InitModule("_psutil_posix", PsutilMethods);
#endif
    if (module == NULL) {
        INITERROR;
    }
#if PY_MAJOR_VERSION >= 3
    return module;
#endif
}
