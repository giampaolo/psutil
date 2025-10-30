/*
 * Copyright (c) 2009, Giampaolo Rodola. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// String utilities

#include <stdio.h>
#include <stdarg.h>
#include <stddef.h>


// Safely formats a string into a buffer. Writes a printf-style
// formatted string into `buf` of size `size`, always null-terminating
// if size > 0. Returns the number of characters written (excluding the
// null terminator) on success, or -1 if the buffer is too small or an
// error occurs.
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
