/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// Disk related functions. Original code was refactored and moved
// from psutil/_psutil_osx.c in 2023. This is the GIT blame before the move:
// https://github.com/giampaolo/psutil/blame/efd7ed3/psutil/_psutil_osx.c

#include <Python.h>
#include <sys/param.h>
#include <sys/ucred.h>
#include <sys/mount.h>
#include <CoreFoundation/CoreFoundation.h>
#include <IOKit/IOKitLib.h>
#include <IOKit/storage/IOBlockStorageDriver.h>
#include <IOKit/storage/IOMedia.h>
#include <IOKit/IOBSD.h>

#include "../../arch/all/init.h"


/*
 * Return a list of tuples including device, mount point and fs type
 * for all partitions mounted on the system.
 */
PyObject *
psutil_disk_partitions(PyObject *self, PyObject *args) {
    int num;
    int i;
    int len;
    uint64_t flags;
    char opts[400];
    struct statfs *fs = NULL;
    PyObject *py_dev = NULL;
    PyObject *py_mountp = NULL;
    PyObject *py_tuple = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;

    // get the number of mount points
    Py_BEGIN_ALLOW_THREADS
    num = getfsstat(NULL, 0, MNT_NOWAIT);
    Py_END_ALLOW_THREADS
    if (num == -1) {
        psutil_oserror();
        goto error;
    }

    len = sizeof(*fs) * num;
    fs = malloc(len);
    if (fs == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    Py_BEGIN_ALLOW_THREADS
    num = getfsstat(fs, len, MNT_NOWAIT);
    Py_END_ALLOW_THREADS
    if (num == -1) {
        psutil_oserror();
        goto error;
    }

    for (i = 0; i < num; i++) {
        opts[0] = 0;
        flags = fs[i].f_flags;

        // see sys/mount.h
        if (flags & MNT_RDONLY)
            str_append(opts, sizeof(opts), "ro");
        else
            str_append(opts, sizeof(opts), "rw");
        if (flags & MNT_SYNCHRONOUS)
            str_append(opts, sizeof(opts), ",sync");
        if (flags & MNT_NOEXEC)
            str_append(opts, sizeof(opts), ",noexec");
        if (flags & MNT_NOSUID)
            str_append(opts, sizeof(opts), ",nosuid");
        if (flags & MNT_UNION)
            str_append(opts, sizeof(opts), ",union");
        if (flags & MNT_ASYNC)
            str_append(opts, sizeof(opts), ",async");
        if (flags & MNT_EXPORTED)
            str_append(opts, sizeof(opts), ",exported");
        if (flags & MNT_LOCAL)
            str_append(opts, sizeof(opts), ",local");
        if (flags & MNT_QUOTA)
            str_append(opts, sizeof(opts), ",quota");
        if (flags & MNT_ROOTFS)
            str_append(opts, sizeof(opts), ",rootfs");
        if (flags & MNT_DOVOLFS)
            str_append(opts, sizeof(opts), ",dovolfs");
        if (flags & MNT_DONTBROWSE)
            str_append(opts, sizeof(opts), ",dontbrowse");
        if (flags & MNT_IGNORE_OWNERSHIP)
            str_append(opts, sizeof(opts), ",ignore-ownership");
        if (flags & MNT_AUTOMOUNTED)
            str_append(opts, sizeof(opts), ",automounted");
        if (flags & MNT_JOURNALED)
            str_append(opts, sizeof(opts), ",journaled");
        if (flags & MNT_NOUSERXATTR)
            str_append(opts, sizeof(opts), ",nouserxattr");
        if (flags & MNT_DEFWRITE)
            str_append(opts, sizeof(opts), ",defwrite");
        if (flags & MNT_UPDATE)
            str_append(opts, sizeof(opts), ",update");
        if (flags & MNT_RELOAD)
            str_append(opts, sizeof(opts), ",reload");
        if (flags & MNT_FORCE)
            str_append(opts, sizeof(opts), ",force");
        if (flags & MNT_CMDFLAGS)
            str_append(opts, sizeof(opts), ",cmdflags");
            // requires macOS >= 10.5
#ifdef MNT_QUARANTINE
        if (flags & MNT_QUARANTINE)
            str_append(opts, sizeof(opts), ",quarantine");
#endif
#ifdef MNT_MULTILABEL
        if (flags & MNT_MULTILABEL)
            str_append(opts, sizeof(opts), ",multilabel");
#endif
#ifdef MNT_NOATIME
        if (flags & MNT_NOATIME)
            str_append(opts, sizeof(opts), ",noatime");
#endif
        py_dev = PyUnicode_DecodeFSDefault(fs[i].f_mntfromname);
        if (!py_dev)
            goto error;
        py_mountp = PyUnicode_DecodeFSDefault(fs[i].f_mntonname);
        if (!py_mountp)
            goto error;
        py_tuple = Py_BuildValue(
            "(OOss)",
            py_dev,  // device
            py_mountp,  // mount point
            fs[i].f_fstypename,  // fs type
            opts  // options
        );
        if (!py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_CLEAR(py_dev);
        Py_CLEAR(py_mountp);
        Py_CLEAR(py_tuple);
    }

    free(fs);
    return py_retlist;

error:
    Py_XDECREF(py_dev);
    Py_XDECREF(py_mountp);
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    if (fs != NULL)
        free(fs);
    return NULL;
}


PyObject *
psutil_disk_usage_used(PyObject *self, PyObject *args) {
    PyObject *py_default_value;
    PyObject *py_mount_point_bytes = NULL;
    char *mount_point;

    if (!PyArg_ParseTuple(
            args,
            "O&O",
            PyUnicode_FSConverter,
            &py_mount_point_bytes,
            &py_default_value
        ))
    {
        return NULL;
    }
    mount_point = PyBytes_AsString(py_mount_point_bytes);
    if (NULL == mount_point) {
        Py_XDECREF(py_mount_point_bytes);
        return NULL;
    }

#ifdef ATTR_VOL_SPACEUSED
    /* Call getattrlist(ATTR_VOL_SPACEUSED) to get used space info. */
    int ret;
    struct {
        uint32_t size;
        uint64_t spaceused;
    } __attribute__((aligned(4), packed)) attrbuf = {0};
    struct attrlist attrs = {0};

    attrs.bitmapcount = ATTR_BIT_MAP_COUNT;
    attrs.volattr = ATTR_VOL_INFO | ATTR_VOL_SPACEUSED;
    attrbuf.size = sizeof(attrbuf);

    Py_BEGIN_ALLOW_THREADS
    ret = getattrlist(mount_point, &attrs, &attrbuf, sizeof(attrbuf), 0);
    Py_END_ALLOW_THREADS
    if (ret == 0) {
        Py_XDECREF(py_mount_point_bytes);
        return PyLong_FromUnsignedLongLong(attrbuf.spaceused);
    }
    psutil_debug(
        "getattrlist(ATTR_VOL_SPACEUSED) failed, fall-back to default value"
    );
#endif
    Py_XDECREF(py_mount_point_bytes);
    Py_INCREF(py_default_value);
    return py_default_value;
}


/*
 * Return a Python dict of tuples for disk I/O information
 */
PyObject *
psutil_disk_io_counters(PyObject *self, PyObject *args) {
    CFDictionaryRef parent_dict = NULL;
    CFDictionaryRef props_dict = NULL;
    CFDictionaryRef stats_dict = NULL;
    io_registry_entry_t parent = IO_OBJECT_NULL;
    io_registry_entry_t disk = IO_OBJECT_NULL;
    io_iterator_t disk_list = IO_OBJECT_NULL;
    PyObject *py_disk_info = NULL;
    PyObject *py_retdict = PyDict_New();

    if (py_retdict == NULL)
        return NULL;

    if (IOServiceGetMatchingServices(
            kIOMasterPortDefault, IOServiceMatching(kIOMediaClass), &disk_list
        )
        != kIOReturnSuccess)
    {
        psutil_runtime_error("unable to get the list of disks");
        goto error;
    }

    while ((disk = IOIteratorNext(disk_list)) != 0) {
        py_disk_info = NULL;
        parent_dict = NULL;
        props_dict = NULL;
        stats_dict = NULL;
        parent = IO_OBJECT_NULL;

        if (IORegistryEntryGetParentEntry(disk, kIOServicePlane, &parent)
            != kIOReturnSuccess)
        {
            psutil_runtime_error("unable to get the disk's parent");
            goto error;
        }

        if (!IOObjectConformsTo(parent, "IOBlockStorageDriver")) {
            IOObjectRelease(parent);
            IOObjectRelease(disk);
            continue;
        }

        if (IORegistryEntryCreateCFProperties(
                disk,
                (CFMutableDictionaryRef *)&parent_dict,
                kCFAllocatorDefault,
                kNilOptions
            )
            != kIOReturnSuccess)
        {
            psutil_runtime_error("unable to get the parent's properties");
            goto error;
        }

        if (IORegistryEntryCreateCFProperties(
                parent,
                (CFMutableDictionaryRef *)&props_dict,
                kCFAllocatorDefault,
                kNilOptions
            )
            != kIOReturnSuccess)
        {
            psutil_runtime_error("unable to get the disk properties");
            goto error;
        }

        CFStringRef disk_name_ref = (CFStringRef
        )CFDictionaryGetValue(parent_dict, CFSTR(kIOBSDNameKey));
        if (disk_name_ref == NULL) {
            psutil_runtime_error("unable to get disk name");
            goto error;
        }

        const int kMaxDiskNameSize = 64;
        char disk_name[kMaxDiskNameSize];
        if (!CFStringGetCString(
                disk_name_ref,
                disk_name,
                kMaxDiskNameSize,
                CFStringGetSystemEncoding()
            ))
        {
            psutil_runtime_error("unable to convert disk name to C string");
            goto error;
        }

        stats_dict = (CFDictionaryRef)CFDictionaryGetValue(
            props_dict, CFSTR(kIOBlockStorageDriverStatisticsKey)
        );
        if (stats_dict == NULL) {
            psutil_runtime_error("unable to get disk stats");
            goto error;
        }

        CFNumberRef number;
        int64_t reads = 0, writes = 0, read_bytes = 0, write_bytes = 0;
        int64_t read_time = 0, write_time = 0;

        if ((number = (CFNumberRef)CFDictionaryGetValue(
                 stats_dict, CFSTR(kIOBlockStorageDriverStatisticsReadsKey)
             )))
            CFNumberGetValue(number, kCFNumberSInt64Type, &reads);

        if ((number = (CFNumberRef)CFDictionaryGetValue(
                 stats_dict, CFSTR(kIOBlockStorageDriverStatisticsWritesKey)
             )))
            CFNumberGetValue(number, kCFNumberSInt64Type, &writes);

        if ((number = (CFNumberRef)CFDictionaryGetValue(
                 stats_dict, CFSTR(kIOBlockStorageDriverStatisticsBytesReadKey)
             )))
            CFNumberGetValue(number, kCFNumberSInt64Type, &read_bytes);

        if ((number = (CFNumberRef)CFDictionaryGetValue(
                 stats_dict,
                 CFSTR(kIOBlockStorageDriverStatisticsBytesWrittenKey)
             )))
            CFNumberGetValue(number, kCFNumberSInt64Type, &write_bytes);

        if ((number = (CFNumberRef)CFDictionaryGetValue(
                 stats_dict,
                 CFSTR(kIOBlockStorageDriverStatisticsTotalReadTimeKey)
             )))
            CFNumberGetValue(number, kCFNumberSInt64Type, &read_time);

        if ((number = (CFNumberRef)CFDictionaryGetValue(
                 stats_dict,
                 CFSTR(kIOBlockStorageDriverStatisticsTotalWriteTimeKey)
             )))
            CFNumberGetValue(number, kCFNumberSInt64Type, &write_time);

        py_disk_info = Py_BuildValue(
            "(KKKKKK)",
            (unsigned long long)reads,
            (unsigned long long)writes,
            (unsigned long long)read_bytes,
            (unsigned long long)write_bytes,
            (unsigned long long)(read_time / 1000 / 1000),
            (unsigned long long)(write_time / 1000 / 1000)
        );

        if (!py_disk_info)
            goto error;

        if (PyDict_SetItemString(py_retdict, disk_name, py_disk_info)) {
            Py_CLEAR(py_disk_info);
            goto error;
        }

        Py_CLEAR(py_disk_info);

        if (parent_dict)
            CFRelease(parent_dict);
        if (props_dict)
            CFRelease(props_dict);
        IOObjectRelease(parent);
        IOObjectRelease(disk);
    }

    IOObjectRelease(disk_list);
    return py_retdict;

error:
    Py_XDECREF(py_disk_info);
    Py_DECREF(py_retdict);
    if (parent_dict)
        CFRelease(parent_dict);
    if (props_dict)
        CFRelease(props_dict);
    if (parent != IO_OBJECT_NULL)
        IOObjectRelease(parent);
    if (disk != IO_OBJECT_NULL)
        IOObjectRelease(disk);
    if (disk_list != IO_OBJECT_NULL)
        IOObjectRelease(disk_list);
    return NULL;
}
