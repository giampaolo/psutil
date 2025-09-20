/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/resource.h>
#include <sys/socket.h>

/*
 * From "man getpagesize" on Linux, https://linux.die.net/man/2/getpagesize:
 *
 * > In SUSv2 the getpagesize() call is labeled LEGACY, and in POSIX.1-2001
 * > it has been dropped.
 * > Portable applications should employ sysconf(_SC_PAGESIZE) instead
 * > of getpagesize().
 * > Most systems allow the synonym _SC_PAGE_SIZE for _SC_PAGESIZE.
 * > Whether getpagesize() is present as a Linux system call depends on the
 * > architecture.
 */
long
psutil_getpagesize(void) {
#ifdef _SC_PAGESIZE
    // recommended POSIX
    return sysconf(_SC_PAGESIZE);
#elif _SC_PAGE_SIZE
    // alias
    return sysconf(_SC_PAGE_SIZE);
#else
    // legacy
    return (long) getpagesize();
#endif
}


// Exposed so we can test it against Python's stdlib.
PyObject *
psutil_getpagesize_pywrapper(PyObject *self, PyObject *args) {
    return Py_BuildValue("l", psutil_getpagesize());
}
