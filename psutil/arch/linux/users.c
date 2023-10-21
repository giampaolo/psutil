/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <dlfcn.h>
#include <utmp.h>
#include <string.h>

#include "../../_psutil_common.h"

/* Systemd function signatures that will be loaded */
int (*sd_booted)(void);
int (*sd_get_sessions)(char ***);
int (*sd_session_get_leader)(const char *, pid_t *);
int (*sd_session_get_remote_host)(const char *,char **);
int (*sd_session_get_start_time)(const char *, uint64_t *);
int (*sd_session_get_tty)(const char *, char **);
int (*sd_session_get_username)(const char *, char **);

#define dlsym_check(__h, __fn) do {           \
    __fn = dlsym(__h, #__fn);                 \
    if (dlerror() != NULL || __fn == NULL) {  \
        dlclose(__h);                         \
        return NULL;                          \
    }                                         \
} while (0)

static void *
load_systemd() {
    void *handle = dlopen("libsystemd.so.0", RTLD_LAZY);
    if (dlerror() != NULL || handle == NULL)
        return NULL;

    dlsym_check(handle, sd_booted);
    dlsym_check(handle, sd_get_sessions);
    dlsym_check(handle, sd_session_get_leader);
    dlsym_check(handle, sd_session_get_remote_host);
    dlsym_check(handle, sd_session_get_start_time);
    dlsym_check(handle, sd_session_get_tty);
    dlsym_check(handle, sd_session_get_username);

    if (! sd_booted()) {
        dlclose(handle);
        return NULL;
    }
    return handle;
}

PyObject *
psutil_users_systemd(PyObject *self, PyObject *args) {
    char **sessions_list = NULL;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;
    PyObject *py_username = NULL;
    PyObject *py_tty = NULL;
    PyObject *py_hostname = NULL;
    PyObject *py_user_proc = NULL;
    double tstamp = 0.0;
    pid_t pid = 0;
    int sessions;
    const char *session_id = NULL;
    char *username = NULL;
    char *tty = NULL;
    char *hostname = NULL;
    uint64_t usec = 0;
    void *handle = load_systemd();

    if (! handle)
        return NULL;

    if (py_retlist == NULL)
        return NULL;
    sessions = sd_get_sessions(&sessions_list);
    for (int i = 0; i < sessions; i++) {
        session_id = sessions_list[i];
        py_tuple = NULL;
        py_user_proc = NULL;
        py_user_proc = Py_True;

        username = NULL;
        if (sd_session_get_username(session_id, &username) < 0)
            goto error;
        py_username = PyUnicode_DecodeFSDefault(username);
        free(username);
        if (! py_username)
            goto error;

        tty = NULL;
        if (sd_session_get_tty(session_id, &tty) < 0) {
            py_tty = PyUnicode_DecodeFSDefault("");
        } else {
            py_tty = PyUnicode_DecodeFSDefault(tty);
            free(tty);
        }
        if (! py_tty)
            goto error;

        hostname = NULL;
        if (sd_session_get_remote_host(session_id, &hostname) < 0)
            goto error;
        py_hostname = PyUnicode_DecodeFSDefault(hostname);
        free(hostname);
        if (! py_hostname)
            goto error;

        usec = 0;
        if (sd_session_get_start_time(session_id, &usec) < 0)
           goto error;
        tstamp = (double)usec / 1000000.0;

        if (sd_session_get_leader(session_id, &pid) < 0)
           goto error;

        py_tuple = Py_BuildValue(
            "OOOdO" _Py_PARSE_PID,
            py_username,              // username
            py_tty,                   // tty
            py_hostname,              // hostname
            tstamp,                   // tstamp
            py_user_proc,             // (bool) user process
            pid                       // process id
        );
        if (! py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_CLEAR(py_username);
        Py_CLEAR(py_tty);
        Py_CLEAR(py_hostname);
        Py_CLEAR(py_tuple);
        free(sessions_list[i]);
    }
    free(sessions_list);
    dlclose(handle);
    return py_retlist;

error:
    Py_XDECREF(py_username);
    Py_XDECREF(py_tty);
    Py_XDECREF(py_hostname);
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    if (sessions_list)
        free(sessions_list);
    dlclose(handle);
    return NULL;
}

PyObject *
psutil_users_utmp(PyObject *self, PyObject *args) {
    struct utmp *ut;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;
    PyObject *py_username = NULL;
    PyObject *py_tty = NULL;
    PyObject *py_hostname = NULL;

    if (py_retlist == NULL)
        return NULL;
    setutent();
    while (NULL != (ut = getutent())) {
        if (ut->ut_type != USER_PROCESS)
            continue;
        py_tuple = NULL;
        py_username = PyUnicode_DecodeFSDefault(ut->ut_user);
        if (! py_username)
            goto error;
        py_tty = PyUnicode_DecodeFSDefault(ut->ut_line);
        if (! py_tty)
            goto error;
        if (strcmp(ut->ut_host, ":0") || strcmp(ut->ut_host, ":0.0"))
            py_hostname = PyUnicode_DecodeFSDefault("localhost");
        else
            py_hostname = PyUnicode_DecodeFSDefault(ut->ut_host);
        if (! py_hostname)
            goto error;

        py_tuple = Py_BuildValue(
            "OOOd" _Py_PARSE_PID,
            py_username,              // username
            py_tty,                   // tty
            py_hostname,              // hostname
            (double)ut->ut_tv.tv_sec,  // tstamp
            ut->ut_pid                // process id
        );
        if (! py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_CLEAR(py_username);
        Py_CLEAR(py_tty);
        Py_CLEAR(py_hostname);
        Py_CLEAR(py_tuple);
    }
    endutent();
    return py_retlist;

error:
    Py_XDECREF(py_username);
    Py_XDECREF(py_tty);
    Py_XDECREF(py_hostname);
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    endutent();
    return NULL;
}
