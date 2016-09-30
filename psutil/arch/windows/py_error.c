#include <Python.h>
#include <windows.h>


PyObject *PyErr_SetFromWindowsErr(int ierr)
{
    int len;
    WCHAR *s_buf = NULL; /* Free via LocalFree */
    PyObject *message;
    PyObject *args, *v;
    DWORD err = (DWORD)ierr;
    if (err==0) err = GetLastError();
    len = FormatMessageW(
        /* Error API error */
        FORMAT_MESSAGE_ALLOCATE_BUFFER |
        FORMAT_MESSAGE_FROM_SYSTEM |
        FORMAT_MESSAGE_IGNORE_INSERTS,
        NULL,           /* no message source */
        err,
        MAKELANGID(LANG_NEUTRAL,
        SUBLANG_DEFAULT), /* Default language */
        (LPWSTR) &s_buf,
        0,              /* size not used */
        NULL);          /* no args */
    if (len==0) {
        /* Only seen this in out of mem situations */
        message = PyUnicode_FromFormat("Windows Error 0x%x", err);
        s_buf = NULL;
    } else {
        /* remove trailing cr/lf and dots */
        while (len > 0 && (s_buf[len-1] <= L' ' || s_buf[len-1] == L'.'))
            s_buf[--len] = L'\0';
        message = PyUnicode_FromWideChar(s_buf, len);
    }

    if (message == NULL)
    {
        LocalFree(s_buf);
        return NULL;
    }

    /* This is the constructor signature for OSError.
       The POSIX translation will be figured out by the constructor. */
    args = Py_BuildValue("(iO)", err, message);
    Py_DECREF(message);

    if (args != NULL) {
        v = PyObject_Call(PyExc_OSError, args, NULL);
        Py_DECREF(args);
        if (v != NULL) {
            PyErr_SetObject((PyObject *) Py_TYPE(v), v);
            Py_DECREF(v);
        }
    }
    LocalFree(s_buf);
    return NULL;
}
