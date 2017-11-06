#include "utils.h"

/*
 Accept a filename's drive in native  format like "\Device\HarddiskVolume1\"
 and return the corresponding drive letter (e.g. "C:\\").
 If no match is found return an empty string.
*/
PyObject *
psutil_win32_QueryDosDevice(PyObject *self, PyObject *args) {
    LPCTSTR   lpDevicePath;
    TCHAR d = TEXT('A');
    TCHAR     szBuff[5];

    if (!PyArg_ParseTuple(args, "s", &lpDevicePath))
        return NULL;

    while (d <= TEXT('Z')) {
        TCHAR szDeviceName[3] = {d, TEXT(':'), TEXT('\0')};
        TCHAR szTarget[512] = {0};
        if (QueryDosDevice(szDeviceName, szTarget, 511) != 0) {
            if (_tcscmp(lpDevicePath, szTarget) == 0) {
                _stprintf_s(szBuff, _countof(szBuff), TEXT("%c:"), d);
                return Py_BuildValue("s", szBuff);
            }
        }
        d++;
    }
    return Py_BuildValue("s", "");
}


