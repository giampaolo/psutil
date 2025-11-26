# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A testing framework for detecting memory leaks in functions,
typically those implemented in C that forget to `free()` heap memory,
call `Py_DECREF` on Python objects, and so on. It works by comparing
the process's memory usage before and after repeatedly calling the
target function.

Detecting memory leaks reliably is inherently difficult (and probably
impossible) because of how the OS manages memory, garbage collection,
and caching. Memory usage may even decrease between runs. So this is
not meant to be bullet proof. To reduce false positives, when an
increase in memory is detected (mem > 0), the test is retried up to 5
times, increasing the number of function calls each time. If memory
continues to grow, the test is considered a failure.

The test monitors RSS, VMS, and USS [1] memory. In addition, it also
monitors **heap metrics** (`heap_used`, `mmap_used` from
`psutil.heap_info()`).

In other words, this is specifically designed to catch cases where a C
extension or other native code allocates memory via `malloc()` or
similar functions but fails to call `free()`, resulting in unreleased
memory that would otherwise remain in the process heap or in mapped
memory regions.

The types of allocations this should catch include:

- `malloc()` without a corresponding `free()`
- `mmap()` without `munmap()`
- `HeapAlloc()` without `HeapFree()` (Windows)
- `VirtualAlloc()` without `VirtualFree()` (Windows)
- `HeapCreate()` without `HeapDestroy()` (Windows)

In addition it also ensures that the target function does not leak file
descriptors (UNIX) or handles (Windows) such as:

- `open()` without a corresponding `close()` (UNIX)
- `CreateFile()` / `CreateProcess()` / ... without `CloseHandle()`
  (Windows)

Usage example:

    from psutil.test import MemoryLeakTestCase

    class TestLeaks(MemoryLeakTestCase):
        def test_fun(self):
            self.execute(some_function)

NOTE - This class is experimental, meaning its API or internal
algorithm may change in the future.

[1] https://gmpy.dev/blog/2016/real-process-memory-and-environ-in-python
[2] https://github.com/giampaolo/psutil/issues/1275
"""

import functools
import gc
import logging
import os
import sys
import unittest

import psutil
from psutil._common import POSIX
from psutil._common import WINDOWS
from psutil._common import bytes2human
from psutil._common import print_color

thisproc = psutil.Process()
b2h = functools.partial(bytes2human, format="%(value)i%(symbol)s")


def format_run_line(idx, diffs, times):
    parts = [f"{k}={'+' + b2h(v):<6}" for k, v in diffs.items() if v > 0]
    metrics = " | ".join(parts)
    avg = "0B"
    if parts:
        first_key = next(k for k, v in diffs.items() if v > 0)
        avg = b2h(diffs[first_key] // times)
    s = f"Run #{idx:>2}: {metrics:<50} (calls={times:>5}, avg/call=+{avg})"
    if idx == 1:
        s = "\n" + s
    return s


def qualname(obj):
    """Return a human-readable qualified name for a function, method or
    class.
    """
    return getattr(obj, "__qualname__", getattr(obj, "__name__", str(obj)))


class MemoryLeakError(AssertionError):
    """Raised when a memory leak is detected."""


class UnclosedFdError(AssertionError):
    """Raised when an unclosed file descriptor (UNIX) or handle
    (Windows) is detected.
    """


class UnclosedHeapCreateError(AssertionError):
    """Raised on Windows when test detects HeapCreate() without a
    corresponding HeapDestroy().
    """


class MemoryLeakTestCase(unittest.TestCase):
    # Number of times to call the tested function in each iteration.
    times = 200
    # Maximum number of retries if memory growth is detected.
    retries = 5
    # Number of warm-up calls before measurements begin.
    warmup_times = 10
    # Allowed memory difference (in bytes) before considering it a leak.
    tolerance = 0
    # 0 = no messages; 1 = print diagnostics when memory increases.
    verbosity = 1

    __doc__ = __doc__

    @classmethod
    def setUpClass(cls):
        cls._psutil_debug_orig = bool(os.getenv("PSUTIL_DEBUG"))
        psutil._set_debug(False)  # avoid spamming to stderr

    @classmethod
    def tearDownClass(cls):
        psutil._set_debug(cls._psutil_debug_orig)

    def _log(self, msg, level):
        if level <= self.verbosity:
            if WINDOWS:
                # On Windows we use ctypes to add colors. Avoid that to
                # not interfere with memory observations.
                print(msg)  # noqa: T201
            else:
                print_color(msg, color="yellow")
            # Force flush to not interfere with memory observations.
            sys.stdout.flush()

    def _trim_mem(self):
        """Release unused memory. Aims to stabilize memory measurements."""
        # flush standard streams
        sys.stdout.flush()
        sys.stderr.flush()

        # flush logging handlers
        for handler in logging.root.handlers:
            handler.flush()

        # full garbage collection
        gc.collect()
        assert gc.garbage == []

        # release free heap memory back to the OS
        if hasattr(psutil, "heap_trim"):
            psutil.heap_trim()

    def _warmup(self, fun, warmup_times):
        for _ in range(warmup_times):
            self.call(fun)

    # --- getters

    def _get_mem(self):
        mem = thisproc.memory_full_info()
        heap_used = mmap_used = 0
        if hasattr(psutil, "heap_info"):
            heap = psutil.heap_info()
            heap_used = heap.heap_used
            mmap_used = heap.mmap_used
        return {
            "heap": heap_used,
            "mmap": mmap_used,
            "uss": getattr(mem, "uss", 0),
            "rss": mem.rss,
            "vms": mem.vms,
        }

    def _get_num_fds(self):
        if POSIX:
            return thisproc.num_fds()
        else:
            return thisproc.num_handles()

    # --- checkers

    def _check_fds(self, fun):
        """Makes sure `num_fds()` (POSIX) or `num_handles()` (Windows)
        do not increase after calling function 1 time.  Used to
        discover forgotten `close(2)` and `CloseHandle()`.
        """

        before = self._get_num_fds()
        self.call(fun)
        after = self._get_num_fds()
        diff = after - before

        if diff < 0:
            msg = (
                f"negative diff {diff!r} (gc probably collected a"
                " resource from a previous test)"
            )
            raise UnclosedFdError(msg)

        if diff > 0:
            type_ = "fd" if POSIX else "handle"
            if diff > 1:
                type_ += "s"
            msg = (
                f"detected {diff} unclosed {type_} after calling"
                f" {qualname(fun)!r} 1 time"
            )
            raise UnclosedFdError(msg)

    def _check_heap_count(self, fun):
        """Windows only. Calls function once, and detects HeapCreate()
        without a corresponding HeapDestroy().
        """
        if not WINDOWS:
            return

        before = psutil.heap_info().heap_count
        self.call(fun)
        after = psutil.heap_info().heap_count
        diff = after - before

        if diff < 0:
            msg = f"negative diff {diff!r}"
            raise UnclosedHeapCreateError(msg)

        if diff > 0:
            msg = (
                f"detected {diff} HeapCreate() without a corresponding "
                f" HeapDestroy() after calling {qualname(fun)!r} 1 time"
            )
            raise UnclosedHeapCreateError(msg)

    def _call_ntimes(self, fun, times):
        """Get memory samples before and after calling fun repeatedly,
        and return the diffs as a dict.
        """
        self._trim_mem()
        mem1 = self._get_mem()

        for _ in range(times):
            self.call(fun)

        self._trim_mem()
        mem2 = self._get_mem()

        diffs = {k: mem2[k] - mem1[k] for k in mem1}
        return diffs

    def _check_mem(self, fun, times, retries, tolerance):
        prev = {}
        messages = []

        for idx in range(1, retries + 1):
            diffs = self._call_ntimes(fun, times)
            leaks = {k: v for k, v in diffs.items() if v > 0}

            if leaks:
                line = format_run_line(idx, leaks, times)
                messages.append(line)
                self._log(line, 1)

            stable = all(
                diffs.get(k, 0) <= tolerance
                or diffs.get(k, 0) <= prev.get(k, 0)
                for k in diffs
            )
            if stable:
                if idx > 1 and leaks:
                    self._log(
                        "Memory stabilized (no further growth detected)", 1
                    )
                return

            prev = diffs
            times *= 2  # double calls each retry

        msg = f"memory kept increasing after {retries} runs" + "\n".join(
            messages
        )
        raise MemoryLeakError(msg)

    # ---

    def call(self, fun):
        return fun()

    def execute(
        self,
        fun,
        *args,
        times=None,
        warmup_times=None,
        retries=None,
        tolerance=None,
    ):
        """Run a full leak test on a callable. If specified, the
        optional arguments override the class attributes with the same
        name.
        """
        times = times if times is not None else self.times
        warmup_times = (
            warmup_times if warmup_times is not None else self.warmup_times
        )
        retries = retries if retries is not None else self.retries
        tolerance = tolerance if tolerance is not None else self.tolerance

        if times < 1:
            msg = f"times must be >= 1 (got {times})"
            raise ValueError(msg)
        if warmup_times < 0:
            msg = f"warmup_times must be >= 0 (got {warmup_times})"
            raise ValueError(msg)
        if retries < 0:
            msg = f"retries must be >= 0 (got {retries})"
            raise ValueError(msg)
        if tolerance < 0:
            msg = f"tolerance must be >= 0 (got {tolerance})"
            raise ValueError(msg)

        if args:
            fun = functools.partial(fun, *args)

        self._warmup(fun, warmup_times)
        self._check_fds(fun)
        if WINDOWS:
            self._check_heap_count(fun)
        self._check_mem(fun, times=times, retries=retries, tolerance=tolerance)
