#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Install pip, or upgrade it if it's too old."""

import re
import ssl
import subprocess
import sys
import tempfile
from urllib.request import urlopen

URL = "https://bootstrap.pypa.io/get-pip.py"
# Needed by "pip install --group" (PEP 735), used by the
# install-pydeps-* makefile targets.
MIN_VERSION = (25, 1)


def get_pip_version():
    try:
        import pip
    except ImportError:
        return None
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
        have = ".".join(map(str, version))
        want = ".".join(map(str, MIN_VERSION))
        print(f"pip {have} is too old, we need >= {want}")
    else:
        print("pip already installed")
        return
    install_pip()


if __name__ == "__main__":
    main()
