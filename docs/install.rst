Install psutil
==============

Linux, Windows, macOS (wheels)
------------------------------

Prebuilt wheels are distributed for these platforms, so you won't need a C
compiler. Install psutil with:

.. code-block:: none

    pip install psutil

Inside a virtual environment you can also use
`uv <https://docs.astral.sh/uv/>`_:

.. code-block:: none

    uv pip install psutil

If wheels are not available for your platform or architecture, or you wish to
build and install psutil from source, keep reading.

.. _install_from_source:

Compile psutil from source
--------------------------

Compiling psutil requires two things: a C compiler and the Python development
headers. On Linux, FreeBSD, NetBSD, OpenBSD and Solaris the
`install-sysdeps.sh`_ script installs the required system dependencies. From an
existing Git checkout:

.. code-block:: none

    make install-sysdeps

...or run the latest development version of the script directly from GitHub:

.. code-block:: none

    curl -fsSL https://raw.githubusercontent.com/giampaolo/psutil/master/scripts/internal/install-sysdeps.sh | sh

Alternatively, install the required dependencies manually as described below,
then head to :ref:`build_and_install`.

Linux
^^^^^

Debian / Ubuntu:

.. code-block:: none

    sudo apt-get install gcc python3-dev

Red Hat / CentOS:

.. code-block:: none

    sudo yum install gcc python3-devel

Fedora:

.. code-block:: none

    sudo dnf install gcc python3-devel

Arch:

.. code-block:: none

    sudo pacman -S gcc python

Alpine:

.. code-block:: none

    sudo apk add gcc python3-dev musl-dev linux-headers

.. _install_windows:

Windows
^^^^^^^

- To build psutil from source, install
  `Microsoft C++ Build Tools <https://visualstudio.microsoft.com/visual-cpp-build-tools/>`_
  with the **Desktop development with C++** option selected.
- MinGW is not supported.
- To clone psutil's Git repository and build or develop it locally, first
  install `Git for Windows`_ and GNU Make. To install GNU Make, open PowerShell
  and run:

  .. code-block:: none

      winget install --exact --id ezwinports.make

- Close and reopen Git Bash, then follow :ref:`build_and_install`.

macOS
^^^^^

Install the Xcode command line tools:

.. code-block:: none

    xcode-select --install

FreeBSD
^^^^^^^

.. code-block:: none

    pkg install python312 py312-pip

OpenBSD
^^^^^^^

.. code-block:: none

    export PKG_PATH=https://cdn.openbsd.org/pub/OpenBSD/`uname -r`/packages/`uname -m`/
    pkg_add -v python%3 py3-pip

NetBSD
^^^^^^

Assuming Python 3.11:

.. code-block:: none

    export PKG_PATH="https://cdn.netbsd.org/pub/pkgsrc/packages/NetBSD/`uname -m`/`uname -r`/All"
    pkg_add -v pkgin
    pkgin update
    pkgin install python311 py311-pip

Solaris
^^^^^^^

.. code-block:: none

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

To build from a Git checkout:

.. code-block:: none

    git clone https://github.com/giampaolo/psutil.git
    cd psutil
    make build
    make install

...or download and install the latest source distribution from `PyPI`_:

.. code-block:: none

    python -m pip install --no-binary=psutil psutil

.. note::
   By default C source files are compiled in parallel, one job per CPU, which
   makes building from source 2x to 3.6x faster. Use
   :envvar:`PSUTIL_BUILD_JOBS` to change the number of jobs.

Troubleshooting
---------------

Install pip
^^^^^^^^^^^

Python installations normally include pip. If it is missing, first try:

.. code-block:: none

    python3 -m ensurepip --upgrade

Some OS-packaged Python installations do not include ``ensurepip``. There,
either install the pip package or download `get-pip.py`_ and run:

.. code-block:: none

    python3 get-pip.py

Permission errors
^^^^^^^^^^^^^^^^^

If you encounter permission errors, install psutil inside a virtual environment
instead of modifying the system Python installation:

.. code-block:: none

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install psutil

.. _`AIX Toolbox`: https://www.ibm.com/support/pages/aix-toolbox-open-source-software-downloads-alpha
.. _`get-pip.py`: https://bootstrap.pypa.io/get-pip.py
.. _`Git for Windows`: https://git-scm.com/install/windows
.. _`install-sysdeps.sh`: https://github.com/giampaolo/psutil/blob/master/scripts/internal/install-sysdeps.sh
.. _`PyPI`: https://pypi.org/project/psutil/
