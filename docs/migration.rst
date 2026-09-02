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

- :func:`process_iter` now pre-fetches values.
- :attr:`Process.info` is deprecated: use direct methods instead.
- Named tuple field order changed: use attribute access instead of positional
  unpacking.
- Some return types are now enums instead of strings.
- :meth:`Process.memory_full_info` is deprecated: use
  :meth:`Process.memory_footprint`.
- New :meth:`Process.memory_extras` method, returning extra platform-specific
  memory metrics.
- New :attr:`Process.attrs`: :class:`frozenset` of valid attribute names;
  ``process_iter(attrs=[])`` is deprecated.
- Python 3.6 and 3.7 dropped.
- Windows < 10 dropped.
- macOS 10.7 and 10.8 dropped.

.. important::

  Do not rely on positional unpacking of named tuples. Always use attribute
  access (e.g. ``t.rss``).

.. _migration-8.0-process-iter:

process_iter(): p.info is deprecated
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:func:`process_iter` now caches pre-fetched values internally, so normal method
calls can return them without using the :attr:`Process.info` dict. ``p.info``
still works, but raises :exc:`DeprecationWarning`.

.. code-block:: python

  import psutil

  # before
  for p in psutil.process_iter(attrs=["name", "status"]):
      print(p.info["name"], p.info["status"])

  # after
  for p in psutil.process_iter(attrs=["name", "status"]):
      print(p.name(), p.status())  # return cached values, never raise

When ``attrs`` are specified, the corresponding method calls return cached
values without extra syscalls. :exc:`AccessDenied` / :exc:`ZombieProcess` are
handled transparently by returning ``ad_value``.

If you need a dict, use :meth:`Process.as_dict` instead of
:attr:`Process.info`.

.. code-block:: python

  import psutil

  # before
  for p in psutil.process_iter(attrs=["name", "status"]):
      print(p.info)

  # after
  attrs = ["name", "status"]
  for p in psutil.process_iter(attrs=attrs):
      print(p.as_dict(attrs))  # return cached values, never raise

.. note::
  If ``"name"`` was pre-fetched via ``attrs``, ``p.name()`` returns
  ``ad_value`` instead of raising :exc:`AccessDenied`. If you need the
  exception, do not include the method in ``attrs``.

.. _migration-8.0-namedtuples:

Named tuple field order changed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- :func:`cpu_times`: :field:`user`, :field:`system`, :field:`idle` fields
  changed order on Linux, macOS and BSD. They are now always the first 3 fields
  on all platforms, with platform-specific fields (e.g. :field:`nice`)
  following. Positional access (e.g. ``cpu_times()[3]``) silently returns the
  wrong field.

  .. code-block:: python

    # before
    user, nice, system, idle = psutil.cpu_times()

    # after
    t = psutil.cpu_times()
    user, system, idle = t.user, t.system, t.idle

- :meth:`Process.memory_info`: the returned named tuple changed size and field
  order.

  - Linux: :field:`lib` and :field:`dirty` fields removed (they were always 0
    since Linux 2.6). Aliases returning 0 and emitting
    :exc:`DeprecationWarning` are kept.
  - macOS: :field:`pfaults` and :field:`pageins` removed with **no aliases**.
    Use :meth:`Process.page_faults` instead.
  - Windows: old fields were renamed: :field:`wset` → :field:`rss`,
    :field:`peak_wset` → :field:`peak_rss`, :field:`pagefile` and
    :field:`private` → :field:`vms`, :field:`peak_pagefile` →
    :field:`peak_vms`, :field:`num_page_faults` → :meth:`Process.page_faults`.
    The old names still work but raise :exc:`DeprecationWarning`.
    :field:`paged_pool`, :field:`nonpaged_pool`, :field:`peak_paged_pool`,
    :field:`peak_nonpaged_pool` moved to :meth:`Process.memory_extras`.
  - BSD: a new :field:`peak_rss` field was added.

- :func:`virtual_memory`: on Windows, new :field:`cached` and :field:`wired`
  fields were added.

cpu_times() interrupt renamed to irq on Windows
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :field:`interrupt` field of :func:`cpu_times` on Windows was renamed to
:field:`irq` to match Linux and BSD. The old name still works but raises
:exc:`DeprecationWarning`.

.. _migration-8.0-enums:

Constants and fields are now enums
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These now yield enum members instead of plain ``str`` / ``int``, and the
matching module constants are members of the same enums:

- :meth:`Process.status` → :class:`ProcessStatus`
- :field:`status` field of :meth:`Process.net_connections` and
  :func:`net_connections` → :class:`ConnectionStatus`
- :meth:`Process.nice` on Windows → :class:`ProcessPriority`
- :field:`ioclass` field of :meth:`Process.ionice` → :class:`ProcessIOPriority`
- :data:`RLIMIT_* <psutil.RLIMIT_NOFILE>` of :meth:`Process.rlimit` →
  :class:`ProcessRlimit`

They subclass :class:`enum.StrEnum` / :class:`enum.IntEnum`, so they compare
equal to the values they replace: ``p.status() == psutil.STATUS_RUNNING`` keeps
working. Only code inspecting :func:`repr` or :class:`type` needs updating.

.. _migration-8.0-memory-full-info:

memory_full_info() is deprecated
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:meth:`Process.memory_full_info` is deprecated. Use
:meth:`Process.memory_footprint` instead; it returns the same fields
(:field:`uss`, :field:`pss` and :field:`swap`), plus a new :field:`shared`
field on Linux and Windows.

.. _migration-8.0-memory-extras:

New memory_extras() method
^^^^^^^^^^^^^^^^^^^^^^^^^^^

8.0 introduces a new :meth:`Process.memory_extras` method, returning extra
platform-specific memory metrics which complement :meth:`Process.memory_info`:

- Linux: :field:`peak_rss`, :field:`peak_vms`, :field:`rss_anon`,
  :field:`rss_file`, :field:`rss_shmem`, :field:`swap_anon`, :field:`hugetlb`.
- macOS: :field:`phys_footprint`, :field:`peak_footprint`.
- Windows: :field:`virtual`, :field:`peak_virtual`, :field:`paged_pool`,
  :field:`nonpaged_pool`, :field:`peak_paged_pool`,
  :field:`peak_nonpaged_pool`.

.. _migration-8.0-attrs:

New Process.attrs class attribute
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:attr:`Process.attrs` is a new :class:`frozenset` containing the valid
attribute names accepted by :meth:`Process.as_dict` and :func:`process_iter`.
It avoids creating a throwaway process just to discover them:

.. code-block:: python

  # before
  attrs = list(psutil.Process().as_dict().keys())

  # after
  attrs = psutil.Process.attrs

It also makes it easy to pass all or a subset of attributes.
``process_iter(attrs=[])`` (empty list meaning "all") is now deprecated; use
:attr:`Process.attrs` instead:

.. code-block:: python

  # all attrs
  psutil.process_iter(attrs=psutil.Process.attrs)

  # all except connections
  psutil.process_iter(attrs=psutil.Process.attrs - {"net_connections"})

Python 3.6 and 3.7 dropped
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The minimum version is now Python 3.8.

.. _migration-8.0-windows:

Windows < 10 dropped
^^^^^^^^^^^^^^^^^^^^^

Support for Windows Vista, 7, 8, 8.1 and their server counterparts (Server 2008
to 2012 R2) was removed. The minimum version is now Windows 10 / Windows Server
2016. The last release supporting older versions is the 7.2.x series. See
:gh:`2893`.

.. _migration-8.0-git-tags:

Git tags renamed
^^^^^^^^^^^^^^^^^

Git tags were renamed from ``release-X.Y.Z`` to ``vX.Y.Z`` (e.g.
``release-7.2.2`` → ``v7.2.2``). Old tags remain for backward compatibility. If
your scripts or URLs reference psutil tags, update them to the new format. See
:gh:`2788`.

-------------------------------------------------------------------------------

.. _migration-7.0:

Migrating to 7.0
-----------------

Process.memory_info_ex() removed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

-------------------------------------------------------------------------------

.. _migration-6.0:

Migrating to 6.0
-----------------

Process.connections() renamed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

disk_partitions() lost two fields
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :field:`maxfile` and :field:`maxpath` fields were removed from the named
tuple returned by :func:`disk_partitions`. Positional unpacking will break:

.. code-block:: python

  # before (broken)
  device, mountpoint, fstype, opts, maxfile, maxpath = part

  # after
  device, mountpoint, fstype, opts = (
      part.device, part.mountpoint, part.fstype, part.opts
  )

process_iter() no longer checks for PID reuse
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:func:`process_iter` no longer preemptively checks whether yielded PIDs have
been reused, making it ~20× faster. To verify that a process object is still
alive and refers to the same process, use :meth:`Process.is_running`
explicitly:

.. code-block:: python

  for p in psutil.process_iter(["name"]):
      if p.is_running():
          print(p.pid, p.name())
