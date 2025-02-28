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


/*
PyObject *
psutil_proc_watcher(PyObject *self, PyObject *args) {
    HRESULT hres;

    // Initialize COM
    hres = CoInitializeEx(0, COINIT_MULTITHREADED);
    if (FAILED(hres)) {
        return NULL;
    }

    // Initialize security
    hres = CoInitializeSecurity(NULL, -1, NULL, NULL, RPC_C_AUTHN_LEVEL_DEFAULT,
                                RPC_C_IMP_LEVEL_IMPERSONATE, NULL, EOAC_NONE, NULL);
    if (FAILED(hres)) {
        CoUninitialize();
        return NULL;
    }

    // Create WMI locator
    IWbemLocator *pLoc = NULL;
    hres = CoCreateInstance(&CLSID_WbemLocator, 0, CLSCTX_INPROC_SERVER, &IID_IWbemLocator, (LPVOID *) &pLoc);
    if (FAILED(hres)) {
        CoUninitialize();
        return NULL;
    }

    // Connect to WMI namespace
    IWbemServices *pSvc = NULL;
    hres = pLoc->lpVtbl->ConnectServer(pLoc, L"ROOT\\CIMV2", NULL, NULL, 0, NULL, 0, 0, &pSvc);
    if (FAILED(hres)) {
        pLoc->lpVtbl->Release(pLoc);
        CoUninitialize();
        return NULL;
    }

    // Set security levels on WMI connection
    hres = CoSetProxyBlanket((IUnknown*)pSvc, RPC_C_AUTHN_WINNT, RPC_C_AUTHZ_NONE, NULL,
                             RPC_C_AUTHN_LEVEL_CALL, RPC_C_IMP_LEVEL_IMPERSONATE, NULL, EOAC_NONE);
    if (FAILED(hres)) {
        pSvc->lpVtbl->Release(pSvc);
        pLoc->lpVtbl->Release(pLoc);
        CoUninitialize();
        return NULL;
    }

    // Create query to listen for process creation events
    IEnumWbemClassObject* pEnumerator = NULL;
    hres = pSvc->lpVtbl->ExecNotificationQuery(pSvc, L"WQL",
                L"SELECT * FROM __InstanceCreationEvent WITHIN 1 WHERE TargetInstance ISA 'Win32_Process'",
                WBEM_FLAG_FORWARD_ONLY | WBEM_FLAG_RETURN_IMMEDIATELY, NULL, &pEnumerator);

    if (FAILED(hres)) {
        pSvc->lpVtbl->Release(pSvc);
        pLoc->lpVtbl->Release(pLoc);
        CoUninitialize();
        return NULL;
    }


    // Event loop
    while (pEnumerator) {
        IWbemClassObject *pObj = NULL;
        ULONG ret = 0;

        hres = pEnumerator->lpVtbl->Next(pEnumerator, WBEM_INFINITE, 1, &pObj, &ret);
        if (ret == 0) break;

        VARIANT var;
        VariantInit(&var);  // Initialize the variant before use
        hres = pObj->lpVtbl->Get(pObj, L"TargetInstance", 0, &var, 0, 0);

        if (SUCCEEDED(hres) && var.vt == VT_UNKNOWN) {
            IWbemClassObject* pProcess = NULL;
            IUnknown* pUnknown = V_UNKNOWN(&var);
            hres = pUnknown->lpVtbl->QueryInterface(pUnknown, &IID_IWbemClassObject, (void**)&pProcess);

            if (SUCCEEDED(hres) && pProcess) {
                VARIANT varProcessId, varName;
                VariantInit(&varProcessId);
                VariantInit(&varName);

                pProcess->lpVtbl->Get(pProcess, L"ProcessId", 0, &varProcessId, 0, 0);
                pProcess->lpVtbl->Get(pProcess, L"Name", 0, &varName, 0, 0);


                VariantClear(&varProcessId);
                VariantClear(&varName);
                pProcess->lpVtbl->Release(pProcess);
            }
        }

        VariantClear(&var);  // Clear the variant to free memory
        pObj->lpVtbl->Release(pObj);
    }

    // Cleanup
    pEnumerator->lpVtbl->Release(pEnumerator);
    pSvc->lpVtbl->Release(pSvc);
    pLoc->lpVtbl->Release(pLoc);
    CoUninitialize();
    Py_RETURN_NONE;
}
*/


// class attributes
typedef struct {
    PyObject_HEAD
    int running;
    IWbemLocator *pLoc;
    IWbemServices *pSvc;
    IEnumWbemClassObject *pEnumerator;
} ProcessWatcherObject;


static int
ProcessWatcher_init(ProcessWatcherObject *self, PyObject *args, PyObject *kwds) {
    self->running = 1;  // Initialize the attribute
    HRESULT hres;

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
        CoUninitialize();
        return -1;
    }

    // Create WMI locator
    hres = CoCreateInstance(
        &CLSID_WbemLocator, 0, CLSCTX_INPROC_SERVER, &IID_IWbemLocator,
        (LPVOID *) &self->pLoc
    );
    if (FAILED(hres)) {
        PyErr_SetString(PyExc_RuntimeError, "CoCreateInstance failed");
        CoUninitialize();
        return -1;
    }

    // Connect to WMI namespace
    hres = self->pLoc->lpVtbl->ConnectServer(
        self->pLoc, L"ROOT\\CIMV2", NULL, NULL, 0, NULL, 0, 0, &self->pSvc
    );
    if (FAILED(hres)) {
        PyErr_SetString(PyExc_RuntimeError, "ConnectServer failed");
        self->pLoc->lpVtbl->Release(self->pLoc);
        CoUninitialize();
        return -1;
    }

    // Set security levels on WMI connection
    hres = CoSetProxyBlanket(
        (IUnknown*)self->pSvc, RPC_C_AUTHN_WINNT, RPC_C_AUTHZ_NONE, NULL,
        RPC_C_AUTHN_LEVEL_CALL, RPC_C_IMP_LEVEL_IMPERSONATE, NULL, EOAC_NONE
    );
    if (FAILED(hres)) {
        PyErr_SetString(PyExc_RuntimeError, "CoSetProxyBlanket failed");
        self->pSvc->lpVtbl->Release(self->pSvc);
        self->pLoc->lpVtbl->Release(self->pLoc);
        CoUninitialize();
        return -1;
    }

    // Create query to listen for process creation events
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
        self->pSvc->lpVtbl->Release(self->pSvc);
        self->pLoc->lpVtbl->Release(self->pLoc);
        CoUninitialize();
        return -1;
    }

    return 0;
}


static PyObject *
ProcessWatcher_loop(ProcessWatcherObject *self, PyObject *Py_UNUSED(ignored)) {
    Py_RETURN_NONE;
}

static PyObject *
ProcessWatcher_close(ProcessWatcherObject *self, PyObject *Py_UNUSED(ignored)) {
    self->running = 0;
    if (self->pSvc != NULL)
        self->pSvc->lpVtbl->Release(self->pSvc);
    if (self->pLoc != NULL)
        self->pLoc->lpVtbl->Release(self->pLoc);
    Py_RETURN_NONE;
}

static PyObject *
ProcessWatcher_iter(PyObject *self) {
    Py_INCREF(self);
    return self;
}

// Define class methods.
static PyMethodDef ProcessWatcher_methods[] = {
    {"loop", (PyCFunction)ProcessWatcher_loop, METH_NOARGS, "Run the event loop"},
    {"close", (PyCFunction)ProcessWatcher_close, METH_NOARGS, "Stop the event loop"},
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
