.. post:: 2016-11-06
   :tags: performance, new-api, featured, release
   :author: Giampaolo Rodola
   :category: featured
   :exclude:

   New :meth:`Process.oneshot`, caching shared syscalls and halving the cost of multi-field queries

Making psutil twice as fast
===========================

Starting from psutil 5.0.0 you can query multiple :class:`Process` fields
around twice as fast as before (see :gh:`799` and :meth:`Process.oneshot`). It
took 7 months, 108 commits, and a massive refactoring of psutil internals
(:pr:`937`), and I think it's one of the best improvements ever shipped in a
psutil release.

The problem
-----------

How process information is retrieved varies by OS. Sometimes it means reading a
file in /proc (Linux), other times calling C (Windows, BSD, macOS, SunOS), but
it's always done differently. Psutil abstracts this away: you call
:meth:`Process.name` without worrying about what happens under the hood or
which OS you're on.

Internally, multiple pieces of process info (e.g. :meth:`Process.name`,
:meth:`Process.ppid`, :meth:`Process.uids`, :meth:`Process.create_time`) are
fetched by the same syscall. On Linux we read ``/proc/PID/stat`` to get the
process name, terminal, CPU times, creation time, status and parent PID, but
only one value is returned: the others are discarded. On Linux this code reads
``/proc/PID/stat`` 6 times:

.. code-block:: pycon

    >>> import psutil
    >>> p = psutil.Process()
    >>> p.name()
    >>> p.cpu_times()
    >>> p.create_time()
    >>> p.ppid()
    >>> p.status()
    >>> p.terminal()

On BSD most process metrics can be fetched with a single ``sysctl()``, yet
psutil was invoking it for each process method (e.g. see
`here <https://github.com/giampaolo/psutil/blob/2fe3f456321ca1605aaa2b71a7193de59d93075c/psutil/_psutil_bsd.c#L242-L258>`__
and
`here <https://github.com/giampaolo/psutil/blob/2fe3f456321ca1605aaa2b71a7193de59d93075c/psutil/_psutil_bsd.c#L261-L277>`__).

Do it in one shot
-----------------

It's clear that this approach is inefficient, especially in tools like top or
htop, where process info is continuously fetched in a loop. psutil 5.0.0
introduces a new :meth:`Process.oneshot` context manager. Inside it, the
internal routine runs once (in the example, on the first :meth:`Process.name`
call) and the other values are cached. Subsequent calls sharing the same
internal routine (read ``/proc/PID/stat``, call ``sysctl()`` or whatever)
return the cached value. The code above can now be rewritten like this, and on
Linux it runs 2.4 times faster:

.. code-block:: pycon

    >>> import psutil
    >>> p = psutil.Process()
    >>> with p.oneshot():
    ...     p.name()
    ...     p.cpu_times()
    ...     p.create_time()
    ...     p.ppid()
    ...     p.status()
    ...     p.terminal()

Implementation
--------------

One great thing about psutil's design is its abstraction. It is divided into 3
"layers". Layer 1 is represented by the main
`Process class <https://github.com/giampaolo/psutil/blob/88ea5e0b2cc15c37fdeb3e38857f6dab6fd87d12/psutil/__init__.py#L340>`__
(Python), which exposes the high-level API. Layer 2 is the
`OS-specific Python module <https://github.com/giampaolo/psutil/blob/88ea5e0b2cc15c37fdeb3e38857f6dab6fd87d12/psutil/_pslinux.py#L1097>`__,
which is a thin wrapper on top of the OS-specific
`C extension module <https://github.com/giampaolo/psutil/blob/88ea5e0b2cc15c37fdeb3e38857f6dab6fd87d12/psutil/_psutil_linux.c>`__
(layer 3).

Because the code was organized this way (modular), the refactoring was
reasonably smooth. I first refactored those C functions that collect multiple
pieces of info and grouped them into a single function (e.g. see
`BSD implementation <https://github.com/giampaolo/psutil/blob/88ea5e0b2cc15c37fdeb3e38857f6dab6fd87d12/psutil/_psutil_bsd.c#L198-L338>`__).
Then I wrote a
`decorator <https://github.com/giampaolo/psutil/blob/88ea5e0b2cc15c37fdeb3e38857f6dab6fd87d12/psutil/_common.py#L264-L314>`__
that enables the cache only when requested (when entering the context manager),
and decorated the
`"grouped functions" <https://github.com/giampaolo/psutil/blob/88ea5e0b2cc15c37fdeb3e38857f6dab6fd87d12/psutil/_psbsd.py#L491>`__
with it. The caching mechanism is controlled by the :meth:`Process.oneshot`
context manager, which is the only thing exposed to the end user. Here's the
decorator:

.. code-block:: python

    def memoize_when_activated(fun):
        """A memoize decorator which is disabled by default. It can be
        activated and deactivated on request.
        """
        @functools.wraps(fun)
        def wrapper(self):
            if not wrapper.cache_activated:
                return fun(self)
            else:
                try:
                    ret = cache[fun]
                except KeyError:
                    ret = cache[fun] = fun(self)
                return ret

        def cache_activate():
            """Activate cache."""
            wrapper.cache_activated = True

        def cache_deactivate():
            """Deactivate and clear cache."""
            wrapper.cache_activated = False
            cache.clear()

        cache = {}
        wrapper.cache_activated = False
        wrapper.cache_activate = cache_activate
        wrapper.cache_deactivate = cache_deactivate
        return wrapper

To measure the speedup I wrote a
`benchmark script <https://github.com/giampaolo/psutil/blob/b5582380ac70ca8c180344d9b22aacdff73b1e0b/scripts/internal/bench_oneshot.py>`__
(well,
`two <https://github.com/giampaolo/psutil/blob/b5582380ac70ca8c180344d9b22aacdff73b1e0b/scripts/internal/bench_oneshot_2.py>`__
actually), and kept tuning until I was sure the change actually made psutil
faster. The scripts report the speedup for calling all the "grouped" methods
together (best-case scenario).

Linux: +2.56x speedup
---------------------

The Linux implementation is mostly Python, reading files in ``/proc``. These
files typically expose multiple pieces of info per process; ``/proc/PID/stat``
and ``/proc/PID/status`` are the perfect example. We aggregate them into three
groups. See the relevant code
`here <https://github.com/giampaolo/psutil/blob/b5582380ac70ca8c180344d9b22aacdff73b1e0b/psutil/_pslinux.py#L1108-L1153>`__.

Windows: from +1.9x to +6.5x speedup
------------------------------------

Windows is an interesting one. For a process owned by our user, we group only
:meth:`Process.num_threads`, :meth:`Process.num_ctx_switches` and
:meth:`Process.num_handles`, for a +1.9x speedup if we access those methods in
one shot.

Windows is special though, because certain methods have a dual implementation
(:gh:`304`): a "fast method" is tried first, but if the process is owned by
another user it fails with :exc:`AccessDenied`. psutil then falls back to a
second, "slower" method (see `here
<https://github.com/giampaolo/psutil/blob/0ccd1373c6e7a189e095df5c436568fb1e8b4d14/psutil/_pswindows.py#L681>`__
for example).

It's slower because it
`iterates over all PIDs <https://github.com/giampaolo/psutil/blob/0ccd1373c6e7a189e095df5c436568fb1e8b4d14/psutil/arch/windows/process_info.c#L790>`__,
but unlike the "plain" Windows APIs it can still
`retrieve multiple pieces of information in one shot <https://github.com/giampaolo/psutil/blob/0ccd1373c6e7a189e095df5c436568fb1e8b4d14/psutil/_psutil_windows.c#L2789>`__:
number of threads, :term:`context switches <context switch>`, handles, CPU
times, create time, and I/O counters.

That's why querying processes owned by other users results in an impressive
+6.5x speedup.

macOS: +1.92x speedup
---------------------

On macOS we can get 2 groups of information. With
`sysctl() <https://github.com/giampaolo/psutil/blob/0ccd1373c6e7a189e095df5c436568fb1e8b4d14/psutil/_psutil_osx.c#L129>`__
we get process parent PID, uids, gids, terminal, create time, name. With
`proc_info() <https://github.com/giampaolo/psutil/blob/0ccd1373c6e7a189e095df5c436568fb1e8b4d14/psutil/_psutil_osx.c#L183>`__
we get CPU times (for PIDs owned by another user), memory metrics and ctx
switches. Not bad.

BSD: +2.18x speedup
-------------------

On BSD we gather tons of process info just by calling ``sysctl()`` (see
`implementation <https://github.com/giampaolo/psutil/blob/0ccd1373c6e7a189e095df5c436568fb1e8b4d14/psutil/_psutil_bsd.c#L199>`__):
process name, ppid, status, uids, gids, IO counters, CPU and create times,
terminal and ctx switches.

SunOS: +1.37x speedup
---------------------

SunOS is like Linux (it reads files in ``/proc``), but the code is in C. Here
too, we group different metrics together (see
`here <https://github.com/giampaolo/psutil/blob/b5582380ac70ca8c180344d9b22aacdff73b1e0b/psutil/_psutil_sunos.c#L83-L142>`__
and
`here <https://github.com/giampaolo/psutil/blob/b5582380ac70ca8c180344d9b22aacdff73b1e0b/psutil/_psutil_sunos.c#L171-L189>`__).

Discussion
----------

* `Reddit <https://www.reddit.com/r/Python/comments/5bhn4q/psutil_500_is_around_twice_as_fast/>`__
