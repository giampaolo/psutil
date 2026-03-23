.. currentmodule:: psutil

Performance
===========

Use process_iter() with an attrs list
--------------------------------------

If you **iterate over multiple PIDs**, use :func:`process_iter`.
It accepts a ``attrs`` argument that pre-fetches only the requested attributes
in a single pass, minimizing system calls by fetching multiple attributes at once.
This is faster than calling individual methods in a loop.

Slow:

.. code-block:: python

  import psutil

  for p in psutil.process_iter():
      try:
          print(p.pid, p.name(), p.status())
      except (psutil.NoSuchProcess, psutil.AccessDenied):
          pass

Fast:

.. code-block:: python

  import psutil

  for p in psutil.process_iter(["name", "status"]):
      # values are retrieved from an internal cache
      print(p.pid, p.name(), p.status())

Note: :func:`process_iter(attrs=...)` is effectively the iterator-friendly
equivalent of using :meth:`Process.oneshot` on each process.

Use oneshot() when reading multiple process attributes
------------------------------------------------------

If you're dealing with a single :class:`Process` instance and need to
retrieve multiple process information, use :meth:`Process.oneshot`.
Each method call issue a separate system call, but the OS often returns
multiple fields at once, which :meth:`oneshot` caches for later use.

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
