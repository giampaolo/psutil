Instructions for running tests
==============================

There are 2 ways of running tests. If you have the source code:

.. code-block:: bash

    make install-pydeps-test  # install pytest
    make test

If you don't have the source code, and just want to test psutil installation.
This will work also if ``pytest`` module is not installed (e.g. production
environments) by using unittest's test runner:

.. code-block:: bash

    python -m psutil.tests

To run tests in parallel (faster):

.. code-block:: bash

    make test-parallel

Run a specific test:

.. code-block:: bash

    make test ARGS=psutil.tests.test_system.TestDiskAPIs

Test C extension memory leaks:

.. code-block:: bash

    make test-memleaks
