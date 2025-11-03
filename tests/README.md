# Instructions for running tests

Install deps (e.g. pytest):

.. code-block:: bash

    make install-pydeps-test

Run tests:

.. code-block:: bash

    make test

Run tests in parallel (faster):

.. code-block:: bash

    make test-parallel

Run a specific test:

.. code-block:: bash

    make test ARGS=tests.test_system.TestDiskAPIs

Test C extension memory leaks:

.. code-block:: bash

    make test-memleaks

# Running tests on Windows

Same as above, just replace `make` with `make.bat`, e.g.:

.. code-block:: bash

    make.bat install-pydeps-test
    make.bat test
    set ARGS=-k tests.test_system.TestDiskAPIs && make.bat test
