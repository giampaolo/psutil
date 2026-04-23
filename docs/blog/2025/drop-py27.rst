.. post:: 2025-02-13
   :tags: compatibility, release, featured
   :author: Giampaolo Rodola
   :exclude:

   Downloads fell from ~8% to 0.36% in three years; psutil
   7.0.0 ends support

Letting go of Python 2.7
========================

About dropping Python 2.7 support in psutil, 3 years ago I stated (:gh:`2014`):

   Not a chance, for many years to come. [Python 2.7] currently
   represents 7-10% of total downloads, meaning around 70k / 100k
   downloads per day.

Only 3 years later, and to my surprise,
**downloads for Python 2.7 dropped to 0.36%**! As such, as of psutil 7.0.0, I
finally decided to drop support for Python 2.7!

The numbers
-----------

These are downloads per month:

.. code-block:: none

   $ pypinfo --percent psutil pyversion
   Served from cache: False
   Data processed: 4.65 GiB
   Data billed: 4.65 GiB
   Estimated cost: $0.03

   | python_version | percent | download_count |
   | -------------- | ------- | -------------- |
   | 3.10           |  23.84% |     26,354,506 |
   | 3.8            |  18.87% |     20,862,015 |
   | 3.7            |  17.38% |     19,217,960 |
   | 3.9            |  17.00% |     18,798,843 |
   | 3.11           |  13.63% |     15,066,706 |
   | 3.12           |   7.01% |      7,754,751 |
   | 3.13           |   1.15% |      1,267,008 |
   | 3.6            |   0.73% |        803,189 |
   | 2.7            |   0.36% |        402,111 |
   | 3.5            |   0.03% |         28,656 |
   | Total          |         |    110,555,745 |

According to `pypistats.org <https://archive.is/wip/knzql>`__ Python 2.7
downloads represent 0.28% of the total, around 15,000 downloads per day.

The pain
--------

Keeping 2.7 alive had become increasingly difficult, but still possible: tests
ran via
`old PyPI backports <https://github.com/giampaolo/psutil/blob/fbb6d9ce98f930d3d101b7df5a4f4d0f1d2b35a3/setup.py#L76-L85>`__
and a
`tweaked GitHub Actions workflow <https://github.com/giampaolo/psutil/blob/fbb6d9ce98f930d3d101b7df5a4f4d0f1d2b35a3/.github/workflows/build.yml#L77-L112>`__
on Linux and macOS, plus a separate third-party service (Appveyor) for Windows.
But the workarounds in the source kept piling up:

-  A Python compatibility layer
   (`psutil/\_compat.py <https://github.com/giampaolo/psutil/blob/fbb6d9ce98f930d3d101b7df5a4f4d0f1d2b35a3/psutil/_compat.py>`__)
   plus ``#if PY_MAJOR_VERSION <= 3`` branches in C, with constant
   str-vs-unicode juggling on both sides.
-  No f-strings, and no free use of :mod:`enum` for constants (which ended up
   with a different API shape than on Python 3).
-  An outdated ``pip`` and
   `outdated deps <https://github.com/giampaolo/psutil/blob/fbb6d9ce98f930d3d101b7df5a4f4d0f1d2b35a3/setup.py#L76-L85>`__.
-  4 extra CI jobs per commit (Linux, macOS, Windows 32-bit and 64-bit), making
   the pipeline slower and flakier.
-  7 wheels specific to Python 2.7 to ship on every release:

.. code-block:: none

   psutil-6.1.1-cp27-cp27m-macosx_10_9_x86_64.whl
   psutil-6.1.1-cp27-none-win32.whl
   psutil-6.1.1-cp27-none-win_amd64.whl
   psutil-6.1.1-cp27-cp27m-manylinux2010_i686.whl
   psutil-6.1.1-cp27-cp27m-manylinux2010_x86_64.whl
   psutil-6.1.1-cp27-cp27mu-manylinux2010_i686.whl
   psutil-6.1.1-cp27-cp27mu-manylinux2010_x86_64.whl

The removal
-----------

The removal was done in :pr:`2481`, which dropped around 1500 lines of code
(nice!). **It felt liberating**. In doing so, in the doc I still made the
promise that the 6.1.\* series will keep supporting Python 2.7 and will receive
**critical bug-fixes only** (no new features). It will be maintained in a
specific `python2 branch <https://github.com/giampaolo/psutil/tree/python2>`__.
I explicitly kept the
`setup.py <https://github.com/giampaolo/psutil/blob/fbb6d9ce98f930d3d101b7df5a4f4d0f1d2b35a3/setup.py>`__
script compatible with Python 2.7 in terms of syntax, so that, when the tarball
is fetched from PyPI, it will emit an informative error message on
``pip install psutil``. The user trying to install psutil on Python 2.7 will
see:

.. code-block:: none

   $ pip2 install psutil
   As of version 7.0.0 psutil no longer supports Python 2.7.
   Latest version supporting Python 2.7 is psutil 6.1.X.
   Install it with: "pip2 install psutil==6.1.*".

Related
-------

-  2017-06: :gh:`1053` (2.7 ticket)
-  2022-04: :pr:`2099` (Drop 2.6)
-  2023-04: :pr:`2246` (Drop 3.4 & 3.5)
-  2024-12: :pr:`2481` (Drop 2.7)
