/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>

#include "../../arch/all/init.h"


#ifndef _ARRAYSIZE
#define _ARRAYSIZE(a) (sizeof(a) / sizeof(a[0]))
#endif


PyObject *
psutil_disk_usage(PyObject *self, PyObject *args) {
    PyObject *py_path;
    wchar_t *path = NULL;
    ULARGE_INTEGER total, free, avail;
    BOOL retval;
    ULONGLONG used;

    if (!PyArg_ParseTuple(args, "U", &py_path)) {
        return NULL;
    }

    path = PyUnicode_AsWideCharString(py_path, NULL);
    if (path == NULL) {
        return NULL;
    }

    Py_BEGIN_ALLOW_THREADS
    retval = GetDiskFreeSpaceExW(path, &avail, &total, &free);
    Py_END_ALLOW_THREADS

    PyMem_Free(path);

    if (retval == 0) {
        return PyErr_SetExcFromWindowsErrWithFilenameObject(
            PyExc_OSError, 0, py_path
        );
    }

    used = total.QuadPart - free.QuadPart;
    return Py_BuildValue("(KKK)", total.QuadPart, used, free.QuadPart);
}


PyObject *
psutil_disk_io_counters(PyObject *self, PyObject *args) {
    DISK_PERFORMANCE *diskPerformance = NULL;
    DWORD dwSize;
    HANDLE hDevice = NULL;
    char szDevice[MAX_PATH];
    char szDeviceDisplay[MAX_PATH];
    int devNum;
    DWORD ioctrlSize;
    BOOL ret;
    PyObject *py_retdict = PyDict_New();
    PyObject *py_tuple = NULL;

    if (py_retdict == NULL)
        return NULL;

    // Drivers may return a bigger struct than the one we know about,
    // in which case the ioctl below asks for a bigger buffer.
    ioctrlSize = sizeof(DISK_PERFORMANCE);
    diskPerformance = malloc(ioctrlSize);
    if (diskPerformance == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    // Apparently there's no way to figure out how many times we have
    // to iterate in order to find valid drives.
    // Let's assume 32, which is higher than 26, the number of letters
    // in the alphabet (from A:\ to Z:\).
    for (devNum = 0; devNum <= 32; ++devNum) {
        py_tuple = NULL;
        str_format(szDevice, MAX_PATH, "\\\\.\\PhysicalDrive%d", devNum);
        // Opening a disk device may block, so do it without the GIL.
        Py_BEGIN_ALLOW_THREADS
        hDevice = CreateFile(
            szDevice,
            0,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            NULL,
            OPEN_EXISTING,
            0,
            NULL
        );
        Py_END_ALLOW_THREADS
        if (hDevice == INVALID_HANDLE_VALUE)
            continue;

        // DeviceIoControl() sucks!
        while (1) {
            Py_BEGIN_ALLOW_THREADS
            ret = DeviceIoControl(
                hDevice,
                IOCTL_DISK_PERFORMANCE,
                NULL,
                0,
                diskPerformance,
                ioctrlSize,
                &dwSize,
                NULL
            );
            Py_END_ALLOW_THREADS
            if (ret != 0)
                break;  // OK!
            if (GetLastError() == ERROR_INSUFFICIENT_BUFFER) {
                // Grow the buffer for real, up to a sane limit.
                if (ioctrlSize < 1024 * 1024) {
                    void *tmp;

                    ioctrlSize *= 2;
                    tmp = realloc(diskPerformance, ioctrlSize);
                    if (tmp == NULL) {
                        PyErr_NoMemory();
                        goto error;
                    }
                    diskPerformance = tmp;
                    continue;
                }
            }
            else if (GetLastError() == ERROR_INVALID_FUNCTION) {
                // This happens on AppVeyor:
                // https://ci.appveyor.com/project/giampaolo/psutil/build/1364/job/ascpdi271b06jle3
                // Assume it means we're dealing with some exotic disk
                // and go on.
                psutil_debug(
                    "DeviceIoControl -> ERROR_INVALID_FUNCTION; "
                    "ignore PhysicalDrive%i",
                    devNum
                );
                goto next;
            }
            else if (GetLastError() == ERROR_NOT_SUPPORTED) {
                // Again, let's assume we're dealing with some exotic disk.
                psutil_debug(
                    "DeviceIoControl -> ERROR_NOT_SUPPORTED; "
                    "ignore PhysicalDrive%i",
                    devNum
                );
                goto next;
            }
            // XXX: it seems we should also catch ERROR_INVALID_PARAMETER:
            // https://sites.ualberta.ca/dept/aict/uts/software/openbsd/ports/4.1/i386/openafs/w-openafs-1.4.14-transarc/openafs-1.4.14/src/usd/usd_nt.c

            // XXX: we can also bump into ERROR_MORE_DATA in which case
            // (quoting doc) we're supposed to retry with a bigger buffer
            // and specify  a new "starting point", whatever it means.
            psutil_oserror();
            goto error;
        }

        str_format(szDeviceDisplay, MAX_PATH, "PhysicalDrive%i", devNum);
        py_tuple = Py_BuildValue(
            "(IILLKK)",
            diskPerformance->ReadCount,
            diskPerformance->WriteCount,
            diskPerformance->BytesRead.QuadPart,
            diskPerformance->BytesWritten.QuadPart,
            // convert to ms:
            // https://github.com/giampaolo/psutil/issues/1012
            (unsigned long long)(diskPerformance->ReadTime.QuadPart)
                / 10000000,
            (unsigned long long)(diskPerformance->WriteTime.QuadPart)
                / 10000000
        );
        if (!py_tuple)
            goto error;
        if (PyDict_SetItemString(py_retdict, szDeviceDisplay, py_tuple))
            goto error;
        Py_CLEAR(py_tuple);

    next:
        CloseHandle(hDevice);
    }

    free(diskPerformance);
    return py_retdict;

error:
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retdict);
    if (hDevice != NULL && hDevice != INVALID_HANDLE_VALUE)
        CloseHandle(hDevice);
    if (diskPerformance != NULL)
        free(diskPerformance);
    return NULL;
}

// ---  disk_partitions()

static char *
get_drive_type(int type) {
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


// Fill fs_type (e.g. "NTFS") and opts (e.g. "rw,fixed") of the volume
// at root (e.g. "C:\" or "\\?\Volume{...}\").
static void
get_volume_info(
    const wchar_t *root,
    int type,
    wchar_t *fs_type,
    DWORD fs_type_size,
    char *opts,
    size_t opts_size
) {
    BOOL ret;
    DWORD pflags = 0;

    fs_type[0] = 0;
    opts[0] = 0;

    // May spin up a removable drive or go over the wire for a
    // network one, so do it without the GIL.
    Py_BEGIN_ALLOW_THREADS
    ret = GetVolumeInformationW(
        root,
        NULL,  // we don't want the volume name
        0,
        NULL,
        NULL,
        &pflags,
        fs_type,
        fs_type_size
    );
    Py_END_ALLOW_THREADS

    if (ret == 0) {
        // We might get here in case of a floppy hard drive, in
        // which case the error is (21, "device not ready").
        // Let's pretend it didn't happen as we already have
        // the drive name and type ('removable'). opts is left
        // empty.
        SetLastError(0);
    }
    else {
        if (pflags & FILE_READ_ONLY_VOLUME)
            str_append(opts, opts_size, "ro");
        else
            str_append(opts, opts_size, "rw");
        if (pflags & FILE_VOLUME_IS_COMPRESSED)
            str_append(opts, opts_size, ",compressed");
        if (pflags & FILE_READ_ONLY_VOLUME)
            str_append(opts, opts_size, ",readonly");
    }

    if (strlen(opts) > 0)
        str_append(opts, opts_size, ",");
    str_append(opts, opts_size, get_drive_type(type));
}


// Volumes mounted in a folder (e.g. "C:\mnt\data\"). Go through all
// volumes because FindFirstVolumeMountPointW() needs admin rights,
// see https://github.com/giampaolo/psutil/issues/1986.
static int
append_folder_mounts(PyObject *py_retlist, int all) {
    wchar_t volume[MAX_PATH];
    wchar_t fs_type[MAX_PATH + 1];
    wchar_t *paths = NULL;
    wchar_t *path;
    wchar_t *device;
    char opts[50];
    DWORD size = MAX_PATH + 1;
    DWORD needed;
    BOOL has_folder;
    HANDLE h;
    int type;
    int ret = -1;

    h = FindFirstVolumeW(volume, _ARRAYSIZE(volume));
    if (h == INVALID_HANDLE_VALUE) {
        psutil_debug("FindFirstVolumeW failed (err=%lu)", GetLastError());
        return 0;
    }
    paths = malloc(size * sizeof(wchar_t));
    if (paths == NULL) {
        PyErr_NoMemory();
        goto done;
    }

    do {
        // the drive letters and folders the volume is mounted in
        while (!GetVolumePathNamesForVolumeNameW(volume, paths, size, &needed))
        {
            if (GetLastError() != ERROR_MORE_DATA) {
                psutil_debug("GetVolumePathNamesForVolumeNameW failed");
                paths[0] = 0;
                break;
            }
            free(paths);
            size = needed;
            paths = malloc(size * sizeof(wchar_t));
            if (paths == NULL) {
                PyErr_NoMemory();
                goto done;
            }
        }

        // the volume's drive letter, or the folder if it has none
        device = NULL;
        has_folder = FALSE;
        for (path = paths; *path != 0; path += wcslen(path) + 1) {
            if (wcslen(path) == 3)  // "C:\"
                device = path;
            else
                has_folder = TRUE;
        }
        if (!has_folder)
            continue;

        Py_BEGIN_ALLOW_THREADS
        type = GetDriveTypeW(volume);
        Py_END_ALLOW_THREADS

        // by default we only show hard drives and cd-roms
        if (!all && (type != DRIVE_FIXED) && (type != DRIVE_REMOVABLE)
            && (type != DRIVE_CDROM))
        {
            continue;
        }
        get_volume_info(
            volume, type, fs_type, _ARRAYSIZE(fs_type), opts, sizeof(opts)
        );

        for (path = paths; *path != 0; path += wcslen(path) + 1) {
            if (wcslen(path) == 3)
                continue;
            if (!pylist_append_fmt(
                    py_retlist,
                    "(uuus)",
                    device ? device : path,
                    path,
                    fs_type,
                    opts
                ))
            {
                goto done;
            }
        }
    } while (FindNextVolumeW(h, volume, _ARRAYSIZE(volume)));

    if (GetLastError() != ERROR_NO_MORE_FILES)
        psutil_debug("FindNextVolumeW failed (err=%lu)", GetLastError());
    ret = 0;

done:
    free(paths);
    FindVolumeClose(h);
    return ret;
}


PyObject *
psutil_disk_partitions(PyObject *self, PyObject *args) {
    DWORD num_chars;
    wchar_t drive_strings[255];
    wchar_t *drive_letter = drive_strings;
    int all = 0;
    int type;
    unsigned int old_mode = 0;
    char opts[50];
    wchar_t fs_type[MAX_PATH + 1] = {0};
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL) {
        return NULL;
    }

    // avoid to visualize a message box in case something goes wrong
    // see https://github.com/giampaolo/psutil/issues/264
    old_mode = SetErrorMode(SEM_FAILCRITICALERRORS);

    if (!PyArg_ParseTuple(args, "p", &all))
        goto error;

    Py_BEGIN_ALLOW_THREADS
    num_chars = GetLogicalDriveStringsW(254, drive_letter);
    Py_END_ALLOW_THREADS

    if (num_chars == 0) {
        psutil_oserror_wsyscall("GetLogicalDriveStringsW");
        goto error;
    }

    while (*drive_letter != 0) {
        Py_BEGIN_ALLOW_THREADS
        type = GetDriveTypeW(drive_letter);
        Py_END_ALLOW_THREADS

        // by default we only show hard drives and cd-roms
        if (all == 0) {
            if ((type == DRIVE_UNKNOWN) || (type == DRIVE_NO_ROOT_DIR)
                || (type == DRIVE_REMOTE) || (type == DRIVE_RAMDISK))
            {
                goto next;
            }
            // floppy disk: skip it by default as it introduces a
            // considerable slowdown.
            if ((type == DRIVE_REMOVABLE)
                && (wcscmp(drive_letter, L"A:\\") == 0))
            {
                goto next;
            }
        }

        get_volume_info(
            drive_letter,
            type,
            fs_type,
            _ARRAYSIZE(fs_type),
            opts,
            sizeof(opts)
        );

        if (!pylist_append_fmt(
                py_retlist,
                "(uuus)",
                drive_letter,
                drive_letter,
                fs_type,  // either FAT, FAT32, NTFS, HPFS, CDFS, UDF or NWFS
                opts
            ))
        {
            goto error;
        }

    next:
        drive_letter = wcschr(drive_letter, 0) + 1;
    }

    if (append_folder_mounts(py_retlist, all) != 0)
        goto error;

    SetErrorMode(old_mode);
    return py_retlist;

error:
    SetErrorMode(old_mode);
    Py_DECREF(py_retlist);
    return NULL;
}


// Accept a filename's drive in native  format like "\Device\HarddiskVolume1\"
// and return the corresponding drive letter (e.g. "C:\\").
// If no match is found return an empty string.
PyObject *
psutil_QueryDosDevice(PyObject *self, PyObject *args) {
    PyObject *py_device_path;
    PyObject *py_ret = NULL;
    wchar_t *device_path;
    wchar_t d = L'A';

    if (!PyArg_ParseTuple(args, "U", &py_device_path))
        return NULL;

    device_path = PyUnicode_AsWideCharString(py_device_path, NULL);
    if (device_path == NULL)
        return NULL;

    while (d <= L'Z') {
        wchar_t szDeviceName[3] = {d, L':', L'\0'};
        wchar_t szTarget[512] = {0};
        if (QueryDosDeviceW(szDeviceName, szTarget, 511) != 0) {
            if (wcscmp(device_path, szTarget) == 0) {
                py_ret = PyUnicode_FromWideChar(
                    szDeviceName, wcslen(szDeviceName)
                );
                PyMem_Free(device_path);
                return py_ret;
            }
        }
        d++;
    }
    PyMem_Free(device_path);
    return PyUnicode_FromString("");
}
