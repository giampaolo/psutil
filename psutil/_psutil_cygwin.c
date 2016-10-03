#define WIN32_LEAN_AND_MEAN

#include <windows.h>
#include <winsock2.h>
#include <iphlpapi.h>

#include <Python.h>

#include <mntent.h>

#include "arch/windows/process_info.h"

/* TODO: Copied verbatim from the Linux module; refactor */
/*
 * Return disk mounted partitions as a list of tuples including device,
 * mount point and filesystem type
 */
static PyObject *
psutil_disk_partitions(PyObject *self, PyObject *args) {
    FILE *file = NULL;
    struct mntent *entry;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;

    if (py_retlist == NULL)
        return NULL;

    // MOUNTED constant comes from mntent.h and it's == '/etc/mtab'
    Py_BEGIN_ALLOW_THREADS
    file = setmntent(MOUNTED, "r");
    Py_END_ALLOW_THREADS
    if ((file == 0) || (file == NULL)) {
        PyErr_SetFromErrnoWithFilename(PyExc_OSError, MOUNTED);
        goto error;
    }

    while ((entry = getmntent(file))) {
        if (entry == NULL) {
            PyErr_Format(PyExc_RuntimeError, "getmntent() failed");
            goto error;
        }
        py_tuple = Py_BuildValue("(ssss)",
                                 entry->mnt_fsname,  // device
                                 entry->mnt_dir,     // mount point
                                 entry->mnt_type,    // fs type
                                 entry->mnt_opts);   // options
        if (! py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_DECREF(py_tuple);
    }
    endmntent(file);
    return py_retlist;

error:
    if (file != NULL)
        endmntent(file);
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    return NULL;
}


/* Copied verbatim from the Windows module
   TODO: Refactor this later
 */
/*
 * Return process CPU affinity as a bitmask
 */
static PyObject *
psutil_proc_cpu_affinity_get(PyObject *self, PyObject *args) {
    DWORD pid;
    HANDLE hProcess;
    DWORD_PTR proc_mask;
    DWORD_PTR system_mask;

    if (! PyArg_ParseTuple(args, "l", &pid))
        return NULL;
    hProcess = psutil_handle_from_pid(pid);
    if (hProcess == NULL)
        return NULL;

    if (GetProcessAffinityMask(hProcess, &proc_mask, &system_mask) == 0) {
        CloseHandle(hProcess);
        return PyErr_SetFromWindowsErr(0);
    }

    CloseHandle(hProcess);
#ifdef _WIN64
    return Py_BuildValue("K", (unsigned long long)proc_mask);
#else
    return Py_BuildValue("k", (unsigned long)proc_mask);
#endif
}


/*
 * Set process CPU affinity
 */
static PyObject *
psutil_proc_cpu_affinity_set(PyObject *self, PyObject *args) {
    DWORD pid;
    HANDLE hProcess;
    DWORD dwDesiredAccess = \
        PROCESS_QUERY_INFORMATION | PROCESS_SET_INFORMATION;
    DWORD_PTR mask;

#ifdef _WIN64
    if (! PyArg_ParseTuple(args, "lK", &pid, &mask))
#else
    if (! PyArg_ParseTuple(args, "lk", &pid, &mask))
#endif
    {
        return NULL;
    }
    hProcess = psutil_handle_from_pid_waccess(pid, dwDesiredAccess);
    if (hProcess == NULL)
        return NULL;

    if (SetProcessAffinityMask(hProcess, mask) == 0) {
        CloseHandle(hProcess);
        return PyErr_SetFromWindowsErr(0);
    }

    CloseHandle(hProcess);
    Py_RETURN_NONE;
}


PIP_ADAPTER_ADDRESSES
psutil_get_nic_addresses() {
    // allocate a 15 KB buffer to start with
    int outBufLen = 15000;
    DWORD dwRetVal = 0;
    ULONG attempts = 0;
    PIP_ADAPTER_ADDRESSES pAddresses = NULL;

    do {
        pAddresses = (IP_ADAPTER_ADDRESSES *) malloc(outBufLen);
        if (pAddresses == NULL) {
            PyErr_NoMemory();
            return NULL;
        }

        dwRetVal = GetAdaptersAddresses(AF_UNSPEC, 0, NULL, pAddresses,
                                        &outBufLen);
        if (dwRetVal == ERROR_BUFFER_OVERFLOW) {
            free(pAddresses);
            pAddresses = NULL;
        }
        else {
            break;
        }

        attempts++;
    } while ((dwRetVal == ERROR_BUFFER_OVERFLOW) && (attempts < 3));

    if (dwRetVal != NO_ERROR) {
        PyErr_SetString(PyExc_RuntimeError, "GetAdaptersAddresses() failed.");
        return NULL;
    }

    return pAddresses;
}


/*
 * Provides stats about NIC interfaces installed on the system.
 * TODO: get 'duplex' (currently it's hard coded to '2', aka
         'full duplex')
 */

/* TODO: This and the helper get_nic_addresses are copied *almost* verbatim
   from the windows module.  The only difference is the use of snprintf with
   the %ls format, as opposed to using sprintf_s from MSCRT */
static PyObject *
psutil_net_if_stats(PyObject *self, PyObject *args) {
    int i;
    DWORD dwSize = 0;
    DWORD dwRetVal = 0;
    MIB_IFTABLE *pIfTable;
    MIB_IFROW *pIfRow;
    PIP_ADAPTER_ADDRESSES pAddresses = NULL;
    PIP_ADAPTER_ADDRESSES pCurrAddresses = NULL;
    char descr[MAX_PATH];
    int ifname_found;

    PyObject *py_nic_name = NULL;
    PyObject *py_retdict = PyDict_New();
    PyObject *py_ifc_info = NULL;
    PyObject *py_is_up = NULL;

    if (py_retdict == NULL)
        return NULL;

    pAddresses = psutil_get_nic_addresses();
    if (pAddresses == NULL)
        goto error;

    pIfTable = (MIB_IFTABLE *) malloc(sizeof (MIB_IFTABLE));
    if (pIfTable == NULL) {
        PyErr_NoMemory();
        goto error;
    }
    dwSize = sizeof(MIB_IFTABLE);
    if (GetIfTable(pIfTable, &dwSize, FALSE) == ERROR_INSUFFICIENT_BUFFER) {
        free(pIfTable);
        pIfTable = (MIB_IFTABLE *) malloc(dwSize);
        if (pIfTable == NULL) {
            PyErr_NoMemory();
            goto error;
        }
    }
    // Make a second call to GetIfTable to get the actual
    // data we want.
    if ((dwRetVal = GetIfTable(pIfTable, &dwSize, FALSE)) != NO_ERROR) {
        PyErr_SetString(PyExc_RuntimeError, "GetIfTable() failed");
        goto error;
    }

    for (i = 0; i < (int) pIfTable->dwNumEntries; i++) {
        pIfRow = (MIB_IFROW *) & pIfTable->table[i];

        // GetIfTable is not able to give us NIC with "friendly names"
        // so we determine them via GetAdapterAddresses() which
        // provides friendly names *and* descriptions and find the
        // ones that match.
        ifname_found = 0;
        pCurrAddresses = pAddresses;
        while (pCurrAddresses) {
            snprintf(descr, MAX_PATH, "%ls", pCurrAddresses->Description);
            if (lstrcmp(descr, pIfRow->bDescr) == 0) {
                py_nic_name = PyUnicode_FromWideChar(
                    pCurrAddresses->FriendlyName,
                    wcslen(pCurrAddresses->FriendlyName));
                if (py_nic_name == NULL)
                    goto error;
                ifname_found = 1;
                break;
            }
            pCurrAddresses = pCurrAddresses->Next;
        }
        if (ifname_found == 0) {
            // Name not found means GetAdapterAddresses() doesn't list
            // this NIC, only GetIfTable, meaning it's not really a NIC
            // interface so we skip it.
            continue;
        }

        // is up?
        if((pIfRow->dwOperStatus == MIB_IF_OPER_STATUS_CONNECTED ||
                pIfRow->dwOperStatus == MIB_IF_OPER_STATUS_OPERATIONAL) &&
                pIfRow->dwAdminStatus == 1 ) {
            py_is_up = Py_True;
        }
        else {
            py_is_up = Py_False;
        }
        Py_INCREF(py_is_up);

        py_ifc_info = Py_BuildValue(
            "(Oikk)",
            py_is_up,
            2,  // there's no way to know duplex so let's assume 'full'
            pIfRow->dwSpeed / 1000000,  // expressed in bytes, we want Mb
            pIfRow->dwMtu
        );
        if (!py_ifc_info)
            goto error;
        if (PyDict_SetItem(py_retdict, py_nic_name, py_ifc_info))
            goto error;
        Py_DECREF(py_nic_name);
        Py_DECREF(py_ifc_info);
    }

    free(pIfTable);
    free(pAddresses);
    return py_retdict;

error:
    Py_XDECREF(py_is_up);
    Py_XDECREF(py_ifc_info);
    Py_XDECREF(py_nic_name);
    Py_DECREF(py_retdict);
    if (pIfTable != NULL)
        free(pIfTable);
    if (pAddresses != NULL)
        free(pAddresses);
    return NULL;
}


/*
 * define the psutil C module methods and initialize the module.
 */
static PyMethodDef
PsutilMethods[] = {
    {"disk_partitions", psutil_disk_partitions, METH_VARARGS,
     "Return disk mounted partitions as a list of tuples including "
     "device, mount point and filesystem type"},
    {"proc_cpu_affinity_get", psutil_proc_cpu_affinity_get, METH_VARARGS,
     "Return process CPU affinity as a bitmask."},
    {"proc_cpu_affinity_set", psutil_proc_cpu_affinity_set, METH_VARARGS,
     "Set process CPU affinity."},
    {"net_if_stats", psutil_net_if_stats, METH_VARARGS,
     "Return NICs stats."},
    {NULL, NULL, 0, NULL}
};

struct module_state {
    PyObject *error;
};

#if PY_MAJOR_VERSION >= 3
#define GETSTATE(m) ((struct module_state*)PyModule_GetState(m))
#else
#define GETSTATE(m) (&_state)
#endif

#if PY_MAJOR_VERSION >= 3

static int
psutil_cygwin_traverse(PyObject *m, visitproc visit, void *arg) {
    Py_VISIT(GETSTATE(m)->error);
    return 0;
}

static int
psutil_cygwin_clear(PyObject *m) {
    Py_CLEAR(GETSTATE(m)->error);
    return 0;
}

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "psutil_cygwin",
    NULL,
    sizeof(struct module_state),
    PsutilMethods,
    NULL,
    psutil_cygwin_traverse,
    psutil_cygwin_clear,
    NULL
};

#define INITERROR return NULL

PyMODINIT_FUNC PyInit__psutil_cygwin(void)

#else
#define INITERROR return

void init_psutil_cygwin(void)
#endif
{
#if PY_MAJOR_VERSION >= 3
    PyObject *module = PyModule_Create(&moduledef);
#else
    PyObject *module = Py_InitModule("_psutil_cygwin", PsutilMethods);
#endif

    PyModule_AddIntConstant(module, "version", PSUTIL_VERSION);

    if (module == NULL)
        INITERROR;
#if PY_MAJOR_VERSION >= 3
    return module;
#endif
}
