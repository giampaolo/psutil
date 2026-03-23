.. _performance:

Performance
===========

Use process_iter() with an attrs list
--------------------------------------

If you iterate over multiple PIDs, use :func:`process_iter`.
It accepts a ``attrs`` argument that pre-fetches only the attributes you need
in a single pass, using :meth:`Process.oneshot` internally.
This is faster than calling individual methods in a loop.

Slow:

.. code-block:: python

  import psutil

  for p in psutil.process_iter():
      try:
          print(p.pid, p.name(), p.status())
      except psutil.Error:
          pass

Fast:

.. code-block:: python

  import psutil

  for p in psutil.process_iter(["name", "status"]):
      print(p.pid, p.name(), p.status())

Use oneshot() when reading multiple process attributes
------------------------------------------------------

If you're dealing with a single :class:`Process` instance, always use
:meth:`Process.oneshot`.

Each attribute call normally issues a separate system call, but many
attributes are returned together by the OS in a single round-trip.
:meth:`Process.oneshot` caches that result so subsequent calls within the context
manager return immediately without hitting the kernel again.

Slow:

.. code-block:: python

  import psutil

  p = psutil.Process()
  p.name()           # syscall
  p.cpu_times()      # syscall
  p.memory_info()    # syscall
  p.status()         # syscall

Fast:

.. code-block:: python

  import psutil

  p = psutil.Process()
  with p.oneshot():
      p.name()         # one syscall, result cached
      p.cpu_times()    # from cache
      p.memory_info()  # from cache
      p.status()       # from cache

The speed improvement depends on the platform and on how many attributes
you read. On Linux the gain is typically 2-4x; on Windows it can be
much higher. As a rule of thumb: if you read more than two attributes
from the same process, use ``oneshot()``.
