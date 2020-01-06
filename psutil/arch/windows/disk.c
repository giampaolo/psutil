/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>
#include <tchar.h>

#include "../../_psutil_common.h"


#ifndef _ARRAYSIZE
#define _ARRAYSIZE(a) (sizeof(a)/sizeof(a[0]))
#endif

static char *psutil_get_drive_type(int type) {
    switch (type) {
        case DRIVE_FIXED:
            return "fixed";
        case DRIVE_CDROM:
            return "cdrom";
        case DRIVE_REMOVABLE:
            return "removable";
        case DRIVE_UNKNOWN:
            return "unknown";
        case DRIVE_NO_ROOT_DIR:
            return "unmounted";
        case DRIVE_REMOTE:
            return "remote";
        case DRIVE_RAMDISK:
            return "ramdisk";
        default:
            return "?";
    }
}


/*
 * Return path's disk total and free as a Python tuple.
 */
PyObject *
psutil_disk_usage(PyObject *self, PyObject *args) {
    BOOL retval;
    ULARGE_INTEGER _, total, free;
    char *path;

    if (PyArg_ParseTuple(args, "u", &path)) {
        Py_BEGIN_ALLOW_THREADS
        retval = GetDiskFreeSpaceExW((LPCWSTR)path, &_, &total, &free);
        Py_END_ALLOW_THREADS
        goto return_;
    }

    // on Python 2 we also want to accept plain strings other
    // than Unicode
#if PY_MAJOR_VERSION <= 2
    PyErr_Clear();  // drop the argument parsing error
    if (PyArg_ParseTuple(args, "s", &path)) {
        Py_BEGIN_ALLOW_THREADS
        retval = GetDiskFreeSpaceEx(path, &_, &total, &free);
        Py_END_ALLOW_THREADS
        goto return_;
    }
#endif

    return NULL;

return_:
    if (retval == 0)
        return PyErr_SetFromWindowsErrWithFilename(0, path);
    else
        return Py_BuildValue("(LL)", total.QuadPart, free.QuadPart);
}


/*
 * Return a Python dict of tuples for disk I/O information. This may
 * require running "diskperf -y" command first.
 */
PyObject *
psutil_disk_io_counters(PyObject *self, PyObject *args) {
    DISK_PERFORMANCE diskPerformance;
    DWORD dwSize;
    HANDLE hDevice = NULL;
    char szDevice[MAX_PATH];
    char szDeviceDisplay[MAX_PATH];
    int devNum;
    int i;
    DWORD ioctrlSize;
    BOOL ret;
    PyObject *py_retdict = PyDict_New();
    PyObject *py_tuple = NULL;

    if (py_retdict == NULL)
        return NULL;
    // Apparently there's no way to figure out how many times we have
    // to iterate in order to find valid drives.
    // Let's assume 32, which is higher than 26, the number of letters
    // in the alphabet (from A:\ to Z:\).
    for (devNum = 0; devNum <= 32; ++devNum) {
        py_tuple = NULL;
        sprintf_s(szDevice, MAX_PATH, "\\\\.\\PhysicalDrive%d", devNum);
        hDevice = CreateFile(szDevice, 0, FILE_SHARE_READ | FILE_SHARE_WRITE,
                             NULL, OPEN_EXISTING, 0, NULL);
        if (hDevice == INVALID_HANDLE_VALUE)
            continue;

        // DeviceIoControl() sucks!
        i = 0;
        ioctrlSize = sizeof(diskPerformance);
        while (1) {
            i += 1;
            ret = DeviceIoControl(
                hDevice, IOCTL_DISK_PERFORMANCE, NULL, 0, &diskPerformance,
                ioctrlSize, &dwSize, NULL);
            if (ret != 0)
                break;  // OK!
            if (GetLastError() == ERROR_INSUFFICIENT_BUFFER) {
                // Retry with a bigger buffer (+ limit for retries).
                if (i <= 1024) {
                    ioctrlSize *= 2;
                    continue;
                }
            }
            else if (GetLastError() == ERROR_INVALID_FUNCTION) {
                // This happens on AppVeyor:
                // https://ci.appveyor.com/project/giampaolo/psutil/build/
                //      1364/job/ascpdi271b06jle3
                // Assume it means we're dealing with some exotic disk
                // and go on.
                psutil_debug("DeviceIoControl -> ERROR_INVALID_FUNCTION; "
                             "ignore PhysicalDrive%i", devNum);
                goto next;
            }
            else if (GetLastError() == ERROR_NOT_SUPPORTED) {
                // Again, let's assume we're dealing with some exotic disk.
                psutil_debug("DeviceIoControl -> ERROR_NOT_SUPPORTED; "
                             "ignore PhysicalDrive%i", devNum);
                goto next;
            }
            // XXX: it seems we should also catch ERROR_INVALID_PARAMETER:
            // https://sites.ualberta.ca/dept/aict/uts/software/openbsd/
            //     ports/4.1/i386/openafs/w-openafs-1.4.14-transarc/
            //     openafs-1.4.14/src/usd/usd_nt.c

            // XXX: we can also bump into ERROR_MORE_DATA in which case
            // (quoting doc) we're supposed to retry with a bigger buffer
            // and specify  a new "starting point", whatever it means.
            PyErr_SetFromWindowsErr(0);
            goto error;
        }

        sprintf_s(szDeviceDisplay, MAX_PATH, "PhysicalDrive%i", devNum);
        py_tuple = Py_BuildValue(
            "(IILLKK)",
            diskPerformance.ReadCount,
            diskPerformance.WriteCount,
            diskPerformance.BytesRead,
            diskPerformance.BytesWritten,
            // convert to ms:
            // https://github.com/giampaolo/psutil/issues/1012
            (unsigned long long)
                (diskPerformance.ReadTime.QuadPart) / 10000000,
            (unsigned long long)
                (diskPerformance.WriteTime.QuadPart) / 10000000);
        if (!py_tuple)
            goto error;
        if (PyDict_SetItemString(py_retdict, szDeviceDisplay, py_tuple))
            goto error;
        Py_CLEAR(py_tuple);

next:
        CloseHandle(hDevice);
    }

    return py_retdict;

error:
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retdict);
    if (hDevice != NULL)
        CloseHandle(hDevice);
    return NULL;
}


/*
 * Return disk partitions as a list of tuples such as
 * (drive_letter, drive_letter, type, "")
 */
PyObject *
psutil_disk_partitions(PyObject *self, PyObject *args) {
    DWORD num_bytes;
    char drive_strings[255];
    char *drive_letter = drive_strings;
    char mp_buf[MAX_PATH];
    char mp_path[MAX_PATH];
    int all;
    int type;
    int ret;
    unsigned int old_mode = 0;
    char opts[20];
    HANDLE mp_h;
    BOOL mp_flag= TRUE;
    LPTSTR fs_type[MAX_PATH + 1] = { 0 };
    DWORD pflags = 0;
    PyObject *py_all;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;

    if (py_retlist == NULL) {
        return NULL;
    }

    // avoid to visualize a message box in case something goes wrong
    // see https://github.com/giampaolo/psutil/issues/264
    old_mode = SetErrorMode(SEM_FAILCRITICALERRORS);

    if (! PyArg_ParseTuple(args, "O", &py_all))
        goto error;
    all = PyObject_IsTrue(py_all);

    Py_BEGIN_ALLOW_THREADS
    num_bytes = GetLogicalDriveStrings(254, drive_letter);
    Py_END_ALLOW_THREADS

    if (num_bytes == 0) {
        PyErr_SetFromWindowsErr(0);
        goto error;
    }

    while (*drive_letter != 0) {
        py_tuple = NULL;
        opts[0] = 0;
        fs_type[0] = 0;

        Py_BEGIN_ALLOW_THREADS
        type = GetDriveType(drive_letter);
        Py_END_ALLOW_THREADS

        // by default we only show hard drives and cd-roms
        if (all == 0) {
            if ((type == DRIVE_UNKNOWN) ||
                    (type == DRIVE_NO_ROOT_DIR) ||
                    (type == DRIVE_REMOTE) ||
                    (type == DRIVE_RAMDISK)) {
                goto next;
            }
            // floppy disk: skip it by default as it introduces a
            // considerable slowdown.
            if ((type == DRIVE_REMOVABLE) &&
                    (strcmp(drive_letter, "A:\\")  == 0)) {
                goto next;
            }
        }

        ret = GetVolumeInformation(
            (LPCTSTR)drive_letter, NULL, _ARRAYSIZE(drive_letter),
            NULL, NULL, &pflags, (LPTSTR)fs_type, _ARRAYSIZE(fs_type));
        if (ret == 0) {
            // We might get here in case of a floppy hard drive, in
            // which case the error is (21, "device not ready").
            // Let's pretend it didn't happen as we already have
            // the drive name and type ('removable').
            strcat_s(opts, _countof(opts), "");
            SetLastError(0);
        }
        else {
            if (pflags & FILE_READ_ONLY_VOLUME)
                strcat_s(opts, _countof(opts), "ro");
            else
                strcat_s(opts, _countof(opts), "rw");
            if (pflags & FILE_VOLUME_IS_COMPRESSED)
                strcat_s(opts, _countof(opts), ",compressed");

            // Check for mount points on this volume and add/get info
            // (checks first to know if we can even have mount points)
            if (pflags & FILE_SUPPORTS_REPARSE_POINTS) {
                mp_h = FindFirstVolumeMountPoint(
                    drive_letter, mp_buf, MAX_PATH);
                if (mp_h != INVALID_HANDLE_VALUE) {
                    while (mp_flag) {

                        // Append full mount path with drive letter
                        strcpy_s(mp_path, _countof(mp_path), drive_letter);
                        strcat_s(mp_path, _countof(mp_path), mp_buf);

                        py_tuple = Py_BuildValue(
                            "(ssss)",
                            drive_letter,
                            mp_path,
                            fs_type, // Typically NTFS
                            opts);

                        if (!py_tuple ||
                                PyList_Append(py_retlist, py_tuple) == -1) {
                            FindVolumeMountPointClose(mp_h);
                            goto error;
                        }

                        Py_CLEAR(py_tuple);

                        // Continue looking for more mount points
                        mp_flag = FindNextVolumeMountPoint(
                            mp_h, mp_buf, MAX_PATH);
                    }
                    FindVolumeMountPointClose(mp_h);
                }

            }
        }

        if (strlen(opts) > 0)
            strcat_s(opts, _countof(opts), ",");
        strcat_s(opts, _countof(opts), psutil_get_drive_type(type));

        py_tuple = Py_BuildValue(
            "(ssss)",
            drive_letter,
            drive_letter,
            fs_type,  // either FAT, FAT32, NTFS, HPFS, CDFS, UDF or NWFS
            opts);
        if (!py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_CLEAR(py_tuple);
        goto next;

next:
        drive_letter = strchr(drive_letter, 0) + 1;
    }

    SetErrorMode(old_mode);
    return py_retlist;

error:
    SetErrorMode(old_mode);
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    return NULL;
}


/*
 Accept a filename's drive in native  format like "\Device\HarddiskVolume1\"
 and return the corresponding drive letter (e.g. "C:\\").
 If no match is found return an empty string.
*/
PyObject *
psutil_win32_QueryDosDevice(PyObject *self, PyObject *args) {
    LPCTSTR lpDevicePath;
    TCHAR d = TEXT('A');
    TCHAR szBuff[5];

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
