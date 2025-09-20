/*
 * Copyright (c) 2017, Arnon Yaari
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#ifndef __PSUTIL_AIX_COMMON_H__
#define __PSUTIL_AIX_COMMON_H__

#include <sys/core.h>

#define PROCINFO_INCR   (256)
#define PROCSIZE        (sizeof(struct procentry64))
#define FDSINFOSIZE     (sizeof(struct fdsinfo64))
#define KMEM            "/dev/kmem"

typedef u_longlong_t    KA_T;

/* psutil_kread() - read from kernel memory */
int psutil_kread(int Kd,     /* kernel memory file descriptor */
    KA_T addr,               /* kernel memory address */
    char *buf,               /* buffer to receive data */
    size_t len);             /* length to read */

struct procentry64 *
psutil_read_process_table(
    int * num               /* out - number of processes read */
);

#endif  /* __PSUTIL_AIX_COMMON_H__ */
