#include <Python.h>
#include <stdarg.h>


// Build a Python object from a Py_BuildValue format string and append
// it to a list. Returns 1 on success, 0 on failure with a Python
// exception set.
int
pylist_append(PyObject *list, const char *fmt, ...) {
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


// Append a Python object to a list and decref it. Returns 1 on
// success, 0 on failure with a Python exception set.
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


// Build a Python object from a Py_BuildValue format string and set it
// as key in an existing dict. Returns 1 on success, 0 on failure with
// a Python exception set.
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
