.. post:: 2019-03-05
   :tags: windows, macos, new-api, compatibility, release
   :author: Giampaolo Rodola
   :exclude:

   5.6.0 adds :meth:`~psutil.Process.parents`, brings several Windows improvements, and removes :meth:`~psutil.Process.memory_maps` on macOS

Announcing psutil 5.6.0
=======================

psutil 5.6.0 is out. Highlights: a new :meth:`Process.parents` method, several
important Windows improvements, and the removal of :meth:`Process.memory_maps`
on macOS.

Process parents()
-----------------

The new method returns the parents of a process as a list of :class:`Process`
instances. If no parents are known, an empty list is returned.

.. code-block:: pycon

    >>> import psutil
    >>> p = psutil.Process(5312)
    >>> p.parents()
    [psutil.Process(pid=4699, name='bash', started='09:06:44'),
     psutil.Process(pid=4689, name='gnome-terminal-server', started='09:06:44'),
     psutil.Process(pid=1, name='systemd', started='05:56:55')]

Nothing fundamentally new here, since this is a convenience wrapper around
:meth:`Process.parent`, but it's still nice to have it built in. It pairs well
with :meth:`Process.children` when working with process trees. The idea was
proposed by Ghislain Le Meur.

Windows
-------

Certain Windows APIs that need to be dynamically loaded from DLLs are now
loaded only once at startup, instead of on every function call. This makes some
operations **50% to 100% faster**; see benchmarks in :pr:`1422`.

:meth:`Process.suspend` and :meth:`Process.resume` previously iterated over all
process threads via ``CreateToolhelp32Snapshot()``, which was unorthodox and
broke when the process had been suspended by Process Hacker. They now call the
undocumented ``NtSuspendProcess()`` / ``NtResumeProcess()`` NT APIs, same as
Process Hacker and Sysinternals tools. Discussed in :gh:`1379`, implemented in
:pr:`1435`.

``SE DEBUG`` is a privilege bit set on the Python process at startup so psutil
can query processes owned by other users (Administrator, Local System), meaning
fewer :exc:`AccessDenied` exceptions for low-PID processes. The code setting it
had presumably been broken for years and is now finally fixed in :pr:`1429`.

Removal of Process.memory_maps() on macOS
-----------------------------------------

:meth:`Process.memory_maps` is gone on macOS (:gh:`1291`). The underlying Apple
API would randomly raise ``EINVAL`` or segfault the host process, and no amount
of reverse-engineering produced a safe fix. So I removed it. This is covered in
a :doc:`separate post </blog/2019/macos-memory-maps>`.

Improved exceptions
-------------------

One problem that affected psutil maintenance over the years was receiving bug
reports whose tracebacks did not indicate which syscall had actually failed.
This was especially painful on Windows, where a single routine may invoke
multiple Windows APIs. Now the :exc:`OSError` (or ``WindowsError``) exception
includes the syscall from which the error originated. See :pr:`1428`.

Other changes
-------------

See the :ref:`changelog <560>`.
