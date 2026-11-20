#include <Python.h>
#include <string.h>
#include <utmp.h>

#include "arch/all/init.h"


static PyObject *
decode_field(const char *value, size_t size) {
    return PyUnicode_DecodeFSDefaultAndSize(value, strnlen(value, size));
}


PyObject *
psutil_users(PyObject *self, PyObject *args) {
    struct utmp *ut;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_user = NULL;
    PyObject *py_tty = NULL;
    PyObject *py_hostname = NULL;

    if (py_retlist == NULL)
        return NULL;

    setutent();
    while ((ut = getutent()) != NULL) {
        if (ut->ut_type != USER_PROCESS)
            continue;

        py_user = decode_field(ut->ut_user, sizeof(ut->ut_user));
        if (!py_user)
            goto error;
        py_tty = decode_field(ut->ut_line, sizeof(ut->ut_line));
        if (!py_tty)
            goto error;
        py_hostname = decode_field(ut->ut_host, sizeof(ut->ut_host));
        if (!py_hostname)
            goto error;

        if (!pylist_append_fmt(
                py_retlist,
                "OOOdOi" _Py_PARSE_PID,
                py_user,
                py_tty,
                py_hostname,
                (double)ut->ut_time,
                1,
                ut->ut_pid
            ))
        {
            goto error;
        }
        Py_CLEAR(py_user);
        Py_CLEAR(py_tty);
        Py_CLEAR(py_hostname);
    }

    endutent();
    return py_retlist;

error:
    endutent();
    Py_XDECREF(py_user);
    Py_XDECREF(py_tty);
    Py_XDECREF(py_hostname);
    Py_DECREF(py_retlist);
    return NULL;
}
