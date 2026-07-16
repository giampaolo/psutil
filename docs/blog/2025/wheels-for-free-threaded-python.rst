.. post:: 2025-10-25
   :tags: wheels, community, python-core
   :author: Giampaolo Rodola
   :exclude:

   Unlocking ``pip install psutil`` for no-GIL Python

Wheels for free-threaded Python now available
=============================================

With the release of psutil 7.1.2, wheels for free-threaded Python are now
available. This milestone was achieved largely through a community effort, as
several internal refactorings to the C code were required to make it possible
(see :gh:`2565`). Many of these changes were contributed by
`Lysandros Nikolaou <https://github.com/lysnikolaou>`__. Thanks to him for the
effort and for bearing with me in code reviews! ;-)

What is free-threaded Python?
-----------------------------

Free-threaded Python (available since Python 3.13) refers to Python builds that
are compiled with the **GIL (Global Interpreter Lock) disabled**, allowing true
parallel execution of Python bytecodes across multiple threads. This is
particularly beneficial for CPU-bound applications, as it enables better
utilization of multi-core processors.

The state of free-threaded wheels
---------------------------------

According to Hugo van Kemenade's `free-threaded wheels
tracker <https://hugovk.github.io/free-threaded-wheels/>`__, the
adoption of free-threaded wheels among the top 360 most-downloaded
PyPI packages with C extensions is still limited. Only 128 out of
these 360 packages provide wheels compiled for free-threaded Python,
meaning they can run on Python builds with the GIL disabled. This shows
that, while progress has been made, most popular packages with C
extensions still do not offer ready-made wheels for free-threaded
Python.

What it means for users
-----------------------

When a library author provides a wheel, users can install a pre-compiled binary
package without having to build it from source. This is especially important
for packages with C extensions, like psutil, which is largely written in C.
Such packages often have complex build requirements and require installing a C
compiler. On Windows, that means installing Visual Studio or the Build Tools,
which can take several gigabytes and a *significant* setup effort. Providing
wheels spares users from this hassle, makes installation far simpler, and is
effectively essential for the users of that package. You basically
``pip install psutil`` and you're done.

What it means for library authors
---------------------------------

Currently, **universal wheels for free-threaded Python do not exist**. Each
wheel must be built specifically for a Python version. Right now authors must
create separate wheels for Python 3.13 and 3.14. Which means distributing
*a lot* of files already:

.. code-block:: none

   psutil-7.1.2-cp313-cp313t-macosx_10_13_x86_64.whl
   psutil-7.1.2-cp313-cp313t-macosx_11_0_arm64.whl
   psutil-7.1.2-cp313-cp313t-manylinux2010_x86_64.manylinux_2_12_x86_64.manylinux_2_28_x86_64.whl
   psutil-7.1.2-cp313-cp313t-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
   psutil-7.1.2-cp313-cp313t-win_amd64.whl
   psutil-7.1.2-cp313-cp313t-win_arm64.whl
   psutil-7.1.2-cp314-cp314t-macosx_10_15_x86_64.whl
   psutil-7.1.2-cp314-cp314t-macosx_11_0_arm64.whl
   psutil-7.1.2-cp314-cp314t-manylinux2010_x86_64.manylinux_2_12_x86_64.manylinux_2_28_x86_64.whl
   psutil-7.1.2-cp314-cp314t-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
   psutil-7.1.2-cp314-cp314t-win_amd64.whl
   psutil-7.1.2-cp314-cp314t-win_arm64.whl

This also multiplies CI jobs and slows down the test matrix (see
`build.yml <https://github.com/giampaolo/psutil/blob/7dfd0ed34fe70ffd879ae62d21aabd4a8ed06d6f/.github/workflows/build.yml>`__).
A true universal wheel would greatly reduce this overhead, allowing a single
wheel to support multiple Python versions and platforms. Hopefully, Python 3.15
will simplify this process. Two competing proposals,
`PEP 803 <https://www.python.org/dev/peps/pep-0803/>`__ and
`PEP 809 <https://www.python.org/dev/peps/pep-0809/>`__, aim to standardize
wheel naming and metadata to allow producing a single wheel that covers
multiple Python versions. That would drastically reduce distribution complexity
for library authors, and it's fair to say it's essential for free-threaded
CPython to truly succeed.

How to install free-threaded psutil
-----------------------------------

You can now install psutil for free-threaded Python directly via ``pip``:

.. code-block:: bash

   pip install psutil --only-binary=:all:

This ensures you get the pre-compiled wheels without triggering a source build.

Discussion
----------

-  `Reddit <https://www.reddit.com/r/Python/comments/1ofrx8v/comment/nllztz6/>`__
