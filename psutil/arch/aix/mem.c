/*
 * Copyright (c) 2009, Giampaolo Rodola'
 * Copyright (c) 2017, Arnon Yaari
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// AIX support is experimental at this time.
// The following functions and methods are unsupported on the AIX platform:
// - psutil.Process.memory_maps
//
// Known limitations:
// - psutil.Process.io_counters read count is always 0
// - psutil.Process.io_counters may not be available on older AIX versions
// - psutil.Process.threads may not be available on older AIX versions
// - psutil.net_io_counters may not be available on older AIX versions
// - reading basic process info may fail or return incorrect values when
//   process is starting (see IBM APAR IV58499 - fixed in newer AIX versions)
// - sockets and pipes may not be counted in num_fds (fixed in newer AIX
//   versions)
//
// Useful resources:
// - proc filesystem:
// http://www-01.ibm.com/support/knowledgecenter/ssw_aix_72/com.ibm.aix.files/proc.htm
// - libperfstat:
// http://www-01.ibm.com/support/knowledgecenter/ssw_aix_72/com.ibm.aix.files/libperfstat.h.htm

#include <Python.h>
#include <sys/limits.h>
#include <sys/proc.h>
#include <sys/procfs.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/sysinfo.h>
#include <sys/thread.h>
#include <sys/types.h>
#include <fcntl.h>
#include <utmp.h>
#include <utmpx.h>
#include <mntent.h>
#include <sys/ioctl.h>
#include <sys/tihdr.h>
#include <stropts.h>
#include <netinet/tcp_fsm.h>
#include <arpa/inet.h>
#include <net/if.h>
#include <libperfstat.h>
#include <unistd.h>

#include "../../arch/all/init.h"
#include "ifaddrs.h"
#include "net_connections.h"
#include "common.h"


#define TV2DOUBLE(t) (((t).tv_nsec * 0.000000001) + (t).tv_sec)


static PyObject *
psutil_virtual_mem(PyObject *self, PyObject *args) {
    int rc;
    long pagesize = psutil_getpagesize();
    perfstat_memory_total_t memory;

    rc = perfstat_memory_total(
        NULL, &memory, sizeof(perfstat_memory_total_t), 1
    );
    if (rc <= 0) {
        psutil_oserror();
        return NULL;
    }

    return Py_BuildValue(
        "KKKKK",
        (unsigned long long)memory.real_total * pagesize,
        (unsigned long long)memory.real_avail * pagesize,
        (unsigned long long)memory.real_free * pagesize,
        (unsigned long long)memory.real_pinned * pagesize,
        (unsigned long long)memory.real_inuse * pagesize
    );
}


static PyObject *
psutil_swap_mem(PyObject *self, PyObject *args) {
    int rc;
    long pagesize = psutil_getpagesize();
    perfstat_memory_total_t memory;

    rc = perfstat_memory_total(
        NULL, &memory, sizeof(perfstat_memory_total_t), 1
    );
    if (rc <= 0) {
        psutil_oserror();
        return NULL;
    }

    return Py_BuildValue(
        "KKKK",
        (unsigned long long)memory.pgsp_total * pagesize,
        (unsigned long long)memory.pgsp_free * pagesize,
        (unsigned long long)memory.pgins * pagesize,
        (unsigned long long)memory.pgouts * pagesize
    );
}
