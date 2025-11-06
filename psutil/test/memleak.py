# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Test framework for detecting memory leaks in C functions."""

import functools
import gc
import os
import sys
import unittest

import psutil
from psutil._common import POSIX
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


class MemoryLeakTestCase(unittest.TestCase):
    """A testing framework for detecting memory leaks in functions,
    typically those implemented in C that forget to `free()` heap
    memory, call `Py_DECREF` on Python objects, and so on. It works by
    comparing the process's memory usage before and after repeatedly
    calling the target function.

    Detecting memory leaks reliably is inherently difficult (and
    probably impossible) because of how the OS manages memory, garbage
    collection, and caching. Memory usage may even decrease between
    runs. So this is not meant to be bullet proof. To reduce false
    positives, when an increase in memory is detected (mem > 0), the
    test is retried up to 5 times, increasing the number of function
    calls each time. If memory continues to grow, the test is
    considered a failure.

    The test currently monitors RSS, VMS, and USS [1] memory.
    `mallinfo()` on Linux and `_heapwalk()` on Windows could provide
    even more precise results [2], but these are not yet implemented.

    In addition it also ensures that the target function does not leak
    file descriptors (UNIX) or handles (Windows).

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

    @classmethod
    def setUpClass(cls):
        cls._psutil_debug_orig = bool(os.getenv("PSUTIL_DEBUG"))
        psutil._set_debug(False)  # avoid spamming to stderr

    @classmethod
    def tearDownClass(cls):
        psutil._set_debug(cls._psutil_debug_orig)

    def _log(self, msg, level):
        if level <= self.verbosity:
            print_color(msg, color="yellow", file=sys.stderr)

    # --- getters

    def _get_mem(self):
        mem = thisproc.memory_full_info()
        return {
            "rss": mem.rss,
            "vms": mem.vms,
            "uss": getattr(mem, "uss", 0),
        }

    def _get_num_fds(self):
        if POSIX:
            return thisproc.num_fds()
        else:
            return thisproc.num_handles()

    # --- checkers

    def _check_fds(self, fun):
        """Makes sure num_fds() (POSIX) or num_handles() (Windows) does
        not increase after calling a function.  Used to discover forgotten
        close(2) and CloseHandle syscalls.
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
            return self.fail(msg)
        if diff > 0:
            type_ = "fd" if POSIX else "handle"
            if diff > 1:
                type_ += "s"
            msg = f"{diff} unclosed {type_} after calling {fun!r}"
            return self.fail(msg)

    def _call_ntimes(self, fun, times):
        """Get memory samples (rss, vms, uss) before and after calling
        fun repeatedly, and return the diffs as a dict.
        """
        gc.collect(generation=1)
        mem1 = self._get_mem()
        for x in range(times):
            ret = self.call(fun)
            del x, ret
        gc.collect(generation=1)
        mem2 = self._get_mem()
        assert gc.garbage == []
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
            times += times  # double calls each retry

        msg = f"Memory kept increasing after {retries} runs." + "\n".join(
            messages
        )
        return self.fail(msg)

    # ---

    def call(self, fun):
        return fun()

    def execute(
        self,
        fun,
        *,
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

        self._call_ntimes(fun, warmup_times)  # warm up

        self._check_fds(fun)
        self._check_mem(fun, times=times, retries=retries, tolerance=tolerance)
