#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import sys


try:
    import pip  # noqa: F401
except ImportError:
    pass
else:
    print("pip already installed")
    sys.exit(0)

import os
import ssl
import tempfile


PY3 = sys.version_info[0] >= 3
if PY3:
    from urllib.request import urlopen

    URL = "https://bootstrap.pypa.io/get-pip.py"

else:
    from urllib2 import urlopen

    URL = "https://bootstrap.pypa.io/pip/2.7/get-pip.py"


def main():
    ssl_context = (
        ssl._create_unverified_context()
        if hasattr(ssl, "_create_unverified_context")
        else None
    )
    with tempfile.NamedTemporaryFile(suffix=".py") as f:
        print("downloading %s into %s" % (URL, f.name))
        kwargs = dict(context=ssl_context) if ssl_context else {}
        req = urlopen(URL, **kwargs)
        data = req.read()
        req.close()

        f.write(data)
        f.flush()
        print("download finished, installing pip")

        code = os.system("%s %s --user --upgrade" % (sys.executable, f.name))

    sys.exit(code)


if __name__ == "__main__":
    main()
