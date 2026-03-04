#include <Python.h>
#include <stdarg.h>
#include <string.h>


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


// Dynamically create a new PyStructSequence type. |type_name| is the
// type name, followed by a NULL-terminated list of field name strings.
// Returns NULL on error with a Python exception set. The returned type
// is heap-allocated and intended to be cached in a static variable by
// the caller.
PyTypeObject *
psutil_structseq_type_new(const char *type_name, ...) {
    va_list ap;
    int nfields = 0;
    int i;
    const char *name;
    PyStructSequence_Field *fields = NULL;
    PyStructSequence_Desc desc;
    PyTypeObject *type = NULL;

    // Count fields.
    va_start(ap, type_name);
    while (va_arg(ap, const char *) != NULL)
        nfields++;
    va_end(ap);

    // Allocate fields array (+1 for NULL sentinel).
    fields = PyMem_Malloc(sizeof(PyStructSequence_Field) * (nfields + 1));
    if (!fields) {
        PyErr_NoMemory();
        return NULL;
    }

    // Fill fields array.
    va_start(ap, type_name);
    for (i = 0; i < nfields; i++) {
        name = va_arg(ap, const char *);
        fields[i].name = (char *)name;
        fields[i].doc = NULL;
    }
    va_end(ap);
    fields[nfields].name = NULL;
    fields[nfields].doc = NULL;

    desc.name = (char *)type_name;
    desc.doc = "";
    desc.fields = fields;
    desc.n_in_sequence = nfields;

#if PY_VERSION_HEX >= 0x03090000
    // Python 3.9+: PyStructSequence_NewType() allocates the type
    // internally and makes its own copy of the member definitions,
    // so the fields array can be freed immediately after.
    type = (PyTypeObject *)PyStructSequence_NewType(&desc);
    PyMem_Free(fields);
    return type;  // NULL on error, exception set
#else
    // Python 3.6-3.8: PyTypeObject is not opaque; allocate and zero
    // a type object, then initialize it with InitType2.
    type = PyMem_Malloc(sizeof(PyTypeObject));
    if (!type) {
        PyMem_Free(fields);
        PyErr_NoMemory();
        return NULL;
    }
    memset(type, 0, sizeof(PyTypeObject));
    if (PyStructSequence_InitType2(type, &desc) < 0) {
        PyMem_Free(fields);
        PyMem_Free(type);
        return NULL;
    }
    // |fields| is referenced by the type's tp_members and must not be
    // freed. Since the type is cached for process lifetime, this is
    // an intentional permanent allocation.
    return type;
#endif
}


// Build a Python value from |fmt| + variadic args and store it at the
// next position in a PyStructSequence via PyTuple_SetItem(), which
// steals the reference in all cases. |name| is purely documentary and
// not used at runtime. *pos is incremented on success. Returns 1 on
// success, 0 on failure with an exception set.
int
pystructseq_add(
    PyObject *obj, Py_ssize_t *pos, const char *name, const char *fmt, ...
) {
    PyObject *val = NULL;
    va_list ap;

    (void)name;  // suppress unused-parameter warning
    va_start(ap, fmt);
    val = Py_VaBuildValue(fmt, ap);
    va_end(ap);

    if (!val)
        return 0;
    // PyTuple_SetItem() steals the ref in all cases (success + error),
    // and is safe for struct sequences since they are tuple subclasses.
    if (PyTuple_SetItem(obj, (*pos)++, val) < 0)
        return 0;
    return 1;
}
