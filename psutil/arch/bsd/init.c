/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <stdio.h>
#include <string.h>

#include "../../arch/all/init.h"


void
convert_kvm_err(const char *syscall, char *errbuf) {
    char fullmsg[512];

    str_format(
        fullmsg, sizeof(fullmsg), "(originated from %s: %s)", syscall, errbuf
    );
    if (strstr(errbuf, "Permission denied") != NULL)
        psutil_oserror_ad(fullmsg);
    else if (strstr(errbuf, "Operation not permitted") != NULL)
        psutil_oserror_ad(fullmsg);
    else
        psutil_runtime_error(fullmsg);
}
