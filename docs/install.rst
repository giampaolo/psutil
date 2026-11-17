Install psutil
==============

Linux, Windows, macOS (wheels)
------------------------------

Prebuilt wheels are distributed for these platforms, so a C compiler is not
required. Install psutil with:

.. code-block:: bash

    pip install psutil

Inside a virtual environment you can also use
`uv <https://docs.astral.sh/uv/>`_:

.. code-block:: bash

    uv pip install psutil

If no wheel is available for your platform or architecture, pip will build
psutil from source (see below).

.. _install_from_source:

Build psutil from source
------------------------

Building psutil from source requires a C compiler and the Python development
headers. On Linux, FreeBSD, NetBSD, OpenBSD and Solaris, the
`install-sysdeps.sh`_ script can install them for you:

.. code-block:: bash

    curl -fsSL \
        https://raw.githubusercontent.com/giampaolo/psutil/master/scripts/internal/install-sysdeps.sh | sh

Alternatively, install them manually as described below.

Linux
^^^^^

Debian / Ubuntu:

.. code-block:: bash

    sudo apt-get install gcc python3-dev

Red Hat / CentOS:

.. code-block:: bash

    sudo yum install gcc python3-devel

Fedora:

.. code-block:: bash

    sudo dnf install gcc python3-devel

Arch:

.. code-block:: bash

    sudo pacman -S gcc python

Alpine:

.. code-block:: bash

    sudo apk add gcc python3-dev musl-dev linux-headers

.. _install_windows:

Windows
^^^^^^^

- To build psutil from source, install
  `Microsoft C++ Build Tools <https://visualstudio.microsoft.com/visual-cpp-build-tools/>`_
  with the "Desktop development with C++" option selected.
- MinGW is not supported.
- To clone psutil's Git repository and build or develop it locally, first
  install `Git for Windows`_ and GNU Make. To install GNU Make, open PowerShell
  and run:

  .. code-block:: powershell

      winget install --exact --id ezwinports.make

- Close and reopen Git Bash, then follow :ref:`build_and_install`.

macOS
^^^^^

Install the Xcode command line tools:

.. code-block:: bash

    xcode-select --install

BSD
^^^

FreeBSD:

.. code-block:: bash

    pkg install python3

OpenBSD:

.. code-block:: bash

    export PKG_PATH=https://cdn.openbsd.org/pub/OpenBSD/`uname -r`/packages/`uname -m`/
    pkg_add -v python%3

NetBSD: pkgsrc has no version-agnostic python3 package, so choose one of the
available Python 3 versions. For example:

.. code-block:: bash

    export PKG_PATH="https://cdn.netbsd.org/pub/pkgsrc/packages/NetBSD/`uname -m`/`uname -r`/All"
    pkg_add -v pkgin
    pkgin update
    pkgin install python314

Solaris
^^^^^^^

.. code-block:: bash

    pkg install developer/gcc

If ``cc`` is unavailable, set ``CC=gcc`` when running the commands in
:ref:`build_and_install`.

AIX
^^^

``install-sysdeps.sh`` has no AIX branch. Install a C compiler and the Python
development headers from the `AIX Toolbox`_.

.. _build_and_install:

Build and install
-----------------

To build and install psutil from a Git checkout:

.. code-block:: bash

    git clone https://github.com/giampaolo/psutil.git
    cd psutil
    make install-sysdeps
    make build
    make install

.. note::

   By default C source files are compiled in parallel, one job per CPU, which
   makes building from source 2x to 3.6x faster. Use
   :envvar:`PSUTIL_BUILD_JOBS` to change the number of jobs.

Troubleshooting
---------------

Install pip
^^^^^^^^^^^

Python installations normally include pip. If it is missing, first try:

.. code-block:: bash

    python3 -m ensurepip --upgrade

Some OS-packaged Python installations do not include ``ensurepip``. There,
either install the pip package or download `get-pip.py`_ and run:

.. code-block:: bash

    python3 get-pip.py

Permission errors
^^^^^^^^^^^^^^^^^

If you encounter permission errors, install psutil inside a virtual environment
instead of modifying the system Python installation:

.. tab-set::

   .. tab-item:: Unix

      .. code-block:: bash

          python3 -m venv .venv
          source .venv/bin/activate
          python -m pip install psutil

   .. tab-item:: Windows

      .. code-block:: powershell

          py -m venv .venv
          .venv\Scripts\Activate.ps1
          python -m pip install psutil

.. _`AIX Toolbox`: https://www.ibm.com/support/pages/aix-toolbox-open-source-software-downloads-alpha
.. _`get-pip.py`: https://bootstrap.pypa.io/get-pip.py
.. _`Git for Windows`: https://git-scm.com/install/windows
.. _`install-sysdeps.sh`: https://github.com/giampaolo/psutil/blob/master/scripts/internal/install-sysdeps.sh
