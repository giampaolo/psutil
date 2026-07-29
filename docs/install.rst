Install psutil
==============

Linux, Windows, macOS (wheels)
------------------------------

Pre-compiled wheels are distributed for these platforms, so you usually won't
need a C compiler. Install psutil with:

.. code-block:: none

    pip install psutil

Or with `uv <https://docs.astral.sh/uv/>`_:

.. code-block:: none

    uv pip install psutil

If wheels are not available for your platform or architecture, or you wish to
build & install psutil from sources, keep reading.

Compile psutil from source
--------------------------

UNIX
^^^^

On all UNIX systems except macOS and AIX you can use the `install-sysdeps.sh`_
script. This will install the system dependencies necessary to compile psutil
from sources. You can invoke this script from the Makefile as:

.. code-block:: none

    make install-sysdeps

...or download and run it directly from GitHub:

.. code-block:: none

    curl -fsSL https://raw.githubusercontent.com/giampaolo/psutil/master/scripts/internal/install-sysdeps.sh | sh

After system deps are installed, you can compile and install psutil with:

.. code-block:: none

    make build
    make install

...or this, which will fetch the latest source distribution from `PyPI`_:

.. code-block:: none

    pip install --no-binary :all: psutil

Linux
^^^^^

Debian / Ubuntu:

.. code-block:: none

    sudo apt-get install gcc python3-dev
    pip install --no-binary :all: psutil

RedHat / CentOS:

.. code-block:: none

    sudo yum install gcc python3-devel
    pip install --no-binary :all: psutil

Fedora:

.. code-block:: none

    sudo dnf install gcc python3-devel
    pip install --no-binary :all: psutil

Arch:

.. code-block:: none

    sudo pacman -S gcc python
    pip install --no-binary :all: psutil

Alpine:

.. code-block:: none

    sudo apk add gcc python3-dev musl-dev linux-headers
    pip install --no-binary :all: psutil

.. _install_windows:

Windows
^^^^^^^

- To build psutil from source, install
  `Microsoft C++ Build Tools <https://visualstudio.microsoft.com/visual-cpp-build-tools/>`_
  with the **Desktop development with C++** option selected.
- MinGW is not supported.
- To build and install psutil directly from the source distribution on PyPI,
  run:

  .. code-block:: none

      python -m pip install --no-binary=:all: psutil

- To clone psutil's Git repository and build or develop it locally, first
  install `Git for Windows`_ and GNU Make. To install GNU Make, open PowerShell
  and run:

  .. code-block:: none

      winget install --exact --id ezwinports.make

- Close and reopen Git Bash, then run the usual ``make`` commands:

  .. code-block:: none

      make build
      make install

macOS
^^^^^

Install the Xcode command line tools first:

.. code-block:: none

    xcode-select --install
    pip install --no-binary :all: psutil

FreeBSD
^^^^^^^

.. code-block:: none

    pkg install python3 py312-pip
    python3 -m pip install psutil

OpenBSD
^^^^^^^

.. code-block:: none

    export PKG_PATH=https://cdn.openbsd.org/pub/OpenBSD/`uname -r`/packages/`uname -m`/
    pkg_add -v python%3 py3-pip
    python3 -m pip install psutil

NetBSD
^^^^^^

Assuming Python 3.11:

.. code-block:: none

    export PKG_PATH="https://cdn.netbsd.org/pub/pkgsrc/packages/NetBSD/`uname -m`/`uname -r`/All"
    pkg_add -v pkgin
    pkgin update
    pkgin install 'python311-*' 'py311-setuptools-*' 'py311-pip-*'
    python3.11 -m pip install psutil

Sun Solaris
^^^^^^^^^^^

.. code-block:: none

    pkg install developer/gcc
    pip install psutil

If there's no ``cc`` afterwards, symlink it to gcc:

.. code-block:: none

    sudo ln -s /usr/bin/gcc /usr/local/bin/cc

AIX
^^^

``install-sysdeps.sh`` has no AIX branch. Install a C compiler and the python
headers from the `AIX Toolbox`_, then:

.. code-block:: none

    pip install --no-binary :all: psutil

Troubleshooting
---------------

Install pip
^^^^^^^^^^^

Python installations normally include pip. If it is missing, first try:

.. code-block:: none

    python3 -m ensurepip --upgrade

Some ports (the BSDs, Debian) build python without ``ensurepip``. There, either
install the pip package or download `get-pip.py`_ and run:

.. code-block:: none

    python3 get-pip.py

Permission errors
^^^^^^^^^^^^^^^^^

If you encounter permission errors, install psutil inside a virtual environment
instead of modifying the system Python installation:

.. code-block:: none

    python3 -m venv .venv
    . .venv/bin/activate
    python -m pip install psutil

.. _`AIX Toolbox`: https://www.ibm.com/support/pages/aix-toolbox-open-source-software-downloads-alpha
.. _`get-pip.py`: https://bootstrap.pypa.io/get-pip.py
.. _`Git for Windows`: https://git-scm.com/install/windows
.. _`install-sysdeps.sh`: https://github.com/giampaolo/psutil/blob/master/scripts/internal/install-sysdeps.sh
.. _`PyPI`: https://pypi.org/project/psutil/
