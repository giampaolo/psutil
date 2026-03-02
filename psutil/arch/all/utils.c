#include <Python.h>
#include <stdarg.h>


// Build a Python object from a Py_BuildValue format string and add it
// to an existing dict. Steals reference to the object. Returns 0 on
// success, -1 on failure. Does not DECREF the dict.
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
