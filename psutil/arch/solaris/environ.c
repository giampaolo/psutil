/*
 * Copyright (c) 2009, Giampaolo Rodola', Oleksii Shevchuk.
 * All rights reserved. Use of this source code is governed by a BSD-style
 * license that can be found in the LICENSE file.
 *
 * Functions specific for Process.environ().
 */

#define NEW_MIB_COMPLIANT 1
#define _STRUCTURED_PROC 1

#include <Python.h>

#if !defined(_LP64) && _FILE_OFFSET_BITS == 64
#  undef _FILE_OFFSET_BITS
#  undef _LARGEFILE64_SOURCE
#endif

#include <sys/types.h>
#include <sys/procfs.h>
#include <sys/stat.h>
#include <fcntl.h>

#include "environ.h"


#define STRING_SEARCH_BUF_SIZE 512


/*
 * Open address space of specified process and return file descriptor.
 *  @param pid a pid of process.
 *  @param procfs_path a path to mounted procfs filesystem.
 *  @return file descriptor or -1 in case of error.
 */
static int
open_address_space(pid_t pid, const char *procfs_path) {
    int fd;
    char proc_path[PATH_MAX];

    snprintf(proc_path, PATH_MAX, "%s/%i/as", procfs_path, pid);
    fd = open(proc_path, O_RDONLY);
    if (fd < 0)
        PyErr_SetFromErrno(PyExc_OSError);

    return fd;
}


/*
 * Read chunk of data by offset to specified buffer of the same size.
 * @param fd a file descriptor.
 * @param offset an required offset in file.
 * @param buf a buffer where to store result.
 * @param buf_size a size of buffer where data will be stored.
 * @return amount of bytes stored to the buffer or -1 in case of
 *         error.
 */
static int
read_offt(int fd, off_t offset, char *buf, size_t buf_size) {
    size_t to_read = buf_size;
    size_t stored  = 0;
    int r;

    while (to_read) {
        r = pread(fd, buf + stored, to_read, offset + stored);
        if (r < 0)
            goto error;
        else if (r == 0)
            break;

        to_read -= r;
        stored += r;
    }

    return stored;

 error:
    PyErr_SetFromErrno(PyExc_OSError);
    return -1;
}


/*
 * Read null-terminated string from file descriptor starting from
 * specified offset.
 * @param fd a file descriptor of opened address space.
 * @param offset an offset in specified file descriptor.
 * @return allocated null-terminated string or NULL in case of error.
*/
static char *
read_cstring_offt(int fd, off_t offset) {
    int r;
    int i = 0;
    off_t end = offset;
    size_t len;
    char buf[STRING_SEARCH_BUF_SIZE];
    char *result = NULL;

    if (lseek(fd, offset, SEEK_SET) == (off_t)-1) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }

    // Search end of string
    for (;;) {
        r = read(fd, buf, sizeof(buf));
        if (r == -1) {
            PyErr_SetFromErrno(PyExc_OSError);
            goto error;
        }
        else if (r == 0) {
            break;
        }
        else {
            for (i=0; i<r; i++)
                if (! buf[i])
                    goto found;
        }

        end += r;
    }

found:
    len = end + i - offset;

    result = malloc(len+1);
    if (! result) {
        PyErr_NoMemory();
        goto error;
    }

    if (len) {
        if (read_offt(fd, offset, result, len) < 0) {
            goto error;
        }
    }

    result[len] = '\0';
    return result;

 error:
    if (result)
        free(result);
    return NULL;
}


/*
 * Read block of addresses by offset, dereference them one by one
 * and create an array of null terminated C strings from them.
 * @param fd a file descriptor of address space of interesting process.
 * @param offset an offset of address block in address space.
 * @param ptr_size a size of pointer. Only 4 or 8 are valid values.
 * @param count amount of pointers in block.
 * @return allocated array of strings dereferenced and read by offset.
 * Number of elements in array are count. In case of error function
 * returns NULL.
 */
static char **
read_cstrings_block(int fd, off_t offset, size_t ptr_size, size_t count) {
    char **result = NULL;
    char *pblock = NULL;
    size_t pblock_size;
    int i;

    assert(ptr_size == 4 || ptr_size == 8);

    if (!count)
        goto error;

    pblock_size = ptr_size * count;

    pblock = malloc(pblock_size);
    if (! pblock) {
        PyErr_NoMemory();
        goto error;
    }

    if (read_offt(fd, offset, pblock, pblock_size) != pblock_size)
        goto error;

    result = (char **) calloc(count, sizeof(char *));
    if (! result) {
        PyErr_NoMemory();
        goto error;
    }

    for (i=0; i<count; i++) {
        result[i] = read_cstring_offt(
            fd, (ptr_size == 4?
                ((uint32_t *) pblock)[i]:
                ((uint64_t *) pblock)[i]));

        if (!result[i])
            goto error;
    }

    free(pblock);
    return result;

 error:
    if (result)
        psutil_free_cstrings_array(result, i);
    if (pblock)
        free(pblock);
    return NULL;
}


/*
 * Check that caller process can extract proper values from psinfo_t
 * structure.
 * @param info a pointer to process info (psinfo_t) structure of the
 *             interesting process.
 *  @return 1 in case if caller process can extract proper values from
 *          psinfo_t structure, or 0 otherwise.
 */
static inline int
is_ptr_dereference_possible(psinfo_t info) {
#if !defined(_LP64)
    return info.pr_dmodel == PR_MODEL_ILP32;
#else
    return 1;
#endif
}


/*
 * Return pointer size according to psinfo_t structure
 * @param info a ponter to process info (psinfo_t) structure of the
 *             interesting process.
 * @return pointer size (4 or 8).
 */
static inline int
ptr_size_by_psinfo(psinfo_t info) {
    return info.pr_dmodel == PR_MODEL_ILP32? 4 : 8;
}


/*
 * Count amount of pointers in a block which ends with NULL.
 * @param fd a discriptor of /proc/PID/as special file.
 * @param offt an offset of block of pointers at the file.
 * @param ptr_size a pointer size (allowed values: {4, 8}).
 * @return amount of non-NULL pointers or -1 in case of error.
 */
static int
search_pointers_vector_size_offt(int fd, off_t offt, size_t ptr_size) {
    int count = 0;
    int r;
    char buf[8];
    static const char zeros[8] = { 0, 0, 0, 0, 0, 0, 0, 0 };

    assert(ptr_size == 4 || ptr_size == 8);

    if (lseek(fd, offt, SEEK_SET) == (off_t)-1)
        goto error;

    for (;; count ++) {
        r = read(fd, buf, ptr_size);

        if (r < 0)
            goto error;

        if (r == 0)
            break;

        if (r != ptr_size) {
            PyErr_SetString(
                PyExc_RuntimeError, "pointer block is truncated");
            return -1;
        }

        if (! memcmp(buf, zeros, ptr_size))
            break;
    }

    return count;

 error:
    PyErr_SetFromErrno(PyExc_OSError);
    return -1;
}


/*
 * Derefence and read array of strings by psinfo_t.pr_argv pointer from
 * remote process.
 * @param info a ponter to process info (psinfo_t) structure of the
 *             interesting process
 * @param procfs_path a cstring with path to mounted procfs filesystem.
 * @param count a pointer to variable where to store amount of elements in
 *        returned array. In case of error value of variable will not be
          changed.
 * @return allocated array of cstrings or NULL in case of error.
 */
char **
psutil_read_raw_args(psinfo_t info, const char *procfs_path, size_t *count) {
    int as;
    char **result;

    if (! is_ptr_dereference_possible(info)) {
        PyErr_SetString(
            PyExc_NotImplementedError,
            "can't get env of a 64 bit process from a 32 bit process");
        return NULL;
    }

    if (! (info.pr_argv && info.pr_argc)) {
        PyErr_SetString(
            PyExc_RuntimeError, "process doesn't have arguments block");

        return NULL;
    }

    as = open_address_space(info.pr_pid, procfs_path);
    if (as < 0)
        return NULL;

    result = read_cstrings_block(
        as, info.pr_argv, ptr_size_by_psinfo(info), info.pr_argc
    );

    if (result && count)
        *count = info.pr_argc;

    close(as);

    return result;
}


/*
 * Dereference and read array of strings by psinfo_t.pr_envp pointer
 * from remote process.
 * @param info a ponter to process info (psinfo_t) structure of the
 *             interesting process.
 * @param procfs_path a cstring with path to mounted procfs filesystem.
 * @param count a pointer to variable where to store amount of elements in
 *        returned array. In case of error value of variable will not be
 *        changed. To detect special case (described later) variable should be
 *        initialized by -1 or other negative value.
 * @return allocated array of cstrings or NULL in case of error.
 *         Special case: count set to 0, return NULL.
 *         Special case means there is no error acquired, but no data
 *         retrieved.
 *         Special case exists because the nature of the process. From the
 *         beginning it's not clean how many pointers in envp array. Also
 *         situation when environment is empty is common for kernel processes.
 */
char **
psutil_read_raw_env(psinfo_t info, const char *procfs_path, ssize_t *count) {
    int as;
    int env_count;
    int ptr_size;
    char **result = NULL;

    if (! is_ptr_dereference_possible(info)) {
        PyErr_SetString(
            PyExc_NotImplementedError,
            "can't get env of a 64 bit process from a 32 bit process");
        return NULL;
    }

    as = open_address_space(info.pr_pid, procfs_path);
    if (as < 0)
        return NULL;

    ptr_size = ptr_size_by_psinfo(info);

    env_count = search_pointers_vector_size_offt(
        as, info.pr_envp, ptr_size);

    if (env_count >= 0 && count)
        *count = env_count;

    if (env_count > 0)
        result = read_cstrings_block(
            as, info.pr_envp, ptr_size, env_count);

    close(as);
    return result;
}


/*
 * Free array of cstrings.
 * @param array an array of cstrings returned by psutil_read_raw_env,
 *              psutil_read_raw_args or any other function.
 * @param count a count of strings in the passed array
 */
void
psutil_free_cstrings_array(char **array, size_t count) {
    int i;

    if (!array)
        return;
    for (i=0; i<count; i++) {
        if (array[i]) {
            free(array[i]);
        }
    }
    free(array);
}
