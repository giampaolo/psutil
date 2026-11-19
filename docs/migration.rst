Migration guide
===============

This page summarises the breaking changes introduced in each major release and
shows the code changes required to upgrade.

.. note::
  Minor and patch releases (e.g. 6.1.x, 7.1.x) do not contain breaking changes.
  Only major releases are listed here.

.. _migration-8.0:

Migrating to 8.0
-----------------

Key breaking changes in 8.0:

- Named tuple field order changed: use attribute access instead of positional
  unpacking.
- Some return types are now enums instead of strings.
- :meth:`Process.memory_full_info` is deprecated: use
  :meth:`Process.memory_footprint`.
- :func:`virtual_memory` and :func:`swap_memory` are :term:`soft deprecated`:
  use :func:`memory_physical` and :func:`memory_swap`. No warning is raised.
- :meth:`Process.num_ctx_switches` is deprecated: use
  :meth:`Process.ctx_switches`.
- :meth:`Process.ionice` on Windows returns a ``(ioclass, value)`` named tuple
  instead of an integer.
- New :meth:`Process.memory_extras` method, returning extra platform-specific
  memory metrics.
- New :attr:`Process.attrs`: :class:`frozenset` of valid attribute names;
  ``process_iter(attrs=[])`` is deprecated.
- New :attr:`Process.snapshot`: a read-only :class:`ProcessSnapshot` holding
  the attributes collected by :func:`process_iter`; ``Process.info`` is
  deprecated.
- New :func:`set_procfs_path` function to relocate ``/proc``. Use this instead
  of setting :data:`PROCFS_PATH`.
- ``psutil.OSX`` removed: use :data:`MACOS`.
- Python 3.6 and 3.7 dropped.
- Windows < 10 dropped.
- macOS 10.7 and 10.8 dropped.

.. important::

  Do not rely on positional unpacking of named tuples. Always use attribute
  access (e.g. ``t.rss``). Named tuples can grow new fields, e.g.
  :func:`virtual_memory` gained :field:`cached` and :field:`wired` on Windows.

.. _migration-8.0-cpu-times:

:func:`cpu_times` field order changed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:field:`user`, :field:`system` and :field:`idle` are now the first 3 fields on
all platforms, followed by the platform-specific ones (e.g. :field:`nice`).
Positional access silently returns the wrong field on Linux, macOS and BSD.

.. code-block:: python

  # before
  user, nice, system, idle = psutil.cpu_times()[:4]

  # after
  t = psutil.cpu_times()
  user, system, idle = t.user, t.system, t.idle

.. _migration-8.0-memory-info:

:meth:`Process.memory_info` fields changed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The returned named tuple changed size and field order. Unless noted, old names
still work but raise :exc:`DeprecationWarning`.

- Linux: :field:`lib` and :field:`dirty` removed (always 0 since Linux 2.6).
- macOS: :field:`pfaults` and :field:`pageins` removed with **no aliases**. Use
  :meth:`Process.page_faults`.
- Windows renamed fields: :field:`wset` → :field:`rss`, :field:`peak_wset` →
  :field:`peak_rss`, :field:`pagefile` and :field:`private` → :field:`vms`,
  :field:`peak_pagefile` → :field:`peak_vms`, :field:`num_page_faults` →
  :meth:`Process.page_faults`. The ``*_pool`` fields moved to
  :meth:`Process.memory_extras`.
- BSD: new :field:`peak_rss` field.

.. code-block:: python

  # before
  rss, vms, shared, text, lib, data, dirty = p.memory_info()  # Linux
  p.memory_info().pageins  # macOS
  p.memory_info().wset  # Windows
  p.memory_info().paged_pool  # Windows

  # after
  m = p.memory_info()  # Linux
  rss, vms, shared, text, data = m.rss, m.vms, m.shared, m.text, m.data
  p.page_faults().major  # macOS
  p.memory_info().rss  # Windows
  p.memory_extras().paged_pool  # Windows

.. _migration-8.0-memory-names:

:func:`virtual_memory` and :func:`swap_memory` are soft deprecated
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

They are now :term:`soft deprecated` aliases of :func:`memory_physical` and
:func:`memory_swap`. No warning is raised and there are no plans to remove
them.

.. code-block:: python

  # before
  psutil.virtual_memory()
  psutil.swap_memory()

  # after
  psutil.memory_physical()
  psutil.memory_swap()

.. _migration-8.0-ctx-switches:

:meth:`Process.num_ctx_switches` is deprecated
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use :meth:`Process.ctx_switches` instead. :meth:`Process.as_dict` now returns a
``ctx_switches`` key.

.. code-block:: python

  # before
  p.num_ctx_switches()
  p.as_dict()["num_ctx_switches"]

  # after
  p.ctx_switches()
  p.as_dict()["ctx_switches"]

.. _migration-8.0-ionice:

:meth:`Process.ionice` returns a named tuple on Windows
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

On Windows :meth:`Process.ionice` now returns a ``(ioclass, value)`` named
tuple, like on Linux. :field:`value` is always ``0``.

.. code-block:: python

  # before
  p.ionice() == psutil.IOPRIO_NORMAL

  # after
  p.ionice().ioclass == psutil.IOPRIO_NORMAL

.. _migration-8.0-users-host:

:func:`users` no longer reports ``"localhost"``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :field:`host` field used to be ``"localhost"`` both when the OS recorded no
host and for an X display (``":0"``). It is now ``None`` in the first case and
the display name in the second.

.. code-block:: python

  # before
  local = [u for u in psutil.users() if u.host == "localhost"]

  # after
  local = [u for u in psutil.users() if not u.host or u.host.startswith(":")]

.. _migration-8.0-snapshot:

:attr:`Process.info` is deprecated
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The attributes collected by :func:`process_iter` are now exposed via
:attr:`Process.snapshot`, a read-only :class:`ProcessSnapshot`. The ``info``
dict still works but raises :exc:`DeprecationWarning`. An attribute which was
not requested raises :exc:`AttributeError` instead of :exc:`KeyError`. If you
need a dict use :meth:`p.snapshot.as_dict() <ProcessSnapshot.as_dict>`.

.. code-block:: python

  # before
  for p in psutil.process_iter(["name", "username"]):
      print(p.info["name"], p.info["username"])

  # after
  for p in psutil.process_iter(["name", "username"]):
      print(p.snapshot.name, p.snapshot.username)

.. _migration-8.0-attrs:

New :attr:`Process.attrs` class attribute
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It's a :class:`frozenset` of the attribute names accepted by
:meth:`Process.as_dict` and :func:`process_iter`:

.. code-block:: python

  # before
  attrs = list(psutil.Process().as_dict().keys())

  # after
  attrs = psutil.Process.attrs

``process_iter(attrs=[])`` (empty list meaning "all") is deprecated in favor of
:attr:`Process.attrs`:

.. code-block:: python

  # before
  psutil.process_iter(attrs=[])

  # after
  psutil.process_iter(attrs=psutil.Process.attrs)
  # all except connections
  psutil.process_iter(attrs=psutil.Process.attrs - {"net_connections"})

.. _migration-8.0-cpu-times-irq:

:func:`cpu_times` :field:`interrupt` renamed to :field:`irq` on Windows
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The old name still works but raises :exc:`DeprecationWarning`.

.. code-block:: python

  # before
  psutil.cpu_times().interrupt

  # after
  psutil.cpu_times().irq

.. _migration-8.0-enums:

Constants and fields are now enums
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These now return enum members instead of plain ``str`` / ``int``. The matching
module constants are members of the same enums:

- :meth:`Process.status` → :class:`ProcessStatus`
- :field:`status` field of :meth:`Process.net_connections` and
  :func:`net_connections` → :class:`ConnectionStatus`
- :meth:`Process.nice` on Windows → :class:`ProcessPriority`
- :field:`ioclass` field of :meth:`Process.ionice` → :class:`ProcessIOPriority`
- :data:`RLIMIT_* <psutil.RLIMIT_NOFILE>` of :meth:`Process.rlimit` →
  :class:`ProcessRlimit`

They subclass :class:`enum.StrEnum` / :class:`enum.IntEnum`, so comparisons
keep working. Only code inspecting :func:`repr` or :class:`type` needs
updating.

.. code-block:: python

  # before
  p.status()  # 'running'

  # after
  p.status()  # <ProcessStatus.STATUS_RUNNING: 'running'>

.. _migration-8.0-memory-full-info:

:meth:`Process.memory_full_info` is deprecated
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use :meth:`Process.memory_footprint` instead. It returns :field:`uss` (plus
:field:`pss` and :field:`swap` on Linux) and a new :field:`shared` field, but
not the :meth:`Process.memory_info` fields (:field:`rss`, :field:`vms`, etc.).
:meth:`Process.memory_footprint` is only available on Linux, macOS and Windows.
On the other platforms use :meth:`Process.memory_info`.

.. code-block:: python

  # before
  m = p.memory_full_info()
  m.rss, m.uss

  # after
  p.memory_info().rss
  p.memory_footprint().uss

.. _migration-8.0-connections:

:meth:`Process.connections` raises :exc:`FutureWarning`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Deprecated since 6.0, it now raises :exc:`FutureWarning` instead of
:exc:`DeprecationWarning`, so it's shown by default. It will be removed in 9.0.
Use :meth:`Process.net_connections` (see :ref:`migration-6.0`).

.. _migration-8.0-memory-extras:

New :meth:`Process.memory_extras` method
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Extra platform-specific memory metrics which complement
:meth:`Process.memory_info`:

- Linux: :field:`peak_rss`, :field:`peak_vms`, :field:`rss_anon`,
  :field:`rss_file`, :field:`rss_shmem`, :field:`swap_anon`, :field:`locked`.
- macOS: :field:`phys_footprint`, :field:`peak_phys_footprint`.
- Windows: :field:`virtual`, :field:`peak_virtual`, :field:`paged_pool`,
  :field:`nonpaged_pool`, :field:`peak_paged_pool`,
  :field:`peak_nonpaged_pool`.

.. _migration-8.0-procfs-path:

New :func:`set_procfs_path` function
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Assigning :data:`PROCFS_PATH` directly still works but leaves internal caches
stale. Use :func:`set_procfs_path` instead:

.. code-block:: python

  # before
  psutil.PROCFS_PATH = "/host/proc"

  # after
  psutil.set_procfs_path("/host/proc")

The :envvar:`PSUTIL_PROCFS_PATH` environment variable does the same from
outside the process.

``psutil.OSX`` removed
^^^^^^^^^^^^^^^^^^^^^^

The ``psutil.OSX`` constant, deprecated since 5.4.7 in 2018, was removed. Use
:data:`MACOS` instead.

.. code-block:: python

  # before
  if psutil.OSX:
      ...

  # after
  if psutil.MACOS:
      ...

Python 3.6 and 3.7 dropped
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The minimum version is now Python 3.8. The last release supporting Python 3.6
and 3.7 is psutil 7.2.x:

.. code-block:: bash

  pip install "psutil==7.2.*"

.. _migration-8.0-windows:

Windows < 10 dropped
^^^^^^^^^^^^^^^^^^^^^

The minimum version is now Windows 10 / Windows Server 2016. Windows Vista, 7,
8, 8.1 and their server counterparts (Server 2008 to 2012 R2) are no longer
supported. See :gh:`2893`.

.. _migration-8.0-git-tags:

Git tags renamed
^^^^^^^^^^^^^^^^^

Git tags were renamed from ``release-X.Y.Z`` to ``vX.Y.Z``. Old tags remain for
backward compatibility. See :gh:`2788`.

.. code-block:: bash

  # before
  pip install git+https://github.com/giampaolo/psutil@release-7.2.2

  # after
  pip install git+https://github.com/giampaolo/psutil@v7.2.2

.. _migration-7.0:

Migrating to 7.0
-----------------

``Process.memory_info_ex()`` removed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``Process.memory_info_ex()``, deprecated since 4.0.0 in 2016, was removed. Use
:meth:`Process.memory_full_info` instead.

.. code-block:: python

  # before
  p.memory_info_ex()

  # after
  p.memory_full_info()

Python 2.7 dropped
^^^^^^^^^^^^^^^^^^^^

Python 2.7 is no longer supported. The last release supporting it is psutil
6.1.x:

.. code-block:: bash

  pip2 install "psutil==6.1.*"

.. _migration-6.0:

Migrating to 6.0
-----------------

:meth:`Process.connections` renamed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:meth:`Process.connections` was renamed to :meth:`Process.net_connections` for
consistency with the system-level :func:`net_connections`. The old name raises
:exc:`DeprecationWarning` and will be removed in a future release:

.. code-block:: python

  # before
  p.connections()
  p.connections(kind="tcp")

  # after
  p.net_connections()
  p.net_connections(kind="tcp")

:func:`disk_partitions` lost two fields
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :field:`maxfile` and :field:`maxpath` fields were removed from the named
tuple returned by :func:`disk_partitions`. Positional unpacking will break:

.. code-block:: python

  # before (broken)
  device, mountpoint, fstype, opts, maxfile, maxpath = part

  # after
  device, mountpoint, fstype, opts = (
      part.device, part.mountpoint, part.fstype, part.opts
  )

:func:`process_iter` no longer checks for PID reuse
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:func:`process_iter` no longer preemptively checks whether yielded PIDs have
been reused, making it ~20× faster. To verify that a process object is still
alive and refers to the same process, use :meth:`Process.is_running`
explicitly:

.. code-block:: python

  for p in psutil.process_iter(["name"]):
      if p.is_running():
          print(p.pid, p.snapshot.name)
