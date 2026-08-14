#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Install pip, or upgrade it if it's too old.

Note: we build wheels on Python 3.8 (the floor), but don't run tests
for it, nor installs deps, so this script is never called there.
"""

import re
import ssl
import subprocess
import sys
import tempfile
from urllib.request import urlopen

try:
    import pip
except ImportError:
    pip = None


if sys.version_info >= (3, 10):
    URL = "https://bootstrap.pypa.io/get-pip.py"
else:
    URL = "https://bootstrap.pypa.io/pip/{}.{}/get-pip.py".format(
        *sys.version_info[:2]
    )

# Needed by "pip install --group" (PEP 735), used by the
# install-pydeps-* makefile targets.
MIN_VERSION = (25, 1)


def get_pip_version():
    if pip is not None:
        match = re.match(r"(\d+)\.(\d+)", pip.__version__)
        return (int(match.group(1)), int(match.group(2))) if match else (0, 0)


def install_pip():
    ssl_context = (
        ssl._create_unverified_context()
        if hasattr(ssl, "_create_unverified_context")
        else None
    )
    opts = ["--upgrade", "--break-system-packages"]
    if not hasattr(sys, "real_prefix") and sys.base_prefix == sys.prefix:
        opts.append("--user")  # rejected when inside a virtualenv

    with tempfile.NamedTemporaryFile(suffix=".py") as f:
        print(f"downloading {URL} into {f.name}")
        kwargs = dict(context=ssl_context) if ssl_context else {}
        req = urlopen(URL, **kwargs)
        data = req.read()
        req.close()

        f.write(data)
        f.flush()
        print("download finished, installing pip")

        code = subprocess.call([sys.executable, f.name, *opts])

    sys.exit(code)


def main():
    version = get_pip_version()
    if version is None:
        print("pip is not installed")
    elif version < MIN_VERSION:
        print(f"pip {pip.__version__} is too old; upgrading")
    else:
        print(f"pip (version {pip.__version__}) already installed")
        return
    install_pip()


if __name__ == "__main__":
    main()
