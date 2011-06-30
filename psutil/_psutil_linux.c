/*
 * $Id$
 *
 * Linux-specific functions.
 */

#include <Python.h>
#include <errno.h>
#include <stdlib.h>
#include <mntent.h>
#include <sys/syscall.h>
#include <linux/unistd.h>

#include "_psutil_linux.h"


#define HAS_IOPRIO defined(__NR_ioprio_get) && defined(__NR_ioprio_set)

#if HAS_IOPRIO
enum {
	IOPRIO_WHO_PROCESS = 1,
};

static inline int
ioprio_get(int which, int who)
{
	return syscall(__NR_ioprio_get, which, who);
}

static inline int
ioprio_set(int which, int who, int ioprio)
{
	return syscall(__NR_ioprio_set, which, who, ioprio);
}

#define IOPRIO_CLASS_SHIFT	13
#define IOPRIO_PRIO_MASK  ((1UL << IOPRIO_CLASS_SHIFT) - 1)

#define IOPRIO_PRIO_CLASS(mask)  ((mask) >> IOPRIO_CLASS_SHIFT)
#define IOPRIO_PRIO_DATA(mask)  ((mask) & IOPRIO_PRIO_MASK)
#define IOPRIO_PRIO_VALUE(class, data)  (((class) << IOPRIO_CLASS_SHIFT) | data)


/*
 * Return a (ioclass, iodata) Python tuple representing process I/O priority.
 */
static PyObject*
linux_ioprio_get(PyObject* self, PyObject* args)
{
    long pid;
	int ioprio, ioclass, iodata;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    ioprio = ioprio_get(IOPRIO_WHO_PROCESS, pid);
    if (ioprio == -1) {
        return PyErr_SetFromErrno(PyExc_OSError);
    }
	ioclass = IOPRIO_PRIO_CLASS(ioprio);
	iodata = IOPRIO_PRIO_DATA(ioprio);
    return Py_BuildValue("ii", ioclass, iodata);
}


/*
 * A wrapper around ioprio_set(); sets process I/O priority.
 * ioclass can be either IOPRIO_CLASS_RT, IOPRIO_CLASS_BE, IOPRIO_CLASS_IDLE
 * or 0. iodata goes from 0 to 7 depending on ioclass specified.
 */
static PyObject*
linux_ioprio_set(PyObject* self, PyObject* args)
{
    long pid;
    int ioprio, ioclass, iodata;
    int retval;

    if (! PyArg_ParseTuple(args, "lii", &pid, &ioclass, &iodata)) {
        return NULL;
    }
    ioprio = IOPRIO_PRIO_VALUE(ioclass, iodata);
	retval = ioprio_set(IOPRIO_WHO_PROCESS, pid, ioprio);
	if (retval == -1) {
        return PyErr_SetFromErrno(PyExc_OSError);
    }
    Py_INCREF(Py_None);
    return Py_None;
}
#endif


/*
 * Return disk mounted partitions as a list of tuples including device,
 * mount point and filesystem type
 */
static PyObject*
get_disk_partitions(PyObject* self, PyObject* args)
{
    FILE *file;
    struct mntent *entry;
    PyObject* py_retlist = PyList_New(0);
    PyObject* py_tuple;

    // MOUNTED constant comes from mntent.h and it's == '/etc/mtab'
    Py_BEGIN_ALLOW_THREADS
    file = setmntent(MOUNTED, "r");
    Py_END_ALLOW_THREADS
    if (file == 0) {
    	return PyErr_SetFromErrno(PyExc_OSError);
    }

    Py_BEGIN_ALLOW_THREADS
    while ((entry = getmntent(file))) {
        py_tuple = Py_BuildValue("(sss)", entry->mnt_fsname,  // device
                                          entry->mnt_dir,     // mount point
                                          entry->mnt_type);   // fs type
        PyList_Append(py_retlist, py_tuple);
        Py_XDECREF(py_tuple);
    }

    endmntent(file);
    Py_END_ALLOW_THREADS
    return py_retlist;
}


/*
 * Define the psutil C module methods and initialize the module.
 */
static PyMethodDef
PsutilMethods[] =
{
#if HAS_IOPRIO
     {"ioprio_get", linux_ioprio_get, METH_VARARGS,
        "Get process I/O priority"},
     {"ioprio_set", linux_ioprio_set, METH_VARARGS,
        "Set process I/O priority"},
#endif
     {"get_disk_partitions", get_disk_partitions, METH_VARARGS,
        "Return disk mounted partitions as a list of tuples including "
        "device, mount point and filesystem type"},

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
psutil_linux_traverse(PyObject *m, visitproc visit, void *arg) {
    Py_VISIT(GETSTATE(m)->error);
    return 0;
}

static int
psutil_linux_clear(PyObject *m) {
    Py_CLEAR(GETSTATE(m)->error);
    return 0;
}

static struct PyModuleDef
moduledef = {
        PyModuleDef_HEAD_INIT,
        "psutil_linux",
        NULL,
        sizeof(struct module_state),
        PsutilMethods,
        NULL,
        psutil_linux_traverse,
        psutil_linux_clear,
        NULL
};

#define INITERROR return NULL

PyObject *
PyInit__psutil_linux(void)

#else
#define INITERROR return

void init_psutil_linux(void)
#endif
{
#if PY_MAJOR_VERSION >= 3
    PyObject *module = PyModule_Create(&moduledef);
#else
    PyObject *module = Py_InitModule("_psutil_linux", PsutilMethods);
#endif
    if (module == NULL) {
        INITERROR;
    }
#if PY_MAJOR_VERSION >= 3
    return module;
#endif
}

