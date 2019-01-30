/*
 * Copyright (c) 2009, Giampaolo Rodola', Oleksii Shevchuk.
 * All rights reserved. Use of this source code is governed by a BSD-style
 * license that can be found in the LICENSE file.
 */

#ifndef PROCESS_AS_UTILS_H
#define PROCESS_AS_UTILS_H

char **
psutil_read_raw_args(psinfo_t info, const char *procfs_path, size_t *count);

char **
psutil_read_raw_env(psinfo_t info, const char *procfs_path, ssize_t *count);

void
psutil_free_cstrings_array(char **array, size_t count);

#endif // PROCESS_AS_UTILS_H
