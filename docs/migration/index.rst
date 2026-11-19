Migration guide
===============

These pages list the breaking changes and deprecations of each release, and
show the code changes required to upgrade.

.. grid:: 1 1 3 3
   :gutter: 3

   .. grid-item-card:: 8.0
      :link: 8.0
      :link-type: doc

      A major breaking release. Process memory APIs were reorganized, many
      names deprecated, Python 3.6 and 3.7 dropped.

   .. grid-item-card:: 7.0
      :link: 7.0
      :link-type: doc

      ``Process.memory_info_ex()`` removed, Python 2.7 dropped.

   .. grid-item-card:: 6.0
      :link: 6.0
      :link-type: doc

      ``disk_partitions()`` lost two fields, ``process_iter()`` no longer
      checks for PID reuse, ``Process.connections()`` renamed.

Other releases
--------------

.. list-table::
   :header-rows: 1
   :widths: 12 88

   * - Release
     - What changed
   * - 7.1
     - FreeBSD 8 and SunOS 10 dropped, 32-bit wheels no longer published.
   * - 5.9
     - Python 2.6, 3.4 and 3.5 dropped.
   * - 5.7
     - Windows XP and Server 2003 dropped.
   * - 5.6
     - :meth:`Process.memory_maps` removed on macOS (see
       :doc:`/blog/2019/macos-memory-maps`).
   * - 5.4
     - ``psutil.OSX`` deprecated, ``Process.memory_info_ex()`` raises
       :exc:`FutureWarning`, Python 3.3 dropped.
   * - 5.3
     - :field:`raddr` of UNIX sockets is ``""`` instead of ``None``, strings
       use the OS filesystem encoding (see
       :doc:`/blog/2017/unicode-internals`), Windows ``.exe`` installers no
       longer provided.
   * - 4.0
     - :meth:`Process.memory_info` returns more fields,
       ``Process.memory_info_ex()`` deprecated.
   * - 3.0
     - APIs deprecated in 2.0 removed, some constants are enums.
   * - 2.2
     - Python 2.4 and 2.5 dropped.
   * - 2.0
     - :class:`Process` properties turned into methods, ``get_*`` and
       ``set_*`` names renamed (see :doc:`/blog/2014/porting-to-20`).

.. toctree::
   :hidden:

   8.0
   7.0
   6.0
