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


PyObject *
psutil_proc_watcher(PyObject *self, PyObject *args) {
    HRESULT hres;

    // Initialize COM
    hres = CoInitializeEx(0, COINIT_MULTITHREADED);
    if (FAILED(hres)) {
        printf("Failed to initialize COM. Error code: 0x%X\n", hres);
        return NULL;
    }

    // Initialize security
    hres = CoInitializeSecurity(NULL, -1, NULL, NULL, RPC_C_AUTHN_LEVEL_DEFAULT,
                                RPC_C_IMP_LEVEL_IMPERSONATE, NULL, EOAC_NONE, NULL);
    if (FAILED(hres)) {
        printf("Failed to initialize security. Error code: 0x%X\n", hres);
        CoUninitialize();
        return NULL;
    }

    // Create WMI locator
    IWbemLocator *pLoc = NULL;
    hres = CoCreateInstance(&CLSID_WbemLocator, 0, CLSCTX_INPROC_SERVER, &IID_IWbemLocator, (LPVOID *) &pLoc);
    if (FAILED(hres)) {
        printf("Failed to create IWbemLocator. Error code: 0x%X\n", hres);
        CoUninitialize();
        return NULL;
    }

    // Connect to WMI namespace
    IWbemServices *pSvc = NULL;
    hres = pLoc->lpVtbl->ConnectServer(pLoc, L"ROOT\\CIMV2", NULL, NULL, 0, NULL, 0, 0, &pSvc);
    if (FAILED(hres)) {
        printf("Failed to connect to WMI. Error code: 0x%X\n", hres);
        pLoc->lpVtbl->Release(pLoc);
        CoUninitialize();
        return NULL;
    }

    // Set security levels on WMI connection
    hres = CoSetProxyBlanket((IUnknown*)pSvc, RPC_C_AUTHN_WINNT, RPC_C_AUTHZ_NONE, NULL,
                             RPC_C_AUTHN_LEVEL_CALL, RPC_C_IMP_LEVEL_IMPERSONATE, NULL, EOAC_NONE);
    if (FAILED(hres)) {
        printf("Failed to set security levels. Error code: 0x%X\n", hres);
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
        printf("Query for process creation failed. Error code: 0x%X\n", hres);
        pSvc->lpVtbl->Release(pSvc);
        pLoc->lpVtbl->Release(pLoc);
        CoUninitialize();
        return NULL;
    }

    printf("Listening for process creation events...\n");

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

                wprintf(L"New Process Created: %s (PID: %lu)\n", varName.bstrVal, varProcessId.uintVal);

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
