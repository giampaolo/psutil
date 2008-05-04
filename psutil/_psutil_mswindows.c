#include <Python.h>
 
static PyObject* say_hello(PyObject* self, PyObject* args)
{
    const char* name;
 
    if (!PyArg_ParseTuple(args, "s", &name))
        return NULL;
 
    printf("Hello %s!\n", name);
 
    Py_RETURN_NONE;
}
 
static PyMethodDef HelloMethods[] =
{
     {"say_hello", say_hello, METH_VARARGS, "Greet somebody."},
     {NULL, NULL, 0, NULL}
};
 
PyMODINIT_FUNC
 
init_psutil_mswindows(void)
{
     (void) Py_InitModule("_psutil_mswindows", HelloMethods);
}
