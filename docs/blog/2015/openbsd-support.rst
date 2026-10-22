.. post:: 2015-11-25
   :tags: bsd, new-platform, community, release
   :author: Giampaolo Rodola
   :exclude:

   psutil 3.3.0 now runs on OpenBSD, sharing most of the implementation with FreeBSD

OpenBSD support
===============

Starting from version 3.3.0 (released just now) psutil officially supports
OpenBSD. This was contributed by `Landry Breuil <https://github.com/landryb>`__
and myself in :pr:`615`.

Differences with FreeBSD
------------------------

As expected, the OpenBSD implementation is very similar to FreeBSD's, so I
merged most of it into a single C file
(`_psutil_bsd.c <https://github.com/giampaolo/psutil/blob/release-3.3.0/psutil/_psutil_bsd.c>`__),
with 2 separate files
(`freebsd.c <https://github.com/giampaolo/psutil/blob/release-3.3.0/psutil/arch/bsd/freebsd.c>`__,
`openbsd.c <https://github.com/giampaolo/psutil/blob/release-3.3.0/psutil/arch/bsd/openbsd.c>`__)
for the parts that differ. Here are the functional differences with FreeBSD:

* :meth:`Process.memory_maps` is not implemented. The kernel provides the
  necessary pieces but I haven't done this yet (hopefully later).
* :meth:`Process.num_ctx_switches`'s :field:`involuntary` field is always 0.
  `kinfo_proc <https://github.com/giampaolo/psutil/blob/fc1e59d08c968898c2ede425a621b62ccf44681c/psutil/_psutil_bsd.c#L335>`__
  provides this info but it is always set to 0.
* :meth:`Process.cpu_affinity` (get and set) is not supported.
* :meth:`Process.exe` is determined by inspecting the command line, so it may
  not always be available (returns ``None``).
* :func:`psutil.swap_memory` :field:`sin` and :field:`sout`
  (:term:`swap in <swap-in>` and :term:`swap out <swap-out>`) values are not
  available, and are therefore always set to 0.
* :func:`psutil.cpu_count` ``(logical=False)`` always returns ``None``.

As with FreeBSD, :meth:`Process.open_files` can't return file paths (FreeBSD
can sometimes). Otherwise everything is there and I'm satisfied with the
result.

Considerations about BSD platforms
----------------------------------

psutil has supported FreeBSD since the beginning (year 2009). At the time, it
made sense to prefer it as the preferred BSD variant as it's the most
`most popular <https://en.wikipedia.org/wiki/Comparison_of_BSD_operating_systems#Popularity>`__.

Compared to FreeBSD, OpenBSD appears to be more "minimal", both in terms of
kernel facilities and the number of CLI tools available. One thing I
particularly appreciate about FreeBSD is that the source code for all CLI tools
is available under ``/usr/src``, which was a big help when implementing psutil
APIs.

OpenBSD source code is `also available <https://github.com/openbsd/src>`__, but
it uses CVS and I am not sure it includes the source code for all CLI tools.

There are still two more BSD variants worth supporting: NetBSD and DragonFlyBSD
(in this order). About a year ago, someone provided a patch (:gh:`429`) adding
basic NetBSD support, so that will likely happen sooner or later.

Other enhancements available in this release
--------------------------------------------

The only other enhancement is :gh:`558`, which allows specifying a different
location for the /proc filesystem on Linux.

Discussion
----------

* `Reddit <https://www.reddit.com/r/Python/comments/3u8wm3/openbsd_support_for_psutil_330/>`__
* `Hacker News <https://news.ycombinator.com/item?id=10628726>`__
