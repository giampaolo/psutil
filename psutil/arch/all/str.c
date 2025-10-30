/*
 * Copyright (c) 2009, Giampaolo Rodola. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// String utilities

#include <stdio.h>
#include <stdarg.h>
#include <stddef.h>


int
str_format(char *buf, size_t size, const char *fmt, ...) {
    va_list args;
    int ret;

    if (size == 0)
        return -1;

    va_start(args, fmt);
#if defined(PSUTIL_WINDOWS)
    ret = _vsnprintf(buf, size, fmt, args);
#else
    ret = vsnprintf(buf, size, fmt, args);
#endif
    va_end(args);

    if (ret < 0 || (size_t)ret >= size) {
        buf[size - 1] = '\0';
        return -1;
    }
    return ret;
}
