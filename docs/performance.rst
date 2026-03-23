.. _performance:

Performance
===========

This page describes how to use psutil efficiently. Most of the advice
applies when querying many processes in a loop, building monitoring
tools, or calling psutil APIs at high frequency.

Use process_iter() with an attrs list
--------------------------------------

:func:`process_iter` accepts an optional ``attrs`` list that pre-fetches
only the attributes you need for all processes in a single efficient
pass. This is faster than calling individual methods in a loop because
psutil internally uses :meth:`Process.oneshot` for each process.

Slow (fetches all info for each process, one attribute at a time):

.. code-block:: python

  import psutil

  for p in psutil.process_iter():
      try:
          print(p.pid, p.name(), p.status())
      except psutil.Error:
          pass

Fast (only fetches name and status, cached via oneshot):

.. code-block:: python

  import psutil

  for p in psutil.process_iter(["name", "status"]):
      print(p.pid, p.name(), p.status())

When ``attrs`` is specified, method calls return cached values instead
of issuing new system calls. If a process disappears or raises
:exc:`AccessDenied` for a requested attribute, the corresponding
method returns ``None`` (or a custom value set via ``ad_value``):

.. code-block:: python

  import psutil

  for p in psutil.process_iter(["name", "username"], ad_value="N/A"):
      print(p.pid, p.name(), p.username())


.. _oneshot:

Use oneshot() when reading multiple process attributes
------------------------------------------------------

Reading multiple attributes from the same process is the most common
source of avoidable overhead. Each attribute call normally results in a
separate system call. :meth:`Process.oneshot` caches all the information
that can be retrieved in a single kernel round-trip, so subsequent calls
within the context manager return cached values at essentially zero cost.

Without ``oneshot()``, four separate system calls are made:

.. code-block:: python

  import psutil

  p = psutil.Process()
  p.name()           # syscall
  p.cpu_times()      # syscall
  p.memory_info()    # syscall
  p.status()         # syscall

With ``oneshot()``, only one system call is needed for all four:

.. code-block:: python

  import psutil

  p = psutil.Process()
  with p.oneshot():
      p.name()       # one syscall, result cached
      p.cpu_times()  # from cache
      p.memory_info()  # from cache
      p.status()     # from cache

The speed improvement depends on the platform and on how many attributes
you read. On Linux the gain is typically 2-4x; on Windows it can be
much higher. As a rule of thumb: if you read more than two attributes
from the same process, use ``oneshot()``.
