/*
 * Copyright (c) 2009, Giampaolo Rodola. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// String utilities.

#include <stdarg.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "init.h"


static int
str_error(const char *fmt, ...) {
    char msg[256];
    va_list args;
    int ret;

    va_start(args, fmt);
    ret = vsnprintf(msg, sizeof(msg), fmt, args);
    va_end(args);
    // If vsnprintf() failed msg is garbage.
    if (ret < 0)
        str_copy(msg, sizeof(msg), "str_error: bad format");

    // Warn because we never check str_*() return value.
    psutil_warn("%s", msg);
    return -1;
}


// Safely formats a string into a buffer. Writes a printf-style
// formatted string into `buf` of size `size`, always null-terminating
// if size > 0. Returns the number of characters written (excluding the
// null terminator) on success, or -1 if the buffer is too small or an
// error occurs.
int
str_format(char *buf, size_t size, const char *fmt, ...) {
    va_list args;
    int ret;

    if (!buf || !fmt || size == 0)
        return str_error("str_format: invalid arg");

    va_start(args, fmt);
#if defined(PSUTIL_WINDOWS)
    ret = _vsnprintf_s(buf, size, _TRUNCATE, fmt, args);
#else
    ret = vsnprintf(buf, size, fmt, args);
#endif
    va_end(args);

    if (ret < 0 || (size_t)ret >= size) {
        buf[size - 1] = '\0';
        return str_error("str_format: failed or truncated, fmt '%s'", fmt);
    }
    return ret;
}


// Safely copy `src` to `dst`, always null-terminating. Replaces unsafe
// strcpy/strncpy. Returns 0 on success, -1 on truncation, in which
// case dst holds as much of src as fits.
// memmove() and not memcpy(): memcpy links memcpy@GLIBC_2.14 on
// x86_64 Linux, raising the min glibc our Linux wheels require.
int
str_copy(char *dst, size_t dst_size, const char *src) {
    size_t src_len;

    if (!dst || !src || dst_size == 0)
        return str_error("str_copy: invalid arg");

    src_len = strlen(src);
    if (src_len >= dst_size) {
        memmove(dst, src, dst_size - 1);
        dst[dst_size - 1] = '\0';
        return str_error("str_copy: truncated");
    }
    memmove(dst, src, src_len + 1);
    return 0;
}


// Safely append `src` to `dst`, always null-terminating. Returns 0 on
// success, -1 on truncation, in which case dst holds as much of src
// as fits.
int
str_append(char *dst, size_t dst_size, const char *src) {
    size_t dst_len, src_len, avail;

    if (!dst || !src || dst_size == 0)
        return str_error("str_append: invalid arg");

    dst_len = strnlen(dst, dst_size);
    if (dst_len >= dst_size)
        return str_error("str_append: dst is not null-terminated");

    src_len = strlen(src);
    avail = dst_size - dst_len - 1;
    if (src_len > avail) {
        memmove(dst + dst_len, src, avail);
        dst[dst_size - 1] = '\0';
        return str_error("str_append: truncated");
    }
    memmove(dst + dst_len, src, src_len + 1);
    return 0;
}
