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
_error(const char *msg) {
    if (PSUTIL_TESTING) {
        fprintf(stderr, "CRITICAL: %s\n", msg);
        fflush(stderr);
        exit(EXIT_FAILURE);  // terminate execution
    }
    else {
        // Print debug msg because we never check str_*() return value.
        psutil_debug("%s", msg);
    }
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

    if (size == 0)
        return _error("str_format: invalid arg 'size' = 0");

    va_start(args, fmt);
#if defined(PSUTIL_WINDOWS)
    ret = _vsnprintf_s(buf, size, _TRUNCATE, fmt, args);
#else
    ret = vsnprintf(buf, size, fmt, args);
#endif
    va_end(args);

    if (ret < 0 || (size_t)ret >= size) {
        psutil_debug("str_format: error in format '%s'", fmt);
        buf[size - 1] = '\0';
        return -1;
    }
    return ret;
}


// Safely copy `src` to `dst`, always null-terminating. Replaces unsafe
// strcpy/strncpy.
int
str_copy(char *dst, size_t dst_size, const char *src) {
    if (dst_size == 0)
        return _error("str_copy: invalid arg 'dst_size' = 0");

#if defined(PSUTIL_WINDOWS)
    if (strcpy_s(dst, dst_size, src) != 0)
        return _error("str_copy: strcpy_s failed");
#else
    strncpy(dst, src, dst_size - 1);
    dst[dst_size - 1] = '\0';
#endif
    return 0;
}


// Safely append `src` to `dst`, always null-terminating. Returns 0 on
// success, -1 on truncation.
int
str_append(char *dst, size_t dst_size, const char *src) {
    size_t dst_len;

    if (!dst || !src || dst_size == 0)
        return _error("str_append: invalid arg");

#if defined(PSUTIL_WINDOWS)
    dst_len = strnlen_s(dst, dst_size);
    if (dst_len >= dst_size - 1)
        return _error("str_append: destination full or truncated");
    if (strcat_s(dst, dst_size, src) != 0)
        return _error("str_append: strcat_s failed");
#elif defined(PSUTIL_MACOS) || defined(PSUTIL_BSD)
    dst_len = strlcat(dst, src, dst_size);
    if (dst_len >= dst_size)
        return _error("str_append: truncated");
#else
    dst_len = strnlen(dst, dst_size);
    if (dst_len >= dst_size - 1)
        return _error("str_append: destination full or truncated");
    strncat(dst, src, dst_size - dst_len - 1);
    dst[dst_size - 1] = '\0';
#endif

    return 0;
}
