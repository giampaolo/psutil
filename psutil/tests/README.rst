Instructions for running tests
==============================

Setup:

.. code-block:: bash

    make install-pydeps-test  # install pytest

There are two ways of running tests. As a "user", if psutil is already
installed and you just want to test it works on your system:

.. code-block:: bash

    python -m psutil.tests

As a "developer", if you have a copy of the source code and you're working on
it:

.. code-block:: bash

    make test

You can run tests in parallel with:

.. code-block:: bash

    make test-parallel

You can run a specific test with:

.. code-block:: bash

    make test ARGS=psutil.tests.test_system.TestDiskAPIs

You can run memory leak tests with:

.. code-block:: bash

    make test-parallel
