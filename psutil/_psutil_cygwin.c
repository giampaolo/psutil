#include <Python.h>

#include <sys/cygwin.h>

#include "_psutil_common.h"


/*
 * Convert the Cygwin PID of a process to/from its corresponding Windows PID
 */
static PyObject*
psutil_cygpid_to_winpid(PyObject *self, PyObject *args) {
    pid_t pid;
    DWORD winpid;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    if (!(winpid = (DWORD)cygwin_internal(CW_CYGWIN_PID_TO_WINPID, pid)))
        return NoSuchProcess("cygwin_internal");

#if PY_MAJOR_VERSION >= 3
    return PyLong_FromLong((long) winpid);
#else
    return PyInt_FromLong((long) winpid);
#endif
}


static PyObject*
psutil_winpid_to_cygpid(PyObject *self, PyObject *args) {
    pid_t pid;
    DWORD winpid;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &winpid))
        return NULL;

    /* For some reason (perhaps historical) Cygwin provides a function
     * specifically for this purpose, rather than using cygwin_internal
     * as in the opposite case. */
    if ((pid = cygwin_winpid_to_pid(winpid)) < 0)
        return NoSuchProcess("cygwin_winpid_to_pid");

#if PY_MAJOR_VERSION >= 3
    return PyLong_FromLong((long) pid);
#else
    return PyInt_FromLong((long) pid);
#endif
}


/*
 * define the psutil C module methods and initialize the module.
 */
static PyMethodDef
PsutilMethods[] = {
    // --- cygwin-specific functions
    {"cygpid_to_winpid", psutil_cygpid_to_winpid, METH_VARARGS,
     "Convert the Cygwin PID of a process to its corresponding Windows PID."},
    {"winpid_to_cygpid", psutil_winpid_to_cygpid, METH_VARARGS,
     "Convert the Windows PID of a process to its corresponding Cygwin PID."},

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

#if PY_MAJOR_VERSION >= 3

static int
psutil_cygwin_traverse(PyObject *m, visitproc visit, void *arg) {
    Py_VISIT(GETSTATE(m)->error);
    return 0;
}

static int
psutil_cygwin_clear(PyObject *m) {
    Py_CLEAR(GETSTATE(m)->error);
    return 0;
}

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "psutil_cygwin",
    NULL,
    sizeof(struct module_state),
    PsutilMethods,
    NULL,
    psutil_cygwin_traverse,
    psutil_cygwin_clear,
    NULL
};

#define INITERROR return NULL

PyMODINIT_FUNC PyInit__psutil_cygwin(void)

#else
#define INITERROR return

void init_psutil_cygwin(void)
#endif
{
#if PY_MAJOR_VERSION >= 3
    PyObject *module = PyModule_Create(&moduledef);
#else
    PyObject *module = Py_InitModule("_psutil_cygwin", PsutilMethods);
#endif

    PyModule_AddIntConstant(module, "version", PSUTIL_VERSION);

    if (module == NULL)
        INITERROR;
#if PY_MAJOR_VERSION >= 3
    return module;
#endif
}
