Install psutil
==============

Linux, Windows, macOS (wheels)
------------------------------

Pre-compiled wheels are distributed for these platforms, so you usually won't
need a C compiler. Install psutil with:

.. code-block:: none

    pip install psutil

If wheels are not available for your platform or architecture, or you wish to
build & install psutil from sources, keep reading.

Compile psutil from source
--------------------------

UNIX
^^^^

On all UNIX systems you can use the `install-sysdeps.sh`_ script. This will
install the system dependencies necessary to compile psutil from sources. You
can invoke this script from the Makefile as:

.. code-block:: none

    make install-sysdeps

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

    sudo apt install gcc python3-dev
    pip install --no-binary :all: psutil

RedHat / CentOS:

.. code-block:: none

    sudo yum install gcc python3-devel
    pip install --no-binary :all: psutil

Arch:

.. code-block:: none

    sudo pacman -S gcc python
    pip install --no-binary :all: psutil

Alpine:

.. code-block:: none

    sudo apk add gcc python3-dev musl-dev linux-headers
    pip install --no-binary :all: psutil

Windows
^^^^^^^

- To build or install psutil from source on Windows, you need to have
  `Visual Studio 2017`_ or later installed. For detailed instructions, see the
  `CPython Developer Guide`_.
- MinGW is not supported for building psutil on Windows.
- To build directly from the source tarball (.tar.gz) on PYPI, run:

  .. code-block:: none

      pip install --no-binary :all: psutil

- If you want to clone psutil's Git repository and build / develop locally,
  first install `Git for Windows`_ and launch a Git Bash shell. This provides a
  Unix-like environment where ``make`` works.
- Once inside Git Bash, you can run the usual ``make`` commands:

  .. code-block:: none

      make build
      make install

macOS
^^^^^

Install Xcode first:

.. code-block:: none

    xcode-select --install
    pip install --no-binary :all: psutil

FreeBSD
^^^^^^^

.. code-block:: none

    pkg install python3 gcc
    python3 -m pip install psutil

OpenBSD
^^^^^^^

.. code-block:: none

    export PKG_PATH=https://cdn.openbsd.org/pub/OpenBSD/`uname -r`/packages/`uname -m`/
    pkg_add -v python3 gcc
    pip install psutil

NetBSD
^^^^^^

Assuming Python 3.11:

.. code-block:: none

    export PKG_PATH="https://ftp.netbsd.org/pub/pkgsrc/packages/NetBSD/`uname -m`/`uname -r`/All"
    pkg_add -v pkgin
    pkgin install python311-* gcc12-* py311-setuptools-* py311-pip-*
    python3.11 -m pip install psutil

Sun Solaris
^^^^^^^^^^^

If ``cc`` compiler is not installed create a symbolic link to ``gcc``:

.. code-block:: none

    sudo ln -s /usr/bin/gcc /usr/local/bin/cc

Install:

.. code-block:: none

    pkg install gcc
    pip install psutil

Troubleshooting
---------------

Install pip
^^^^^^^^^^^

If you don't have pip you can install it with wget:

.. code-block:: none

    wget https://bootstrap.pypa.io/get-pip.py -O - | python3

...or with curl:

.. code-block:: none

    python3 < <(curl -s https://bootstrap.pypa.io/get-pip.py)

On Windows, `download pip`_, open cmd.exe and install it with:

.. code-block:: none

    py get-pip.py

Permission errors (UNIX)
^^^^^^^^^^^^^^^^^^^^^^^^

If you want to install psutil system-wide and you bump into permission errors
either run as root user or prepend ``sudo``:

.. code-block:: none

    sudo pip install psutil

.. _`CPython Developer Guide`: https://devguide.python.org/getting-started/setup-building/#windows
.. _`download pip`: https://pip.pypa.io/en/latest/installing/
.. _`Git for Windows`: https://git-scm.com/install/windows
.. _`install-sysdeps.sh`: https://github.com/giampaolo/psutil/blob/master/scripts/internal/install-sysdeps.sh
.. _`PyPI`: https://pypi.org/project/psutil/
.. _`Visual Studio 2017`: https://visualstudio.microsoft.com/vs/older-downloads/
