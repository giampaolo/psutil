.. post:: 2025-04-04
   :tags: tests, performance
   :author: Giampaolo Rodola
   :exclude:

   Trimming heavy imports and plugins: 0.42s → 0.30s (~28%)

Speeding up pytest startup
==========================

Preface: the migration to pytest
--------------------------------

Last year, after 17 years of :mod:`unittest`, I started adopting pytest in
psutil (see :gh:`2446`). The two advantages I cared about most were plain
``assert`` statements and
`pytest-xdist <https://pypi.org/project/pytest-xdist/>`__'s free parallelism.
Tests still inherit from :class:`unittest.TestCase` and there's no
``conftest.py`` or fixture use (rationale in :pr:`2456`).

What I want to focus on here is one of pytest's most frustrating aspects: slow
startup.

pytest invocation is slow
-------------------------

To measure pytest's startup time, let's run a very `simple
test <https://github.com/giampaolo/psutil/blob/265fcf94a5da4260beb514653a2124915bf2a4f2/psutil/tests/test_misc.py#L232-L236>`__
where execution time itself is negligible:

.. code-block:: text

   $ time python3 -m pytest psutil/tests/test_misc.py::TestMisc::test_version
   1 passed in 0.05s
   real    0m0,427s

Almost half a second, which is excessive for something I run repeatedly during
development. For comparison, the same test under :mod:`unittest`:

.. code-block:: text

   $ time python3 -m unittest psutil.tests.test_misc.TestMisc.test_version
   Ran 1 test in 0.000s
   real    0m0,204s

Roughly twice as fast. Why?

Where is time being spent?
--------------------------

A significant portion of pytest's overhead comes from import time, and there's
not much one can do about it:

.. code-block:: text

   $ time python3 -c "import pytest"
   real    0m0,151s

   $ time python3 -c "import unittest"
   real    0m0,065s

   $ time python3 -c "import psutil"
   real    0m0,056s

Disable plugin auto loading
---------------------------

After some research, I discovered that pytest automatically loads all plugins
installed on the system, even if they aren't used. Here's how to list them
(output is cut):

.. code-block:: text

   $ pytest --trace-config --collect-only
   ...
   active plugins:
       ...
       setupplan           : ~/.local/lib/python3.12/site-packages/_pytest/setupplan.py
       stepwise            : ~/.local/lib/python3.12/site-packages/_pytest/stepwise.py
       warnings            : ~/.local/lib/python3.12/site-packages/_pytest/warnings.py
       logging             : ~/.local/lib/python3.12/site-packages/_pytest/logging.py
       reports             : ~/.local/lib/python3.12/site-packages/_pytest/reports.py
       python_path         : ~/.local/lib/python3.12/site-packages/_pytest/python_path.py
       unraisableexception : ~/.local/lib/python3.12/site-packages/_pytest/unraisableexception.py
       threadexception     : ~/.local/lib/python3.12/site-packages/_pytest/threadexception.py
       faulthandler        : ~/.local/lib/python3.12/site-packages/_pytest/faulthandler.py
       instafail           : ~/.local/lib/python3.12/site-packages/pytest_instafail.py
       anyio               : ~/.local/lib/python3.12/site-packages/anyio/pytest_plugin.py
       pytest_cov          : ~/.local/lib/python3.12/site-packages/pytest_cov/plugin.py
       subtests            : ~/.local/lib/python3.12/site-packages/pytest_subtests/plugin.py
       xdist               : ~/.local/lib/python3.12/site-packages/xdist/plugin.py
       xdist.looponfail    : ~/.local/lib/python3.12/site-packages/xdist/looponfail.py
       ...

It turns out ``PYTEST_DISABLE_PLUGIN_AUTOLOAD`` environment variable can be
used to disable them. By running
``PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest --trace-config --collect-only`` again
I can see that the following plugins disappeared:

.. code-block:: text

   anyio
   pytest_cov
   pytest_instafail
   pytest_subtests
   xdist
   xdist.looponfail

Now let's run the test again with ``PYTEST_DISABLE_PLUGIN_AUTOLOAD``:

.. code-block:: text

   $ time PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest psutil/tests/test_misc.py::TestMisc::test_version
   1 passed in 0.05s
   real    0m0,285s

We went from 0.427s to 0.285s, a ~40% improvement. Not bad. We now need to
selectively enable only the plugins we actually use, via ``-p``. psutil uses
``pytest-instafail`` and ``pytest-subtests`` (we'll deal with ``pytest-xdist``
later):

.. code-block:: text

   $ time PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p instafail -p subtests ...
   real    0m0,320s

Time went back up to 0.320s. Quite a slowdown, but still better than the
original 0.427s. Adding ``pytest-xdist``:

.. code-block:: text

   $ time PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p instafail -p subtests -p xdist ...
   real    0m0,369s

0.369s. Not much, but still a pity to pay the price when NOT running tests in
parallel.

Handling pytest-xdist
---------------------

If we disable ``pytest-xdist`` psutil tests still run, but we get a warning:

.. code-block:: text

   psutil/tests/test_testutils.py:367
     ~/svn/psutil/psutil/tests/test_testutils.py:367: PytestUnknownMarkWarning: Unknown pytest.mark.xdist_group - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
       @pytest.mark.xdist_group(name="serial")

This warning appears for methods that are intended to run serially, those
decorated with ``@pytest.mark.xdist_group(name="serial")``. However, since
``pytest-xdist`` is now disabled, the decorator no longer exists. To address
this, I implemented the following solution in ``psutil/tests/__init__.py``:

.. code-block:: python

   import pytest, functools

   PYTEST_PARALLEL = "PYTEST_XDIST_WORKER" in os.environ  # True if running parallel tests

   if not PYTEST_PARALLEL:
       def fake_xdist_group(*_args, **_kwargs):
           """Mimics `@pytest.mark.xdist_group` decorator. No-op: it just
           calls the test method or return the decorated class."""
           def wrapper(obj):
               @functools.wraps(obj)
               def inner(*args, **kwargs):
                   return obj(*args, **kwargs)

               return obj if isinstance(obj, type) else inner

           return wrapper

       pytest.mark.xdist_group = fake_xdist_group  # monkey patch

With this in place the warning disappears when running tests serially. To run
tests in parallel, we'll manually enable ``xdist``:

.. code-block:: text

   $ python3 -m pytest -p xdist -n auto --dist loadgroup

Optimizing test collection time
-------------------------------

By default, pytest searches the entire directory for tests, adding unnecessary
overhead. In ``pyproject.toml`` you can tell pytest where test files are
located, and only to consider ``test_*.py`` files:

.. code-block:: toml

   [tool.pytest.ini_options]
   testpaths = ["psutil/tests/"]
   python_files = ["test_*.py"]

Collection time dropped from 0.20s to 0.17s, another ~0.03s shaved off.

Putting it all together
-----------------------

With these small optimizations, I managed to reduce ``pytest`` startup time by
~0.12 seconds, bringing it down from 0.42 seconds. While this improvement is
insignificant for full test runs, it makes a noticeable difference (~28%
faster) when repeatedly running individual tests from the command line, which
is something I do frequently during development. Final result is visible in
:pr:`2538`.

Other links which may be useful
-------------------------------

-  https://github.com/zupo/awesome-pytest-speedup
-  https://projects.gentoo.org/python/guide/pytest.html
