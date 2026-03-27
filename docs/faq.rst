.. currentmodule:: psutil

FAQ
===

This section answers common questions and pitfalls when using psutil.

.. contents::
   :local:
   :depth: 3

General
-------

.. _faq_named_tuple_unpacking:

Why should I avoid positional unpacking of named tuples?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Most psutil functions return named tuples. It is tempting to unpack them
positionally, but **field order may change across major releases** (as
happened in 8.0 with :func:`cpu_times` and :meth:`Process.memory_info`).
Always use attribute access instead:

.. code-block:: python

  # bad
  rss, vms = p.memory_info()

  # good
  m = p.memory_info()
  print(m.rss, m.vms)

See the :ref:`migration guide <migration-8.0>` for the full list of
field-order changes in 8.0.

-------------------------------------------------------------------------------

Exceptions
----------

.. _faq_access_denied:

Why do I get AccessDenied?
^^^^^^^^^^^^^^^^^^^^^^^^^^

:exc:`AccessDenied` is raised when the OS refuses to return information about
a process because the calling user does not have sufficient privileges.
This is expected behavior and is not a bug. It typically happens when:

- querying processes owned by other users (e.g. *root*)
- calling certain methods like :meth:`Process.memory_maps`,
  :meth:`Process.open_files` or :meth:`Process.net_connections` for privileged
  processes

You have two options to deal with it.

- Option 1: call the method directly and catch the exception:

  .. code-block:: python

    import psutil

    p = psutil.Process(pid)
    try:
        print(p.memory_maps())
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        pass

- Option 2: use :func:`process_iter` with a list of attribute names to
  pre-fetch. Both :exc:`AccessDenied` and :exc:`NoSuchProcess` are handled
  internally: the corresponding method returns ``None`` (or ``ad_value``)
  instead of raising. This also avoids the race condition where a process
  disappears between iteration and method call:

  .. code-block:: python

    import psutil

    for p in psutil.process_iter(["name", "username"], ad_value="N/A"):
        print(p.name(), p.username())  # no try/except needed

.. _faq_no_such_process:

Why do I get NoSuchProcess?
^^^^^^^^^^^^^^^^^^^^^^^^^^^

:exc:`NoSuchProcess` is raised when a process no longer exists.
The most common cause is a TOCTOU (time-of-check / time-of-use) race
condition: a process can die between the moment its PID is obtained and
the moment it is queried. The following two naive patterns are racy:

.. code-block:: python

  import psutil

  for pid in psutil.pids():
      p = psutil.Process(pid)  # may raise NoSuchProcess
      print(p.name())  # may raise NoSuchProcess

.. code-block:: python

  import psutil

  if psutil.pid_exists(pid):
      p = psutil.Process(pid)  # may raise NoSuchProcess
      print(p.name())  # may raise NoSuchProcess

The correct approach is to use :func:`process_iter`, which handles
:exc:`NoSuchProcess` internally and skips processes that disappear
during iteration:

.. code-block:: python

  import psutil

  for p in psutil.process_iter(["name"]):
      print(p.name())

If you have a specific PID (e.g. a known child process), wrap the
call in a try/except:

.. code-block:: python

  import psutil

  try:
      p = psutil.Process(pid)
      print(p.name(), p.status())
  except (psutil.NoSuchProcess, psutil.AccessDenied):
      pass

An even simpler pattern is to catch :exc:`Error`, which implies both
:exc:`AccessDenied` and :exc:`NoSuchProcess`:

.. code-block:: python

  import psutil

  try:
      p = psutil.Process(pid)
      print(p.name(), p.status())
  except psutil.Error:
      pass

.. _faq_zombie_process:

What is ZombieProcess?
^^^^^^^^^^^^^^^^^^^^^^^

:exc:`ZombieProcess` is a subclass of :exc:`NoSuchProcess` raised on UNIX
for a :term:`zombie process`.

**What you can and cannot do with a zombie:**

- A zombie process can be instantiated via :class:`Process` (pid) without error.
- :meth:`Process.status` always returns :data:`STATUS_ZOMBIE`.
- :meth:`Process.is_running` and :func:`pid_exists` return ``True``.
- The zombie appears in :func:`process_iter` and :func:`pids`.
- Sending signals (:meth:`Process.terminate`, :meth:`Process.kill`,
  etc.) has no effect.
- Most other methods (:meth:`Process.cmdline`, :meth:`Process.exe`,
  :meth:`Process.memory_maps`, etc.) may raise :exc:`ZombieProcess`,
  return a meaningful value, or return a null/empty value depending on
  the platform.
- :meth:`Process.as_dict` will not crash.

**How to create a zombie:**

.. code-block:: python

  import os, time

  pid = os.fork()  # the zombie
  if pid == 0:
      os._exit(0)  # child exits immediately
  else:
      time.sleep(1000)  # parent does NOT call wait()

**How to detect zombies:**

.. code-block:: python

  import psutil

  for p in psutil.process_iter(["status"]):
      if p.status() == psutil.STATUS_ZOMBIE:
          print(f"zombie: pid={p.pid}")

**How to get rid of a zombie:** the only way is to have its parent
process call ``wait()`` (or ``waitpid()``). If the parent never does
this, killing the parent will cause the zombie to be re-parented to
``init`` / ``systemd``, which will reap it automatically.

-------------------------------------------------------------------------------

Processes
---------

.. _faq_pid_reuse:

PID reuse
^^^^^^^^^

Operating systems recycle PIDs. A :class:`Process` object obtained now may
later refer to a different process if the original one terminated and a new one
was assigned the same PID.

**How psutil handles this:**

- *Most read-only methods* (e.g. :meth:`Process.name`,
  :meth:`Process.cpu_percent`) do **not** check for PID reuse and instead
  query whatever process currently holds that PID.

- *Signal methods* (e.g. :meth:`Process.send_signal`,
  :meth:`Process.suspend`, :meth:`Process.resume`,
  :meth:`Process.terminate`, :meth:`Process.kill`) **do** check for PID
  reuse (via PID + creation time) before acting, raising
  :exc:`NoSuchProcess` if the PID was recycled. This prevents accidentally
  killing the wrong process (`BPO-6973`_).

- *Set methods* :meth:`Process.nice` (set), :meth:`Process.ionice` (set),
  :meth:`Process.cpu_affinity` (set), and
  :meth:`Process.rlimit` (set) also perform this check before applying
  changes.

:meth:`Process.is_running` is the recommended way to verify whether a
:class:`Process` instance still refers to the same process. It compares
PID and creation time, and returns ``False`` if the PID was reused.
Prefer it over :func:`pid_exists`.

.. _faq_pid_exists_vs_isrunning:

What is the difference between pid_exists() and Process.is_running()?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:func:`pid_exists` checks whether a PID is present in the process list.
:meth:`Process.is_running` does the same, but also detects :ref:`PID
reuse <faq_pid_reuse>` by comparing the process creation time. Use
:func:`pid_exists` when you have a bare PID and don't need to guard
against reuse (it's faster). Use :meth:`Process.is_running` when you
hold a :class:`Process` object and want to confirm it still refers to
the same process.

-------------------------------------------------------------------------------

CPU
---

.. _faq_cpu_percent:

Why does cpu_percent() return 0.0 on first call?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:func:`cpu_percent` (and :meth:`Process.cpu_percent`) measures CPU usage
*between two calls*. The very first call has no prior sample to compare
against, so it always returns ``0.0``. The fix is to call it once to
initialize the baseline, discard the result, then call it again after a
short sleep:

.. code-block:: python

  import time
  import psutil

  psutil.cpu_percent()          # discard first call
  time.sleep(0.5)
  print(psutil.cpu_percent())   # meaningful value

Alternatively, pass ``interval`` to make it block internally:

.. code-block:: python

  print(psutil.cpu_percent(interval=0.5))

The same applies to :meth:`Process.cpu_percent`:

.. code-block:: python

  p = psutil.Process()
  p.cpu_percent()               # discard
  time.sleep(0.5)
  print(p.cpu_percent())        # meaningful value

.. _faq_cpu_percent_gt_100:

Can Process.cpu_percent() return a value higher than 100%?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Yes. On a multi-core system a process can run threads on several CPUs at
the same time. The maximum value is ``psutil.cpu_count() * 100``. For
example, on a 4-core machine a fully-loaded process can reach 400%.
The system-wide :func:`cpu_percent` (without a :class:`Process`) always
stays in the 0–100% range because it averages across all cores.

.. _faq_cpu_count:

What is the difference between psutil, os, and multiprocessing cpu_count()?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- :func:`os.cpu_count` returns the number of **logical** CPUs (including
  hyperthreads). It is the same as ``psutil.cpu_count(logical=True)``, but
  psutil does not honour `PYTHON_CPU_COUNT`_ environment variable introduced in
  Python 3.13.
- :func:`os.process_cpu_count` (Python 3.13+) returns the number of CPUs the
  calling process is **allowed to use** (respects CPU affinity and cgroups).
  The psutil equivalent is ``len(psutil.Process().cpu_affinity())``.
- :func:`multiprocessing.cpu_count` returns the same value as
  :func:`os.process_cpu_count` (Python 3.13+).
- :func:`psutil.cpu_count` with ``logical=False`` returns the number of
  **physical** cores, which has no stdlib equivalent.

-------------------------------------------------------------------------------

Memory
------

.. _faq_virtual_memory_available:

What is the difference between virtual_memory() available and free?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:func:`virtual_memory` returns both ``free`` and ``available``, but they
measure different things:

- ``free``: memory that is not being used at all.
- ``available``: how much memory can be given to processes without swapping.
  This includes reclaimable caches and buffers that the OS can reclaim under
  pressure.

In practice, ``available`` is almost always the metric you want when monitoring
memory. ``free`` can be misleadingly low on systems where the OS aggressively
uses RAM for caches (which is normal and healthy). On Windows, ``free`` and
``available`` are the same value.

.. _faq_memory_rss_vs_vms:

What is the difference between RSS and VMS?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- ``rss`` (Resident Set Size): the amount of physical memory (RAM)
  currently mapped into the process.
- ``vms`` (Virtual Memory Size): the total virtual address space of the
  process, including memory that has been swapped out, shared libraries,
  and memory-mapped files.

``rss`` is the go-to metric for answering "how much RAM is this process
using?". Note that it includes shared memory, so it may overestimate
actual usage when compared across processes. ``vms`` is generally larger
and can be misleadingly high, as it includes memory that is not resident
in physical RAM.

Both values are portable across platforms and are returned by
:meth:`Process.memory_info`.

.. _faq_memory_footprint:

When should I use memory_footprint() vs memory_info()?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:meth:`Process.memory_info` returns ``rss``, which includes shared
libraries counted in every process that uses them. For example, if
``libc`` uses 2 MB and 100 processes map it, each process includes those
2 MB in its ``rss``.

:meth:`Process.memory_footprint` returns USS (Unique Set Size), i.e.
memory private to the process. It represents the amount of memory that
would be freed if the process were terminated right now.
It is more accurate than RSS, but substantially slower and requires higher
privileges. On Linux it also returns PSS (Proportional Set Size) and swap.

.. _faq_used_plus_free:

Why does virtual_memory() used + free != total?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Because some memory (like cache and buffers) is reclaimable and accounted
separately:

.. code-block:: pycon

  >>> import psutil
  >>> m = psutil.virtual_memory()
  >>> m.used + m.free == m.total
  False

The ``available`` field already includes this reclaimable memory and is the
best indicator of memory pressure. See :ref:`faq_virtual_memory_available`.

.. _`BPO-6973`: https://bugs.python.org/issue6973
.. _`PYTHON_CPU_COUNT`: https://docs.python.org/3/using/cmdline.html#envvar-PYTHON_CPU_COUNT
