.. post:: 2016-02-25
   :tags: bsd, new-platform, community, release
   :author: Giampaolo Rodola
   :exclude:

   Completing the BSD trio alongside FreeBSD and OpenBSD

NetBSD support
==============

Roughly two months have passed since I last
:doc:`announced </blog/2015/openbsd-support>` that psutil added support for
OpenBSD. Today I'm happy to announce that it's the turn of NetBSD! This was
contributed by `Thomas Klausner <https://github.com/0-wiz-0>`_,
`Ryo Onodera <https://github.com/ryoon>`_ and myself in :pr:`557`.

Differences with FreeBSD (and OpenBSD)
--------------------------------------

The NetBSD implementation has limitations similar to the ones I encountered
with OpenBSD. Again, FreeBSD remains the BSD variant with the best support in
terms of kernel functionality.

* :meth:`Process.memory_maps` is not implemented. The kernel provides the
  necessary pieces, but I haven't done this yet (hopefully later).
* :meth:`Process.num_ctx_switches`'s :field:`involuntary` field is always 0.
  The ``kinfo_proc()`` syscall provides this info, but it's always set to 0.
* :meth:`Process.cpu_affinity` (get and set) is not supported.
* :func:`psutil.cpu_count` ``(logical=False)`` always returns ``None``.

As for the rest: it is all there. All memory, disk, network and process APIs
are fully supported and functioning.

Other enhancements available in this psutil release
---------------------------------------------------

Besides NetBSD support, this release has a couple of interesting enhancements:

* :gh:`708`: [Linux] :func:`psutil.net_connections` and
  :meth:`Process.connections` can be up to 3x faster when there are many
  connections.
* :gh:`718`: :func:`psutil.process_iter` is now thread safe.

You can read the rest in the :ref:`changelog <341>`, as usual.

Discussion
----------

* `Reddit <https://www.reddit.com/r/Python/comments/4131q2/netbsd_support_for_psutil/>`_
* `Hacker News <https://news.ycombinator.com/item?id=10909101>`_
