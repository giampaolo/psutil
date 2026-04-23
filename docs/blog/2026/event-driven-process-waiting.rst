.. post:: 2026-01-28
   :tags: python-core, performance, featured
   :author: Giampaolo Rodola
   :exclude:

   Replacing :meth:`subprocess.Popen.wait`'s busy-loop with an event-driven model, in psutil then upstream CPython

From Python 3.3 to today: ending 15 years of subprocess polling
===============================================================

One of the less fun aspects of process management on POSIX systems is waiting
for a process to terminate. The standard library's :mod:`subprocess` module has
relied on a busy-loop polling approach since the *timeout* parameter was added
to :meth:`subprocess.Popen.wait` in Python 3.3, around 15 years ago (see
`source <https://github.com/python/cpython/blob/8def603d853c7f5e4ff57f95de289f99e1943669/Lib/subprocess.py#L2056-L2077>`__).
And psutil's :meth:`Process.wait` method uses exactly the same technique (see
`source <https://github.com/giampaolo/psutil/blob/700b7e6a/psutil/_psposix.py#L95-L160>`__).

The logic is straightforward: check whether the process has exited using
non-blocking ``waitpid(WNOHANG)``, sleep briefly, check again, sleep a bit
longer, and so on.

.. code-block:: python

   import os, time

   def wait_busy(pid, timeout):
       end = time.monotonic() + timeout
       interval = 0.0001
       while time.monotonic() < end:
           pid_done, _ = os.waitpid(pid, os.WNOHANG)
           if pid_done:
               return
           time.sleep(interval)
           interval = min(interval * 2, 0.04)
       raise TimeoutExpired

In this blog post I'll show how I finally addressed this long-standing
inefficiency, first in psutil, and most excitingly, directly in CPython's
standard library :mod:`subprocess` module.

The problem with busy-polling
-----------------------------

- CPU wake-ups: even with exponential backoff (starting at 0.1ms, capping at
  40ms), the system constantly wakes up to check process status, wasting CPU
  cycles and draining batteries.
- Latency: there's always a gap between when a process actually terminates and
  when you detect it.
- Scalability: monitoring many processes simultaneously magnifies all of the
  above.

Event-driven waiting
--------------------

All POSIX systems provide at least one mechanism to be notified when a file
descriptor becomes ready. These are
`select() <https://man7.org/linux/man-pages/man2/select.2.html>`__,
`poll() <https://man7.org/linux/man-pages/man2/poll.2.html>`__,
`epoll() <https://man7.org/linux/man-pages/man7/epoll.7.html>`__ (Linux) and
`kqueue() <https://man.freebsd.org/cgi/man.cgi?query=kqueue>`__ (BSD / macOS)
system calls. Until recently, I believed they could only be used with file
descriptors referencing sockets, pipes, etc., but it turns out they can also be
used to wait for events on process PIDs!

Linux
-----

In 2019, Linux 5.3 introduced a new syscall, :func:`os.pidfd_open`, which was
added in Python 3.9. It returns a :term:`file descriptor` referencing a process
PID. The interesting thing is that ``pidfd_open()`` can be used in conjunction
with ``select()``, ``poll()`` or ``epoll()`` to effectively wait until the
process exits. E.g. by using ``poll()``:

.. code-block:: python

   import os, select

   def wait_pidfd(pid, timeout):
       pidfd = os.pidfd_open(pid)
       poller = select.poll()
       poller.register(pidfd, select.POLLIN)
       # block until process exits or timeout occurs
       events = poller.poll(timeout * 1000)
       if events:
           return
       raise TimeoutError

This approach has zero busy-looping. The kernel wakes us up exactly when the
process terminates or when the timeout expires if the PID is still alive.

I chose ``poll()`` over ``select()`` because ``select()`` has a historical file
descriptor limit (``FD_SETSIZE``), which typically caps it at 1024
:term:`file descriptors <file descriptor>` per-process (reminded me of
`BPO-1685000 <https://bugs.python.org/issue1685000>`__).

I chose ``poll()`` over ``epoll()`` because it does not require creating an
additional :term:`file descriptor`. It also needs only a single syscall, which
should make it a bit more efficient when monitoring a single FD rather than
many.

macOS and BSD
-------------

BSD-derived systems (including macOS) provide the ``kqueue()`` syscall. It's
conceptually similar to ``select()``, ``poll()`` and ``epoll()``, but more
powerful (e.g. it can also handle regular files). ``kqueue()`` can be passed a
PID directly, and it will return once the PID disappears or the timeout
expires:

.. code-block:: python

   import select

   def wait_kqueue(pid, timeout):
       kq = select.kqueue()
       kev = select.kevent(
           pid,
           filter=select.KQ_FILTER_PROC,
           flags=select.KQ_EV_ADD | select.KQ_EV_ONESHOT,
           fflags=select.KQ_NOTE_EXIT,
       )
       # block until process exits or timeout occurs
       events = kq.control([kev], 1, timeout)
       if events:
           return
       raise TimeoutError

Windows
-------

Windows does not busy-loop, both in psutil and :mod:`subprocess` module, thanks
to ``WaitForSingleObject``. This means Windows has effectively had event-driven
process waiting from the start. So nothing to do on that front.

Graceful fallbacks
------------------

Both ``pidfd_open()`` and ``kqueue()`` can fail for different reasons. For
example, with ``EMFILE`` if the process runs out of
:term:`file descriptors <file descriptor>` (usually 1024), or with ``EACCES`` /
``EPERM`` if the syscall was explicitly blocked at the system level by the
sysadmin (e.g. via SECCOMP). In all cases, psutil silently falls back to the
traditional busy-loop polling approach rather than raising an exception.

This fast-path-with-fallback approach is similar in spirit to
`BPO-33671 <https://bugs.python.org/issue33671>`__, where I sped up
:func:`shutil.copyfile` by using zero-copy system calls back in 2018. In there,
more efficient :func:`os.sendfile` is attempted first, and if it fails (e.g. on
network filesystems) we fall back to the traditional ``read()`` / ``write()``
approach to copy regular files.

Measurement
-----------

As a simple experiment, here's a simple program which waits on itself for 10
seconds without terminating:

.. code-block:: python

   # test.py
   import psutil, os
   try:
       psutil.Process(os.getpid()).wait(timeout=10)
   except psutil.TimeoutExpired:
       pass

We can measure the CPU context switching using ``/usr/bin/time -v``. Before the
patch (the busy-loop):

::

   $ /usr/bin/time -v python3 test.py 2>&1 | grep context
       Voluntary context switches: 258
       Involuntary context switches: 4

After the patch (the event-driven approach):

::

   $ /usr/bin/time -v python3 test.py 2>&1 | grep context
       Voluntary context switches: 2
       Involuntary context switches: 1

This shows that instead of spinning in userspace, the process blocks in
``poll()`` / ``kqueue()``, and is woken up only when the kernel notifies it,
resulting in just a few CPU :term:`context switches <context switch>`.

Sleeping state
--------------

It's also interesting to note that waiting via ``poll()`` (or ``kqueue()``)
puts the process into the exact same sleeping state as a plain
:func:`time.sleep` call. From the kernel's perspective, both are interruptible
sleeps: the process is de-scheduled, consumes zero CPU, and sits quietly in
kernel space.

The ``"S+"`` state shown below by ``ps`` means that the process “sleeps in
foreground”.

-  :func:`time.sleep`:

::

   $ (python3 -c 'import time; time.sleep(10)' & pid=$!; sleep 0.3; ps -o pid,stat,comm -p $pid) && fg &>/dev/null
       PID STAT COMMAND
    491573 S+   python3

-  :func:`select.poll`:

::

   $ (python3 -c 'import os,select; fd = os.pidfd_open(os.getpid(),0); p = select.poll(); p.register(fd,select.POLLIN); p.poll(10_000)' & pid=$!; sleep 0.3; ps -o pid,stat,comm -p $pid) && fg &>/dev/null
       PID STAT COMMAND
    491748 S+   python3

CPython contribution
--------------------

After landing the psutil implementation (:pr:`2706`), I took the extra step and
submitted a matching pull request for CPython :mod:`subprocess` module:
`cpython/PR-144047 <https://github.com/python/cpython/pull/144047>`__.

I'm especially proud of this one: this is the **third time** in psutil's 17+
year history that a feature developed in psutil made its way upstream into the
Python standard library.

-  The first was back in 2010, when :meth:`Process.nice` inspired
   :func:`os.getpriority` and :func:`os.setpriority`, see
   `BPO-10784 <https://bugs.python.org/issue10784>`__. Landed in Python 3.3.

-  The second was back in 2011, when :func:`psutil.disk_usage` inspired
   :func:`shutil.disk_usage`, see `python-ideas ML
   proposal <https://mail.python.org/archives/list/python-ideas@python.org/thread/67A7ML2TJ7MBS3WOL6IZKLD2C3B3VCQG>`__.
   Landed in Python 3.3.

*Funny thing:* 15 years ago, Python 3.3 added the *timeout* parameter to
:meth:`subprocess.Popen.wait` (see
`commit <https://github.com/python/cpython/commit/31aa7dd1419>`__). That's
probably where I took inspiration when I first added the *timeout* parameter to
psutil's :meth:`Process.wait` around the same time (see
`commit <https://github.com/giampaolo/psutil/commit/886710daf>`__). Now, 15
years later, I'm contributing back a similar improvement for that very same
*timeout* parameter. **The circle is complete**.

Links
-----

Topics related to this:

-  :gh:`2712`: proposal to extend this to multiple PIDs
   (:func:`psutil.wait_procs`).
-  :gh:`2703`: proposal for asynchronous :meth:`Process.wait` integration with
   :mod:`asyncio`.
-  `cpython/#144211 <https://github.com/python/cpython/issues/144211>`__:
   proposal to extend the :mod:`selectors` module to enable :mod:`asyncio`
   optimization on BSD / macOS via ``kqueue()``.

Discussion
----------

-  `Reddit <https://www.reddit.com/r/Python/comments/1qpp42k/from_python_33_to_today_ending_15_years_of/>`__
-  `Hacker News <https://news.ycombinator.com/item?id=46802061>`__
-  `Medium <https://medium.com/@g.rodola/from-python-3-3-to-today-ending-15-years-of-subprocess-polling-e8a83ba17c86>`__
-  `Linkedin <https://www.linkedin.com/feed/update/urn:li:share:7422396026449391616/>`__
