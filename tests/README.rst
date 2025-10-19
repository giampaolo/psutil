Instructions for running tests
==============================

Run tests:

.. code-block:: bash

    make install-pydeps-test  # install pytest
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
