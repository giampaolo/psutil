/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Copyright (c) 2025, Mingye Wang. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Functions related to the Windows Management Instrumentation API (currently
 * just load average).
 */

#include <Python.h>
#include <windows.h>
#include <pdh.h>
#include <math.h>

#include "../../arch/all/init.h"


// We use an exponentially weighted moving average, just like Unix systems do
// https://en.wikipedia.org/wiki/Load_(computing)#Unix-style_load_calculation
// These constants serve as the damping factor and are calculated with
// 1 / exp(sampling interval / window size) = exp(-interval/window)
// For us this would be exp(-1/13), exp(-1/(13*5)), exp(-1/(13*15)).
//
// This formula comes from linux's include/linux/sched/loadavg.h
// https://github.com/torvalds/linux/blob/v4.20-rc1/include/linux/sched/loadavg.h#L20-L23
static const double alpha[4] = {
    /* 1, 5, 15, Instant */
    0.925961078642316,
    0.9847331232494916,
    0.9948849216671609,
    0.0
};

// The time interval in milliseconds between taking load counts
// Used to be 5000 ms, but revised to 60/13*1000 (~4615 ms) per:
// https://ripke.com/loadavg/moire/
// 60/13*1000 = 4615.384615384615, rounded to nearest integer
// (We can actually get away with a smaller interval since we use doubles.)
#define SAMPLING_INTERVAL 4615

static inline void
update4(double avg[4], const double current) {
    for (int i = 0; i < 4; i++) {
        avg[i] *= alpha[i];
        avg[i] += current * (1.0 - alpha[i]);
    }
}

static inline void
set4(double a[4], const double x) {
    for (int i = 0; i < 4; i++) {
        a[i] = x;
    }
}

static inline ULONGLONG
filetime_to_ull(const FILETIME *ft) {
    ULARGE_INTEGER u;
    u.LowPart = ft->dwLowDateTime;
    u.HighPart = ft->dwHighDateTime;
    return u.QuadPart;
}

const char UTIL_ERRORS[2][80] = {
    "GetSystemTimes failed (%lx), util not updated",
    "delta is 0, util not updated%*lx"
};

// Data guarded by mutex (hot shared state)
typedef struct {
    double pque_avg[4];
    double util_avg[4];
    double dque_avg[4];
    BYTE state;
    const char *errmsg;  // string literal or NULL
    DWORD errcode;
} LoadAvgShared;
static LoadAvgShared g = {0};

#ifdef Py_GIL_DISABLED
static PyMutex mutex;
    #define MUTEX_LOCK(m) PyMutex_Lock(m)
    #define MUTEX_UNLOCK(m) PyMutex_Unlock(m)
#else
    #define MUTEX_LOCK(m) (void)0
    #define MUTEX_UNLOCK(m) (void)0
#endif

#define WITH_MUTEX(m) \
    for (int _once = (MUTEX_LOCK(m), 1); _once; _once = (MUTEX_UNLOCK(m), 0))

/*
 * Having a struct to hold many things is neat.  We get many possibilities
 * for expansion:
 *
 * * Custom sampling intervals? Custom set of weight/time-factors? Put ALPHA_*
 *   here.
 * * Another queue counter, perhaps "\\PhysicalDisk\\_Total\\Avg. Disk Queue
 *   Length" to match Linux's unusual inclusion of disk load in load average?
 *   Add a nullable handle here. (Alternatively, BYTE to control whether we do
 *   IOCTL_DISK_PERFORMANCE, but that requires us to open a handle per disk.)
 *
 * Only one thread will be using this struct at any time: first the
 * initializer, which is protected by a threading.Lock(), then the timer
 * callback.
 */
typedef struct _LoadAvgContext {
    HQUERY hQuery;
    HCOUNTER hPqueCounter;
    HCOUNTER hDqueCounter;
    unsigned int nlcpus;
    ULONGLONG last_cputimes[3];  // user, sys, wall
    HANDLE hTimer;
    HANDLE hWait;
} LoadAvgContext;
static LoadAvgContext ctx;

static inline int
psutil_load_cpu_util(double *out) {
    ULONGLONG idle, kernel, user, sys, total;
    ULONGLONG duser, dsys, dtotal;
    FILETIME idle_time, kernel_time, user_time;

    if (!GetSystemTimes(&idle_time, &kernel_time, &user_time)) {
        return -1;
    }

    idle = filetime_to_ull(&idle_time);
    user = filetime_to_ull(&user_time);
    kernel = filetime_to_ull(&kernel_time);

    // Kernel time includes idle time.
    sys = (kernel - idle);
    total = user + kernel;

    duser = user - ctx.last_cputimes[0];
    dsys = sys - ctx.last_cputimes[1];
    dtotal = total - ctx.last_cputimes[2];

    ctx.last_cputimes[0] = user;
    ctx.last_cputimes[1] = sys;
    ctx.last_cputimes[2] = total;

    if (!dtotal) {
        return -2;
    }

    *out = 1.0 * ctx.nlcpus * (duser + dsys) / dtotal;
    return 0;
}

/* In the future we could use timedOut and our own timestamp tracking
 * to implement multi-tick */
VOID CALLBACK
LoadAvgCallback(PVOID dummy, BOOLEAN timedOut) {
    PDH_FMT_COUNTERVALUE displayValue;
    double currentPque, currentUtil, currentDque;
    PDH_STATUS err;

    // Refresh PDH query data on each tick since we're not using
    // PdhCollectQueryDataEx anymore.
    err = PdhCollectQueryData(ctx.hQuery);
    if (err != ERROR_SUCCESS) {
        WITH_MUTEX(&mutex) {
            g.errmsg = "PdhCollectQueryData failed (%lx), p,que not updated";
            g.errcode = err;
            currentPque = g.pque_avg[0];
            currentDque = g.dque_avg[0];
        }
    }
    else {
        // Processor queue corresponds to waiting-to-run threads.
        err = PdhGetFormattedCounterValue(
            ctx.hPqueCounter, PDH_FMT_DOUBLE, 0, &displayValue
        );
        if (err != ERROR_SUCCESS) {
            WITH_MUTEX(&mutex) {
                g.errmsg =
                    "PdhGetFormattedCounterValue failed (%lx), pque not "
                    "updated";
                g.errcode = err;
                currentPque = g.pque_avg[0];
            }
        }
        else {
            currentPque = displayValue.doubleValue;
        }

        if (g.state) {
            // Disk queue corresponds to waiting-to-use threads.
            err = PdhGetFormattedCounterValue(
                ctx.hDqueCounter, PDH_FMT_DOUBLE, 0, &displayValue
            );
            if (err != ERROR_SUCCESS) {
                WITH_MUTEX(&mutex) {
                    g.errmsg =
                        "PdhGetFormattedCounterValue failed (%lx), dque not "
                        "updated";
                    g.errcode = err;
                    currentDque = g.dque_avg[0];
                }
            }
            else {
                currentDque = displayValue.doubleValue;
            }
        }
    }

    // CPU util is an approximation of active threads.  It's actually better
    // than the real thing since it provides an average instead of a snapshot.
    err = psutil_load_cpu_util(&currentUtil);
    if (err != 0) {
        WITH_MUTEX(&mutex) {
            g.errmsg = UTIL_ERRORS[-err - 1];
            g.errcode = GetLastError();
            currentUtil = g.util_avg[0];
        }
    }

    WITH_MUTEX(&mutex) {
        if (g.state < 1) {
            // Prime the EWMA so it doesn't snail-start from zero.
            set4(g.pque_avg, currentPque);
            // First CPU util sample is somehow not too far off from reality,//
            // even though MS doesn't document the exact starting point. Might
            // as well use it to seed.
            set4(g.util_avg, currentUtil);
            // First dque set in initializer, nothing to do here.
            g.state = 1;
        }
        else if (g.state < 2) {
            update4(g.pque_avg, currentPque);
            update4(g.util_avg, currentUtil);
            // Disk queue length is often very bursty, so using an average to
            // re-seed helps.
            set4(g.dque_avg, currentDque);
            g.state = 2;
        }
        else {
            update4(g.pque_avg, currentPque);
            update4(g.util_avg, currentUtil);
            update4(g.dque_avg, currentDque);
        }
    }
}

PyObject *
psutil_init_loadavg_counter(PyObject *self, PyObject *args) {
    WCHAR *szPquePath = L"\\System\\Processor Queue Length";
    // This is an average of the last sampling interval, which makes it more
    // representative than Current Disk Queue Length.  Unfortunately it's
    // delta-based...
    WCHAR *szDquePath = L"\\PhysicalDisk(_Total)\\Avg. Disk Queue Length";
    WCHAR
    *szDqueNowPath = L"\\PhysicalDisk(_Total)\\Current Disk Queue Length";
    HCOUNTER hDqueNowCounter;
    PDH_STATUS s;
    PDH_FMT_COUNTERVALUE displayValue;
    LARGE_INTEGER dueTime;

    s = PdhOpenQueryW(NULL, 0, &ctx.hQuery);
    if (s != ERROR_SUCCESS) {
        PyErr_Format(PyExc_RuntimeError, "PdhOpenQueryW failed (%lx)", s);
        return NULL;
    }

    s = PdhAddEnglishCounterW(ctx.hQuery, szPquePath, 0, &ctx.hPqueCounter);
    if (s != ERROR_SUCCESS) {
        PyErr_Format(
            PyExc_RuntimeError, "PdhAddEnglishCounterW[pque] failed (%lx)", s
        );
        goto defer_query;
    }

    s = PdhAddEnglishCounterW(ctx.hQuery, szDquePath, 0, &ctx.hDqueCounter);
    if (s != ERROR_SUCCESS) {
        PyErr_Format(
            PyExc_RuntimeError, "PdhAddEnglishCounterW[dque] failed (%lx)", s
        );
        goto defer_query;
    }

    s = PdhAddEnglishCounterW(ctx.hQuery, szDqueNowPath, 0, &hDqueNowCounter);
    if (s != ERROR_SUCCESS) {
        PyErr_Format(
            PyExc_RuntimeError,
            "PdhAddEnglishCounterW[dque_now] failed (%lx)",
            s
        );
        goto defer_query;
    }

    // Initial collection to prime the counters.
    s = PdhCollectQueryData(ctx.hQuery);
    if (s != ERROR_SUCCESS) {
        PyErr_Format(
            PyExc_RuntimeError, "PdhCollectQueryData failed (%lx)", s
        );
        goto defer_query;
    }

    // Seed the disk queue length with the current value.
    s = PdhGetFormattedCounterValue(
        hDqueNowCounter, PDH_FMT_DOUBLE, 0, &displayValue
    );
    if (s != ERROR_SUCCESS) {
        PyErr_Format(
            PyExc_RuntimeError,
            "PdhGetFormattedCounterValue[dque_now] failed (%lx)",
            s
        );
        goto defer_query;
    }

    WITH_MUTEX(&mutex) {
        set4(g.dque_avg, displayValue.doubleValue);
    }

    // No use for ya anymore.
    s = PdhRemoveCounter(hDqueNowCounter);
    if (s != ERROR_SUCCESS) {
        PyErr_Format(
            PyExc_RuntimeError, "PdhRemoveCounter[dque_now] failed (%lx)", s
        );
        goto defer_query;
    }

    ctx.nlcpus = psutil_get_num_cpus(1);
    if (ctx.nlcpus == 0) {
        goto defer_query;
    }

    LoadAvgCallback(&ctx, FALSE);  // Initial call to prime data.

    // Create a periodic waitable timer to achieve a fractional-second
    // interval.
    ctx.hTimer = CreateWaitableTimerW(NULL, FALSE, L"LoadUpdateTimer");
    if (ctx.hTimer == NULL) {
        psutil_oserror_wsyscall("CreateWaitableTimerW");
        goto defer_query;
    }

    // 500 ms delay before it fires for real, so the util call has some data.
    dueTime.QuadPart = -500 * 10000;
    if (!SetWaitableTimer(
            ctx.hTimer, &dueTime, SAMPLING_INTERVAL, NULL, NULL, FALSE
        ))
    {
        psutil_oserror_wsyscall("SetWaitableTimer");
        goto defer_timer;
    }

    if (!RegisterWaitForSingleObject(
            &ctx.hWait,
            ctx.hTimer,
            (WAITORTIMERCALLBACK)LoadAvgCallback,
            NULL,
            INFINITE,
            WT_EXECUTEDEFAULT
        ))
    {
        psutil_oserror_wsyscall("RegisterWaitForSingleObject");
        goto defer_timer;
    }
    goto success;

defer_timer:
    CloseHandle(ctx.hTimer);
    ctx.hTimer = NULL;
defer_query:
    PdhCloseQuery(ctx.hQuery);
    ctx.hQuery = NULL;

success:
    Py_RETURN_NONE;
}

/*
 * Gets the emulated 1 minute, 5 minute and 15 minute load averages
 * (processor queue length) for the system.
 * `init_loadavg_counter` must be called before this function to engage the
 * mechanism that records load values.
 */
PyObject *
psutil_get_loadavg(PyObject *self, PyObject *args) {
    LoadAvgShared l;
    BYTE flag = 0;
    WITH_MUTEX(&mutex) {
        memcpy(&l, &g, sizeof(LoadAvgShared));
        g.errmsg = NULL;
        g.errcode = 0;
    }

    if (l.errmsg) {
        PyErr_WarnFormat(PyExc_RuntimeWarning, 1, l.errmsg, l.errcode);
    }

    if (l.state == 0) {
        PyErr_WarnEx(
            PyExc_RuntimeWarning,
            "Loadavg not initialized yet, this should not happen!",
            1
        );
    }

    // Binpack is suboptimal
    // clang-format off
    return Py_BuildValue(
        "(dddd)(dddd)(dddd)",
        l.pque_avg[0], l.pque_avg[1], l.pque_avg[2], l.pque_avg[3],
        l.util_avg[0], l.util_avg[1], l.util_avg[2], l.util_avg[3],
        l.dque_avg[0], l.dque_avg[1], l.dque_avg[2], l.dque_avg[3]
    );
    // clang-format on
}
