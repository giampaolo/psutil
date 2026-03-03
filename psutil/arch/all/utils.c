#include <Python.h>
#include <stdarg.h>


// Build a Python object from a format string, append it to a list,
// then decref it. Eliminates the need for a temporary variable, a NULL
// check, and a Py_DECREF / Py_XDECREF at the error label. Returns 1 on
// success, 0 on failure with a Python exception set.
int
pylist_append_fmt(PyObject *list, const char *fmt, ...) {
    int ret = 0;  // 0 = failure
    PyObject *obj = NULL;
    va_list ap;

    va_start(ap, fmt);
    obj = Py_VaBuildValue(fmt, ap);
    va_end(ap);

    if (!obj)
        return 0;
    if (PyList_Append(list, obj) < 0)
        goto done;
    ret = 1;  // success

done:
    Py_DECREF(obj);
    return ret;
}


// Append a pre-built Python object to a list, then decref it. Same as
// pylist_append_fmt() but takes an already-built object instead of a
// format string. Returns 1 on success, 0 on failure with a Python
// exception set.
int
pylist_append_obj(PyObject *list, PyObject *obj) {
    if (!obj)
        return 0;
    if (PyList_Append(list, obj) < 0) {
        Py_DECREF(obj);
        return 0;
    }
    Py_DECREF(obj);
    return 1;
}


// Build a Python object from a format string, set it as a key in a
// dict, then decref it. Same idea as pylist_append_fmt() but for
// dicts. Returns 1 on success, 0 on failure with a Python exception
// set.
int
pydict_add(PyObject *dict, const char *key, const char *fmt, ...) {
    int ret = 0;  // 0 = failure
    PyObject *obj = NULL;
    va_list ap;

    va_start(ap, fmt);
    obj = Py_VaBuildValue(fmt, ap);
    va_end(ap);

    if (!obj)
        return 0;
    if (PyDict_SetItemString(dict, key, obj) < 0)
        goto done;
    ret = 1;  // success

done:
    Py_DECREF(obj);
    return ret;
}
