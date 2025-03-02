/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <wbemidl.h>
#include <objbase.h>
#include <stdio.h>

#pragma comment(lib, "wbemuuid.lib")


// class attributes
typedef struct {
    PyObject_HEAD
    int closed;
    IWbemLocator *pLoc;
    IWbemServices *pSvc;
    IEnumWbemClassObject *pEnumerator;
} ProcessWatcherObject;


static void
ProcessWatcher_cleanup(ProcessWatcherObject *self) {
    if (self->closed == 1)
        return;
    self->closed = 1;
    if (self->pEnumerator)
        self->pEnumerator->lpVtbl->Release(self->pEnumerator);
    if (self->pSvc)
        self->pSvc->lpVtbl->Release(self->pSvc);
    if (self->pLoc)
        self->pLoc->lpVtbl->Release(self->pLoc);
    CoUninitialize();
}


static int
ProcessWatcher_init(ProcessWatcherObject *self, PyObject *args, PyObject *kwds) {
    HRESULT hres;

   if (self->closed == 1) {
        PyErr_SetString(
            PyExc_ValueError, "can't reuse an already closed ProcessWatcher"
        );
        return -1;
    }

    hres = CoInitializeEx(0, COINIT_MULTITHREADED);
    if (FAILED(hres)) {
        PyErr_SetString(PyExc_RuntimeError, "CoInitializeEx failed");
        return -1;
    }

    hres = CoInitializeSecurity(
        NULL, -1, NULL, NULL, RPC_C_AUTHN_LEVEL_DEFAULT,
        RPC_C_IMP_LEVEL_IMPERSONATE, NULL, EOAC_NONE, NULL
    );
    if (FAILED(hres)) {
        PyErr_SetString(PyExc_RuntimeError, "CoInitializeSecurity failed");
        goto error;
    }

    hres = CoCreateInstance(
        &CLSID_WbemLocator, 0, CLSCTX_INPROC_SERVER, &IID_IWbemLocator,
        (LPVOID *) &self->pLoc
    );
    if (FAILED(hres)) {
        PyErr_SetString(PyExc_RuntimeError, "CoCreateInstance failed");
        goto error;
    }

    hres = self->pLoc->lpVtbl->ConnectServer(
        self->pLoc, L"ROOT\\CIMV2", NULL, NULL, 0, NULL, 0, 0, &self->pSvc
    );
    if (FAILED(hres)) {
        PyErr_SetString(PyExc_RuntimeError, "ConnectServer failed");
        goto error;
    }

    hres = CoSetProxyBlanket(
        (IUnknown*)self->pSvc, RPC_C_AUTHN_WINNT, RPC_C_AUTHZ_NONE, NULL,
        RPC_C_AUTHN_LEVEL_CALL, RPC_C_IMP_LEVEL_IMPERSONATE, NULL, EOAC_NONE
    );
    if (FAILED(hres)) {
        PyErr_SetString(PyExc_RuntimeError, "CoSetProxyBlanket failed");
        goto error;
    }

    hres = self->pSvc->lpVtbl->ExecNotificationQuery(
        self->pSvc,
        L"WQL",
        L"SELECT * FROM __InstanceCreationEvent WITHIN 1 WHERE TargetInstance ISA 'Win32_Process'",
        WBEM_FLAG_FORWARD_ONLY | WBEM_FLAG_RETURN_IMMEDIATELY,
        NULL,
        &self->pEnumerator
    );
    if (FAILED(hres)) {
        PyErr_SetString(PyExc_RuntimeError, "ExecNotificationQuery failed");
        goto error;
    }

    return 0;

error:
    ProcessWatcher_cleanup(self);
    return -1;
}


static PyObject *
ProcessWatcher_read(ProcessWatcherObject *self, PyObject *Py_UNUSED(ignored)) {
    HRESULT hres;
    ULONG ret;
    IWbemClassObject *pObj = NULL;
    IWbemClassObject* pProcess = NULL;
    VARIANT var;
    VARIANT varProcessId;
    VARIANT varName;
    IUnknown* pUnknown = V_UNKNOWN(&var);

    // Event loop
    while (self->pEnumerator) {
        ret = 0;

        Py_BEGIN_ALLOW_THREADS
        hres = self->pEnumerator->lpVtbl->Next(
            self->pEnumerator, 1000, 1, &pObj, &ret
        );
        Py_END_ALLOW_THREADS

        if (PyErr_CheckSignals() != 0)
            return NULL;
        if (ret == 0)
            break;

        VariantInit(&var);  // Initialize the variant before use
        hres = pObj->lpVtbl->Get(pObj, L"TargetInstance", 0, &var, 0, 0);

        if (SUCCEEDED(hres) && var.vt == VT_UNKNOWN) {
            pProcess = NULL;
            pUnknown = V_UNKNOWN(&var);
            hres = pUnknown->lpVtbl->QueryInterface(
                pUnknown, &IID_IWbemClassObject, (void**)&pProcess
            );

            if (SUCCEEDED(hres) && pProcess) {
                VariantInit(&varProcessId);
                VariantInit(&varName);

                pProcess->lpVtbl->Get(pProcess, L"ProcessId", 0, &varProcessId, 0, 0);
                pProcess->lpVtbl->Get(pProcess, L"Name", 0, &varName, 0, 0);

                // printf("new process %ld, %S\n", varProcessId.lVal, varName.bstrVal);

                VariantClear(&varProcessId);
                VariantClear(&varName);
                pProcess->lpVtbl->Release(pProcess);
            }
        }

        VariantClear(&var);  // Clear the variant to free memory
        pObj->lpVtbl->Release(pObj);
    }

    Py_RETURN_NONE;
}


static PyObject *
ProcessWatcher_close(ProcessWatcherObject *self, PyObject *Py_UNUSED(ignored)) {
    ProcessWatcher_cleanup(self);
    Py_RETURN_NONE;
}


static PyObject *
ProcessWatcher_iter(PyObject *self) {
    Py_INCREF(self);
    return self;
}


// ====================================================================


// Define class methods.
static PyMethodDef ProcessWatcher_methods[] = {
    {"read", (PyCFunction)ProcessWatcher_read, METH_NOARGS, ""},
    {"close", (PyCFunction)ProcessWatcher_close, METH_NOARGS, ""},
    {"__iter__", (PyCFunction)ProcessWatcher_iter, METH_NOARGS, ""},
    {NULL}  // Sentinel
};

static PyType_Slot ProcessWatcher_slots[] = {
    {Py_tp_init, (void *)ProcessWatcher_init},
    {Py_tp_methods, ProcessWatcher_methods},
    {Py_tp_iter, (void *)ProcessWatcher_iter},
    {0, NULL}  // Sentinel
};

PyType_Spec ProcessWatcher_spec = {
    "ProcessWatcher",
    sizeof(ProcessWatcherObject),
    0,
    Py_TPFLAGS_DEFAULT,
    ProcessWatcher_slots
};
